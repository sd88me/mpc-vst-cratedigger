// Crate Digger for MPC / Force: the MPC Plugin SDK front end (framework/mpc_plugin.h) around the unchanged schwung-webstream core
// (src/dsp/yt_stream_plugin.c, built with -DYT_POSIX_SPAWN: no fork() inside the MPC).
//
// The core renders on a worker thread into a ring buffer and the audio callback only copies from it: the core takes locks, starts ffmpeg and
// reads pipes while rendering, none of which may happen on the MPC's audio thread. The filter steppers, SEARCH, the transport buttons, the
// popup keyboard, the status readouts and the eight result rows are host parameters in the frozen order of vst/params.json (103, the order of
// the 1.x wrapper build). Their text is the parameter's value text: the worker keeps the host in step with the plugin's own state
// (steppers, lit buttons, the playing row, every readout) and asks it to re-read the text when it changes.
//
// The engine bundle (yt-dlp, python, ffmpeg) is found at run time, in this order: an existing 1.x install (/sdcard/vst/cratedigger), the
// plugin folder's Content/engine, and, when that folder cannot run programs (exFAT drives), a copy of it made once on the internal drive.
// State: the framework saves every parameter by id; the typed search text goes in the extra state. A project saved by the 1.x wrapper build
// ("g=..;s=..;..." text) is still read: effSetChunk is wrapped in VSTPluginMain below.

#include "mpc_plugin.h"

#include <algorithm>
#include <atomic>
#include <cerrno>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <mutex>
#include <string>
#include <thread>
#include <vector>
#include <dlfcn.h>
#include <signal.h>
#include <spawn.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <unistd.h>

#include "plugin_api_v1.h"
#include "cratedig_tables.h"
#include "params_gen.h"

extern "C" plugin_api_v2_t *move_plugin_init_v2(const host_api_v1_t *host);
extern char **environ;

#ifndef CD_NAME
#define CD_NAME "Crate Digger"
#endif
#ifndef CD_UID
#define CD_UID 'C', 'r', 'D', 'g'
#endif
#define CD_FOURCC(...) MPC_FOURCC(__VA_ARGS__)   // expands CD_UID before MPC_FOURCC counts its arguments
#ifndef CD_VERSION
#define CD_VERSION 2000
#endif

/* ---- constants ------------------------------------------------------------ */
static const int BLOCK = 128;             /* core's native block (44.1 kHz, same as Move) */
static const int RING = 16384;            /* frames, power of two */
static const int TARGET_FILL = 2048;      /* ~46 ms kept ahead of MPC */
static const int SLOTS = 8;               /* result rows per page */
enum { DIM_GENRE, DIM_STYLE, DIM_DECADE, DIM_REGION, DIM_COUNTRY, NDIMS };
enum { SRC_DISCOGS, SRC_CHANNEL, SRC_YOUTUBE, NSOURCES };
static const char *const SOURCE_NAMES[NSOURCES] = {"discogs", "channel", "youtube"};
static const size_t QUERY_MAX = 48;       /* typed search text, characters */
static const size_t CHANNELS_MAX = 16;
/* YOUTUBE tab: the length window (minutes; 0 = any) and the music-only switch, for the channel and YouTube sources. */
static const int MIN_LENS[] = {0, 1, 2, 3, 5, 10};
static const int MAX_LENS[] = {0, 5, 6, 10, 15, 20, 30, 60};
static const int NMIN_LENS = (int)(sizeof MIN_LENS / sizeof *MIN_LENS), NMAX_LENS = (int)(sizeof MAX_LENS / sizeof *MAX_LENS);
static const long KEY_REPEAT_MS = 150;
static const long TAP_GAP_MS = 300;   /* same popup key twice inside this is one tap */
struct Channel { std::string link, name; };   /* one line of channels.txt */

/* Everything the old wrapper's Plugin struct held, minus the VST glue. Guarded by `lock`. */
struct Engine {
    plugin_api_v2_t *api = nullptr;
    void *core = nullptr;                 /* null until the worker has found the engine bundle and created the core */
    std::string engine_error;             /* set when no engine bundle could be found or prepared */
    std::mutex lock;                      /* serialises every core call and every field below */
    int16_t ring[RING * 2];
    std::atomic<uint32_t> wpos{0}, rpos{0};
    int dim[NDIMS] = {0, 0, 0, 0, 0};     /* filter selection */
    int page = 0;
    float gain = 1.0f;
    int source = SRC_DISCOGS;             /* FIND tab: where SEARCH digs */
    int min_len = 0, max_len = 0;         /* YOUTUBE tab: indices into MIN_LENS / MAX_LENS */
    bool music = false;                   /* YOUTUBE tab: YouTube Music songs only */
    int chan = 0;                         /* index into channels */
    std::vector<Channel> channels;        /* channels.txt, reloaded when its mtime changes */
    std::string channels_path;
    time_t channels_mtime = -1;
    std::string query;                    /* typed on the popup keyboard */
    bool kb = false;                      /* popup keyboard shown */
    int last_key = -1;                    /* the popup keyboard's last key and when, to drop a repeat of one tap */
    std::chrono::steady_clock::time_point last_key_at;
    std::chrono::steady_clock::time_point search_at;
    int searched_source = SRC_DISCOGS;    /* what the last SEARCH asked, for the status text */
    /* Transport Sync: a tapped result loads and buffers, then waits for MPC's Play. */
    bool sync = false;
    bool hold = false;                    /* a track is buffered and waiting */
    bool sync_started = false;            /* MPC Play released the current track */
    std::atomic<bool> transport_playing{false};
    std::atomic<int> transport_edge{0};   /* +1 = MPC started, -1 = MPC stopped; worker consumes */
};
typedef Engine Plugin;   /* the helpers below keep their old signatures */

/* ---- small helpers -------------------------------------------------------- */
static FILE *g_log;
/* [sec.msec] prefix lines up against the engine's own /tmp/webstream-runtime.log (also wall-clock-stamped), so a bug report's two log files
 * can be read as one timeline. */
#define LOG(...) do { if (g_log) { \
        auto __now = std::chrono::system_clock::now().time_since_epoch(); \
        long long __ms = std::chrono::duration_cast<std::chrono::milliseconds>(__now).count(); \
        std::fprintf(g_log, "[%lld.%03lld] ", __ms / 1000, __ms % 1000); \
        std::fprintf(g_log, __VA_ARGS__); std::fflush(g_log); \
    } } while (0)

static std::string core_get(Plugin *p, const char *key) {
    if (!p->core) return std::string();
    char buf[512];
    int n = p->api->get_param(p->core, key, buf, sizeof buf);
    return n > 0 ? std::string(buf, (size_t)(n < (int)sizeof buf ? n : (int)sizeof buf - 1)) : std::string();
}
static void core_set(Plugin *p, const char *key, const char *val) {
    if (p->core) p->api->set_param(p->core, key, val);
}
static std::string core_get_idx(Plugin *p, const char *fmt, int i) {
    char key[64];
    std::snprintf(key, sizeof key, fmt, i);
    return core_get(p, key);
}
static std::string upper(std::string s) {
    for (auto &c : s) c = (char)std::toupper((unsigned char)c);
    return s;
}

/* ---- filter lists (cratedig_tables.h, shared with the Force host) --------- */
static int dim_count(Plugin *p, int d) {
    switch (d) {
    case DIM_GENRE: return N_CRATEDIG_GENRES;
    case DIM_STYLE: return styles_for_genre(CRATEDIG_GENRES[p->dim[DIM_GENRE]])->n;
    case DIM_DECADE: return N_CRATEDIG_DECADES;
    case DIM_REGION: return N_CRATEDIG_REGIONS;
    default: return N_COUNTRIES_BY_REGION[p->dim[DIM_REGION]];
    }
}
static const char *dim_value(Plugin *p, int d) {
    int i = p->dim[d];
    switch (d) {
    case DIM_GENRE: return CRATEDIG_GENRES[i];
    case DIM_STYLE: return styles_for_genre(CRATEDIG_GENRES[p->dim[DIM_GENRE]])->styles[i];
    case DIM_DECADE: return CRATEDIG_DECADES[i];
    case DIM_REGION: return CRATEDIG_REGIONS[i];
    default: return CRATEDIG_COUNTRIES_BY_REGION[p->dim[DIM_REGION]][i];
    }
}
static void set_dim(Plugin *p, int d, int i) {
    int n = dim_count(p, d);
    if (i < 0) i = 0;
    if (i > n - 1) i = n - 1;
    const bool changed = p->dim[d] != i;
    p->dim[d] = i;
    if (changed && d == DIM_GENRE) p->dim[DIM_STYLE] = 0;       /* style list depends on genre */
    if (changed && d == DIM_REGION) p->dim[DIM_COUNTRY] = 0;    /* country list depends on region */
}

static std::string json_escape(const char *s) {
    std::string o;
    for (; *s; s++) {
        if (*s == '"' || *s == '\\') o += '\\';
        o += *s;
    }
    return o;
}

/* ---- results -------------------------------------------------------------- */
static int result_count(Plugin *p) { return std::atoi(core_get(p, "search_count").c_str()); }
static int page_count(Plugin *p) { int n = result_count(p); return n > 0 ? (n + SLOTS - 1) / SLOTS : 1; }

static std::string result_label(Plugin *p, int idx) {
    std::string t = core_get_idx(p, "search_result_title_%d", idx);
    std::string ch = core_get_idx(p, "search_result_channel_%d", idx);
    std::string yr = core_get_idx(p, "search_result_year_%d", idx);
    std::string du = core_get_idx(p, "search_result_duration_%d", idx);
    char num[16];
    std::snprintf(num, sizeof num, "%02d  ", idx + 1);
    std::string l = num + (t.empty() ? std::string("(untitled)") : t);
    if (!ch.empty()) l += " - " + ch;
    if (!yr.empty()) l += "  " + yr;
    if (!du.empty()) l += "  " + du;
    return l;
}

/* Same two-step protocol as the host's handle_play_result_index_locked(). */
static bool play_result(Plugin *p, int idx) {
    std::string url = core_get_idx(p, "search_result_url_%d", idx);
    if (url.empty()) return false;
    std::string prov = core_get_idx(p, "search_result_provider_%d", idx);
    char s[16];
    std::snprintf(s, sizeof s, "%d", idx);
    LOG("play_result idx=%d prev_stream_status=%s prev_stream_url=%s\n", idx,
        core_get(p, "stream_status").c_str(), core_get(p, "stream_url").c_str());
    p->hold = p->sync;
    p->sync_started = false;
    core_set(p, "hold_start", p->hold ? "1" : "0");
    core_set(p, "stream_provider", prov.empty() ? "youtube" : prov.c_str());
    core_set(p, "stream_url", url.c_str());
    core_set(p, "cratedig_result_index", s);
    return true;
}
static int current_result(Plugin *p) {
    if (core_get(p, "stream_url").empty()) return -1;
    return std::atoi(core_get(p, "cratedig_result_index").c_str());
}

/* channels.txt: one channel per line, "link-or-@handle-or-UC-id | Name". A leading "any =" or "2020s =" (the old
 * channels.txt of PR #21, where the DECADE stepper picked the channel) is ignored. Reread when the file changes. */
static void load_channels(Plugin *p) {
    if (p->channels_path.empty()) return;
    struct stat sb;
    time_t mt = stat(p->channels_path.c_str(), &sb) == 0 ? sb.st_mtime : 0;
    if (mt == p->channels_mtime) return;
    p->channels_mtime = mt;
    p->channels.clear();
    if (FILE *f = std::fopen(p->channels_path.c_str(), "r")) {
        char line[512];
        while (std::fgets(line, sizeof line, f) && p->channels.size() < CHANNELS_MAX) {
            std::string l = line;
            while (!l.empty() && std::isspace((unsigned char)l.back())) l.pop_back();
            size_t b = l.find_first_not_of(" \t");
            if (b == std::string::npos || l[b] == '#') continue;
            l = l.substr(b);
            size_t eq = l.find('=');
            if (eq != std::string::npos && eq <= 5 && (l.compare(0, 3, "any") == 0 || std::isdigit((unsigned char)l[0])))
                l = l.substr(eq + 1);
            std::string name;
            size_t bar = l.find('|');
            if (bar != std::string::npos) { name = l.substr(bar + 1); l = l.substr(0, bar); }
            auto trim = [](std::string &t) {
                while (!t.empty() && std::isspace((unsigned char)t.back())) t.pop_back();
                size_t s0 = t.find_first_not_of(" \t");
                t = s0 == std::string::npos ? std::string() : t.substr(s0);
            };
            trim(l); trim(name);
            if (l.empty()) continue;
            if (name.empty()) name = l;
            p->channels.push_back({l, name});
        }
        std::fclose(f);
    }
    if (p->chan >= (int)p->channels.size()) p->chan = 0;
    LOG("channels.txt: %zu channels\n", p->channels.size());
}

static void do_search(Plugin *p, bool find);

static bool is_key(int i) { return PARAMS[i].key[0] == 'k' && PARAMS[i].key[1] == '_'; }
static void type_key(Plugin *p, const char *k) {
    if (!std::strcmp(k, "back")) { if (!p->query.empty()) p->query.pop_back(); }
    else if (!std::strcmp(k, "clear")) p->query.clear();
    else if (!std::strcmp(k, "hide")) p->kb = false;
    else if (!std::strcmp(k, "send")) { p->kb = false; do_search(p, true); }
    else if (!std::strcmp(k, "space")) { if (!p->query.empty() && p->query.back() != ' ' && p->query.size() < QUERY_MAX) p->query += ' '; }
    else if (k[0] && !k[1] && p->query.size() < QUERY_MAX) p->query += (char)std::tolower((unsigned char)k[0]);
}

/* find=false: the FILTERS tab, always a Discogs dig on the five filters. find=true: the FIND tab, which also sends the source,
 * the typed text and the chosen channel (the daemon routes on "source"; for Discogs the text joins the filters). */
static void do_search(Plugin *p, bool find) {
    if (!p->core) return;
    int src = find ? p->source : SRC_DISCOGS;
    std::string q = find ? p->query : std::string();
    while (!q.empty() && q.back() == ' ') q.pop_back();
    std::string chan = src == SRC_CHANNEL && p->chan < (int)p->channels.size() ? p->channels[p->chan].link : std::string();
    std::string json = std::string("{\"genre\":\"") + json_escape(dim_value(p, DIM_GENRE)) +
                       "\",\"style\":\"" + json_escape(dim_value(p, DIM_STYLE)) +
                       "\",\"decade\":\"" + json_escape(dim_value(p, DIM_DECADE)) +
                       "\",\"country\":\"" + json_escape(dim_value(p, DIM_COUNTRY)) +
                       "\",\"source\":\"" + SOURCE_NAMES[src] + "\",\"query\":\"" + json_escape(q.c_str()) +
                       "\",\"channel\":\"" + json_escape(chan.c_str()) +
                       "\",\"min_len\":" + std::to_string(MIN_LENS[p->min_len] * 60) + ",\"max_len\":" + std::to_string(MAX_LENS[p->max_len] * 60) +
                       ",\"music\":" + (p->music ? "1" : "0") + "}";
    p->page = 0;
    p->searched_source = src;
    LOG("search pressed: prev_search_status=%s stream_status=%s stream_url=%s filter=%s\n",
        core_get(p, "search_status").c_str(), core_get(p, "stream_status").c_str(),
        core_get(p, "stream_url").c_str(), json.c_str());
    core_set(p, "cratedig_filter", json.c_str());
}

/* MPC Play releases a buffered track (or resumes a paused one); MPC Stop pauses it. */
static void transport_edge_locked(Plugin *p, bool playing) {
    std::string st = core_get(p, "stream_status");
    LOG("transport %s: hold=%d stream_status=%s\n", playing ? "play" : "stop", p->hold, st.c_str());
    if (playing) {
        if (p->hold) {
            p->hold = false;
            p->sync_started = true;
            core_set(p, "hold_start", "0");
        } else if (st == "paused") {
            core_set(p, "play_pause_toggle", "1");
        }
    } else if (!p->hold && (st == "streaming" || st == "buffering")) {
        core_set(p, "play_pause_toggle", "1");
    }
}

static int stepper_count(Plugin *p, int i) {
    if (i == P_PAGE) return page_count(p);
    if (i == P_SOURCE) return NSOURCES;
    if (i == P_CHANNEL) return p->channels.empty() ? 1 : (int)p->channels.size();
    if (i == P_MIN_LEN) return NMIN_LENS;
    if (i == P_MAX_LEN) return NMAX_LENS;
    if (i == P_MUSIC) return 2;
    return dim_count(p, i);
}
static int stepper_index(Plugin *p, int i) {
    if (i == P_PAGE) return p->page;
    if (i == P_SOURCE) return p->source;
    if (i == P_CHANNEL) return p->chan;
    if (i == P_MIN_LEN) return p->min_len;
    if (i == P_MAX_LEN) return p->max_len;
    if (i == P_MUSIC) return p->music ? 1 : 0;
    return i >= 0 && i < NDIMS ? p->dim[i] : 0;
}
static void stepper_set(Plugin *p, int i, int v) {
    if (i == P_PAGE) {
        int n = page_count(p);
        p->page = v < 0 ? 0 : v > n - 1 ? n - 1 : v;
    } else if (i == P_SOURCE) {
        p->source = v < 0 ? 0 : v > NSOURCES - 1 ? NSOURCES - 1 : v;
    } else if (i == P_CHANNEL) {
        int n = stepper_count(p, i);
        p->chan = v < 0 ? 0 : v > n - 1 ? n - 1 : v;
    } else if (i == P_MIN_LEN) {
        p->min_len = v < 0 ? 0 : v > NMIN_LENS - 1 ? NMIN_LENS - 1 : v;
    } else if (i == P_MAX_LEN) {
        p->max_len = v < 0 ? 0 : v > NMAX_LENS - 1 ? NMAX_LENS - 1 : v;
    } else if (i == P_MUSIC) {
        p->music = v > 0;
    } else {
        set_dim(p, i, v);
    }
}

/* ---- status text: say what actually went wrong -------------------------------------------------
 * The core keeps the cause (search_error, and yt-dlp's own words for a failed resolve); the readouts used to show
 * only its status code ("ERROR", "NO_RESULTS", "EOF"). */
static bool has(const std::string &hay, const char *needle) {
    std::string h = hay, n = needle;
    for (auto &c : h) c = (char)std::tolower((unsigned char)c);
    for (auto &c : n) c = (char)std::tolower((unsigned char)c);
    return h.find(n) != std::string::npos;
}

static std::string clip(const std::string &s, size_t n) {
    return s.size() <= n ? s : s.substr(0, n - 3) + "...";
}

/* yt-dlp reports "ERROR: [youtube] abc123: Video unavailable. ...": drop the prefix and the id. */
static std::string tidy_error(std::string e) {
    if (e.compare(0, 7, "ERROR: ") == 0) e.erase(0, 7);
    if (!e.empty() && e[0] == '[') {
        size_t colon = e.find(": ");
        if (colon != std::string::npos) e.erase(0, colon + 2);
    }
    return e;
}

/* STATUS is 170 px wide: a short, specific label for why a stream failed (empty = no known failure). */
static std::string stream_failure(const std::string &err, bool dead) {
    if (err.empty()) return dead ? "UNAVAILABLE" : "";
    if (has(err, "yt-dlp is unavailable")) return "YT-DLP MISSING";
    if (has(err, "private")) return "PRIVATE VIDEO";
    if (has(err, "removed") || has(err, "been deleted") || has(err, "terminated")) return "VIDEO REMOVED";
    if (has(err, "copyright")) return "COPYRIGHT";
    if (has(err, "your country") || has(err, "geo")) return "REGION BLOCKED";
    if (has(err, "confirm your age") || has(err, "age-restricted") || has(err, "sign in") ||
        has(err, "inappropriate for some")) return "AGE / LOGIN";
    if (has(err, "429") || has(err, "too many requests")) return "RATE LIMITED";
    if (has(err, "timed out") || has(err, "timeout")) return "TIMED OUT";
    if (has(err, "name or service") || has(err, "name resolution") || has(err, "unreachable") ||
        has(err, "urlopen") || has(err, "connection")) return "NO NETWORK";
    if (dead || has(err, "unavailable") || has(err, "not available")) return "UNAVAILABLE";
    return "RESOLVE FAILED";
}

static std::string stream_text(Plugin *p) {
    std::string st = core_get(p, "stream_status");
    if (st == "eof" || st == "unavailable") {
        std::string why = stream_failure(core_get(p, "stream_error"), st == "unavailable");
        return why.empty() ? "TRACK ENDED" : why;
    }
    return upper(st);
}

/* SEARCH readout: progress, the result count, or the cause. Search causes arrive from the core already worded for
 * this line ("Discogs rejected the token (HTTP 401)", "No playable video in 12 releases tried, ..."). */
static std::string search_text(Plugin *p) {
    std::string st = core_get(p, "search_status");
    if (st == "done") {
        std::string n = core_get(p, "search_count"), ms = core_get(p, "search_elapsed_ms");
        char s[48];
        std::snprintf(s, sizeof s, "DONE - %s RESULTS IN %.1fS", n.c_str(), std::atof(ms.c_str()) / 1000.0);
        return s;
    }
    if (st == "searching") return std::string("SEARCHING ") + upper(SOURCE_NAMES[p->searched_source]) + "...";
    if (st == "queued") return "QUEUED - PREVIOUS SEARCH STILL RUNNING";
    if (st == "error" || st == "no_results") {
        std::string e = core_get(p, "search_error");
        if (!e.empty()) return clip(upper(e), 46);
        return st == "error" ? "SEARCH ERROR" : "NO RESULTS";
    }
    return upper(st);
}

/* NOW PLAYING: the track, or when its stream failed, the track and yt-dlp's reason. */
static std::string now_playing_text(Plugin *p, int c) {
    std::string t = core_get_idx(p, "search_result_title_%d", c), ch = core_get_idx(p, "search_result_channel_%d", c);
    std::string title = ch.empty() ? t : t + " - " + ch;
    std::string st = core_get(p, "stream_status");
    std::string err = st == "eof" || st == "unavailable" ? tidy_error(core_get(p, "stream_error")) : std::string();
    if (err.empty()) return title;
    return clip(t, 28) + "  |  " + clip(err, 52);
}

static std::string display(Plugin *p, int i) {
    switch (PARAMS[i].type) {
    case T_STEPPER:
        if (i == P_PAGE) {
            char s[32];
            std::snprintf(s, sizeof s, "PAGE %d / %d", p->page + 1, page_count(p));
            return s;
        } else if (i == P_SOURCE) {
            return upper(SOURCE_NAMES[p->source]);
        } else if (i == P_MIN_LEN || i == P_MAX_LEN) {
            int m = i == P_MIN_LEN ? MIN_LENS[p->min_len] : MAX_LENS[p->max_len];
            return m ? std::to_string(m) + " MIN" : std::string("ANY");
        } else if (i == P_MUSIC) {
            return p->music ? "ON" : "OFF";
        } else if (i == P_CHANNEL) {
            if (p->channels.empty()) return "NONE - SEE CHANNELS.TXT";
            return clip(upper(p->channels[p->chan].name), 40);
        } else {
            const char *v = dim_value(p, i);
            return v[0] ? upper(v) : std::string("ANY");
        }
    case T_OPTION: return p->kb ? "ON" : "OFF";
    case T_FLOAT: {
        char s[16];
        std::snprintf(s, sizeof s, "%.2f", p->gain);
        return s;
    }
    case T_SLOT: {
        int idx = p->page * SLOTS + (i - P_RESULT_1);
        return idx < result_count(p) ? result_label(p, idx) : std::string();
    }
    case T_READOUT:
        if (i == P_STATUS) return p->core ? stream_text(p) : (p->engine_error.empty() ? std::string("PREPARING ENGINE") : p->engine_error);
        if (i == P_SYNC_STATE) return p->sync ? "SYNC ON" : "SYNC OFF";
        if (i == P_TIME) return core_get(p, "playback_time");
        if (i == P_SEARCH_STATUS) return search_text(p);
        if (i == P_QUERY) return p->query.empty() ? std::string(p->kb ? "_" : "TAP KEYBOARD TO TYPE") : upper(p->query) + (p->kb ? "_" : "");
        if (i == P_NOW_PLAYING) {
            int c = current_result(p);
            if (c < 0) return "";
            return now_playing_text(p, c);
        }
        return "";
    default:
        return "";
    }
}

/* ---- the engine bundle: where bin/yt-dlp, bin/python3, bin/ffmpeg live --------------------------------------------------------------- */
static bool can_run(const std::string &d) {
    return !d.empty() && access((d + "/bin/yt-dlp").c_str(), X_OK) == 0 && access((d + "/bin/python3").c_str(), X_OK) == 0;
}
static bool exists(const std::string &d) {
    struct stat sb;
    return !d.empty() && stat((d + "/bin/yt-dlp").c_str(), &sb) == 0;
}
/* Runs a program without fork() (posix_spawnp) and waits for it. */
static bool run(std::vector<std::string> args) {
    std::vector<char *> argv;
    for (auto &a : args) argv.push_back(const_cast<char *>(a.c_str()));
    argv.push_back(nullptr);
    pid_t pid;
    if (posix_spawnp(&pid, argv[0], nullptr, nullptr, argv.data(), environ) != 0) return false;
    int st = 0;
    while (waitpid(pid, &st, 0) < 0) if (errno != EINTR) return false;
    return WIFEXITED(st) && WEXITSTATUS(st) == 0;
}
/* Returns the folder holding bin/, or "" (error says why). Called on the worker thread: the copy can take seconds. */
static std::string locate_engine(std::string &error, bool &legacy) {
    legacy = false;
    const std::string old = "/sdcard/vst/cratedigger";   /* a 1.x install: it runs programs and the user's channels.txt is there */
    if (can_run(old)) { legacy = true; return old; }
    const std::string src = mpc::contentPath("engine");
    if (!exists(src)) { error = "ENGINE MISSING"; return ""; }
    if (can_run(src)) return src;
    /* The plugin's drive cannot run programs (exFAT): keep a copy where it can. Stamped, so a new plugin version replaces it. */
    char stamp[32];
    std::snprintf(stamp, sizeof stamp, "engine-%d", CD_VERSION);
    for (const char *base : {"/sdcard/vst/.cd-sdk", "/data/cratedigger", "/tmp/cratedigger"}) {
        std::string dest = std::string(base) + "/" + stamp;
        if (can_run(dest)) return dest;
        if (!run({"mkdir", "-p", dest})) continue;
        LOG("copying the engine bundle from %s to %s\n", src.c_str(), dest.c_str());
        if (run({"cp", "-a", src + "/.", dest}) && can_run(dest)) return dest;
        run({"rm", "-rf", dest});
    }
    error = "ENGINE NOT RUNNABLE";
    return "";
}

namespace {
mpc::PluginInfo makeInfo()
{
    mpc::PluginInfo i;
    i.name = CD_NAME;
    i.vendor = "sd88me";
    i.uniqueId = CD_FOURCC(CD_UID);
    i.version = CD_VERSION;
    i.isInstrument = true;
    i.numInputs = 0;
    i.numOutputs = 2;
    return i;
}
}

/* the sticky (lit) buttons: TRANSPORT SYNC, SOURCE x3, MUSIC ONLY. Their value is the state. */
static bool is_sticky(int i) { return i == P_TRANSPORT_SYNC || (i >= P_SOURCE_DISCOGS && i <= P_MUSIC_BTN); }
static bool sticky_on(Engine *p, int i) {
    if (i == P_TRANSPORT_SYNC) return p->sync;
    if (i == P_MUSIC_BTN) return p->music;
    return p->source == i - P_SOURCE_DISCOGS;
}

class CrateDigger : public mpc::Plugin
{
public:
    CrateDigger() : mpc::Plugin(makeInfo())
    {
        int maxStyle = 1, maxCountry = 1;
        for (int g = 0; g < N_CRATEDIG_GENRES; ++g) maxStyle = std::max(maxStyle, styles_for_genre(CRATEDIG_GENRES[g])->n);
        for (int r = 0; r < N_CRATEDIG_REGIONS; ++r) maxCountry = std::max(maxCountry, N_COUNTRIES_BY_REGION[r]);
        for (int i = 0; i < NPARAMS; ++i)
        {
            const param_t &s = PARAMS[i];
            switch (s.type)
            {
            case T_STEPPER:
            {
                int mx = i == P_GENRE ? N_CRATEDIG_GENRES : i == P_STYLE ? maxStyle : i == P_DECADE ? N_CRATEDIG_DECADES
                       : i == P_REGION ? N_CRATEDIG_REGIONS : i == P_COUNTRY ? maxCountry : i == P_PAGE ? 3 : i == P_SOURCE ? NSOURCES
                       : i == P_CHANNEL ? (int)CHANNELS_MAX : i == P_MIN_LEN ? NMIN_LENS : i == P_MAX_LEN ? NMAX_LENS : 2;
                addParam(mpc::intParam(s.key, s.name, 0, mx - 1, 0));
                break;
            }
            case T_FLOAT: addParam(mpc::floatParam(s.key, s.name, s.min, s.max, s.def, "", 2)); break;
            case T_READOUT: addParam(mpc::intParam(s.key, s.name, 0, 255, 0)); break;   // a counter: the text is the value text
            case T_LEVEL: addParam(mpc::intParam(s.key, s.name, 0, 10, 0)); break;      // output level meter: lamps lit, 0..10
            default: addParam(mpc::intParam(s.key, s.name, 0, 1, 0)); break;             // triggers, option, slots
            }
        }
        shown_.assign((size_t)NPARAMS, std::string());
        held_ = new std::atomic<bool>[(size_t)NPARAMS];
        release_ = new std::atomic<bool>[(size_t)NPARAMS];
        last_ = new float[(size_t)NPARAMS];
        for (int i = 0; i < NPARAMS; ++i) { held_[i].store(false); release_[i].store(false); last_[i] = 0.0f; }
        e_.api = move_plugin_init_v2(nullptr);
        worker_ = std::thread(&CrateDigger::workerMain, this);
    }

    ~CrateDigger() override
    {
        quit_.store(true);
        if (worker_.joinable()) worker_.join();
        if (e_.core) e_.api->destroy_instance(e_.core);
        delete[] held_;
        delete[] release_;
        delete[] last_;
    }

    void reset() override { resync_.store(true); }

    // ---- the audio callback: copy from the ring, never wait ---------------------------------------------------------------------------
    void process(mpc::ProcessContext &ctx) override
    {
        if (ctx.numOutputs < 2 || !ctx.outputs) return;
        if (sync_.load())
        {
            const bool now = ctx.transport.valid && ctx.transport.playing;
            if (now != e_.transport_playing.load()) { e_.transport_playing.store(now); e_.transport_edge.store(now ? 1 : -1); }
        }
        const int n = ctx.numFrames;
        float pkL = 0.0f, pkR = 0.0f;
        uint32_t r = e_.rpos.load(), avail = e_.wpos.load() - r;
        float *l = ctx.outputs[0], *rr = ctx.outputs[1];
        for (int i = 0; i < n; ++i)
        {
            if ((uint32_t)i < avail)
            {
                uint32_t k = (r + (uint32_t)i) & (RING - 1);
                l[i] = e_.ring[k * 2] * (1.0f / 32768.0f);
                rr[i] = e_.ring[k * 2 + 1] * (1.0f / 32768.0f);
                pkL = std::max(pkL, std::fabs(l[i]));
                pkR = std::max(pkR, std::fabs(rr[i]));
            }
            else l[i] = rr[i] = 0.0f;   // underrun: silence
        }
        // the level meter: the block peak, falling away between blocks (read by the worker, which tells the host)
        peakL_.store(std::max(pkL, peakL_.load() * 0.96f));
        peakR_.store(std::max(pkR, peakR_.load() * 0.96f));
        e_.rpos.store(r + ((uint32_t)n < avail ? (uint32_t)n : avail));
    }

    // ---- parameters: a host change (touch, jog, Q-Link) arrives here --------------------------------------------------------------------
    void parameterChanged(int index, float plain) override
    {
        if (index < 0 || index >= NPARAMS) return;
        const param_t &s = PARAMS[index];
        std::lock_guard<std::mutex> lk(e_.lock);
        switch (s.type)
        {
        case T_STEPPER:
            if (index == P_GENRE && !loading_.load())
            {   // the host nudges parameter 0 to its top and straight back on every prepare: only a value that stays ~40 ms counts
                pendingGenre_ = (int)std::lround(plain);
                pendingAt_.store(nowMs());
                return;
            }
            stepper_set(&e_, index, (int)std::lround(plain));
            dirty_.store(true);
            return;
        case T_OPTION: if (index == P_KB && !loading_.load()) e_.kb = plain > 0.5f; return;   // the popup keyboard is not part of a saved state
        case T_FLOAT:
        {
            char b[32];
            e_.gain = plain;
            std::snprintf(b, sizeof b, "%.3f", plain);
            core_set(&e_, "gain", b);
            return;
        }
        case T_SLOT:
        {   // a touch changes the row's value (it reads 1 while that row plays): play on any change
            const bool fire = std::fabs(plain - last_[index]) > 0.25f;
            last_[index] = plain;
            const int idx = e_.page * SLOTS + (index - P_RESULT_1);
            if (fire && !loading_.load() && idx < result_count(&e_)) play_result(&e_, idx);
            dirty_.store(true);
            return;
        }
        case T_TRIGGER:
            if (is_sticky(index)) { stickyChanged(index, plain); return; }
            break;
        default: return;
        }
        // momentary buttons: a rising edge fires once; the worker drops the value back to 0 (the echo of that is not a press)
        if (plain < 0.5f) { held_[index].store(false); return; }
        if (held_[index].exchange(true) || loading_.load()) return;
        release_[index].store(true);
        press(index);
    }

    bool formatValue(int index, float, std::string &out) override
    {
        if (index < 0 || index >= NPARAMS) return false;
        if (PARAMS[index].type == T_TRIGGER) { out = ""; return true; }
        std::lock_guard<std::mutex> lk(e_.lock);
        out = display(&e_, index);
        return true;
    }

    // ---- state ----------------------------------------------------------------------------------------------------------------------
    void saveExtraState(std::vector<uint8_t> &out) override
    {
        std::lock_guard<std::mutex> lk(e_.lock);
        const std::string s = "q=" + e_.query;
        out.assign(s.begin(), s.end());
    }
    void loadExtraState(const uint8_t *data, size_t size) override
    {
        if (!data || size < 2 || std::memcmp(data, "q=", 2) != 0) return;
        std::lock_guard<std::mutex> lk(e_.lock);
        e_.query = std::string(reinterpret_cast<const char *>(data) + 2, size - 2).substr(0, QUERY_MAX);
    }

    // A project saved by the 1.x wrapper build: "g=..;s=..;d=..;r=..;c=..;gain=..;src=..;ch=..;ml=..;xl=..;mu=..;q=..".
    bool loadLegacy(const char *data, size_t size)
    {
        if (!data || size == 0) return false;
        char s[320];
        const size_t n = std::min(size, sizeof s - 1);
        std::memcpy(s, data, n);
        s[n] = 0;
        int g = 0, st = 0, d = 0, r = 0, c = 0;
        float gn = 1.0f;
        int got = std::sscanf(s, "g=%d;s=%d;d=%d;r=%d;c=%d;gain=%f", &g, &st, &d, &r, &c, &gn);
        LOG("legacy effSetChunk '%s' parsed=%d\n", s, got);
        if (got < 5) return false;   // not one of ours: keep the current filters
        int src = SRC_DISCOGS, ch = 0, ml = 0, xl = 0, mu = 0;
        if (const char *tail = std::strstr(s, ";src=")) std::sscanf(tail, ";src=%d;ch=%d;ml=%d;xl=%d;mu=%d", &src, &ch, &ml, &xl, &mu);
        if (got < 6 || !(gn >= 0.0f && gn <= 4.0f)) gn = 1.0f;
        std::lock_guard<std::mutex> lk(e_.lock);
        e_.page = 0;
        e_.source = src < 0 || src >= NSOURCES ? SRC_DISCOGS : src;
        e_.chan = ch < 0 ? 0 : ch;
        e_.min_len = ml < 0 || ml >= NMIN_LENS ? 0 : ml;
        e_.max_len = xl < 0 || xl >= NMAX_LENS ? 0 : xl;
        e_.music = mu == 1;
        e_.query.clear();
        if (const char *q = std::strstr(s, ";q=")) e_.query = std::string(q + 3).substr(0, QUERY_MAX);
        set_dim(&e_, DIM_GENRE, g); set_dim(&e_, DIM_STYLE, st); set_dim(&e_, DIM_DECADE, d);
        set_dim(&e_, DIM_REGION, r); set_dim(&e_, DIM_COUNTRY, c);
        e_.gain = gn;
        char gs[32];
        std::snprintf(gs, sizeof gs, "%.3f", gn);
        core_set(&e_, "gain", gs);
        resync_.store(true);
        return true;
    }

    std::atomic<bool> loading_{false};   // set around a state load (wrapped effSetChunk)
    void requestResync() { resync_.store(true); dirty_.store(true); }

private:
    static long long nowMs()
    {
        return std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now().time_since_epoch()).count();
    }

    // A lit button changed. Under lock. SOURCE x3 pick their source on a value above 0.5. MUSIC ONLY and TRANSPORT SYNC are toggles: the MPC
    // sends one tap on a lit button as two events ~130 ms apart (a Live III log: 1 then 0 when switching off, 0 then 1 when on), so the value
    // means nothing; each tap flips the state once and events within TAP_GAP_MS of that are its second event. The worker tells the host the
    // real state again, so a tap the MPC turned "off" lights up again.
    void stickyChanged(int i, float plain)
    {
        if (i >= P_SOURCE_DISCOGS && i < P_MUSIC_BTN) { if (plain > 0.5f) e_.source = i - P_SOURCE_DISCOGS; dirty_.store(true); return; }
        const auto now = std::chrono::steady_clock::now();
        if (std::chrono::duration_cast<std::chrono::milliseconds>(now - pressAt_[i]).count() < TAP_GAP_MS) return;
        pressAt_[i] = now;
        if (i == P_MUSIC_BTN) e_.music = !e_.music;
        else   // P_TRANSPORT_SYNC
        {
            e_.sync = !e_.sync;
            sync_.store(e_.sync);
            e_.transport_playing.store(false);
            e_.transport_edge.store(0);
            if (!e_.sync && e_.hold) { e_.hold = false; core_set(&e_, "hold_start", "0"); }
            LOG("transport sync %s\n", e_.sync ? "on" : "off");
        }
        dirty_.store(true);
    }

    // A momentary button was pressed. Under lock. The old wrapper's setParameter() body, minus its MPC-event workarounds.
    void press(int i)
    {
        Engine *p = &e_;
        if (i >= P_GENRE_PREV && i <= P_COUNTRY_NEXT)   /* arrows wrap: ANY <-> last entry */
        {
            int d = (i - P_GENRE_PREV) / 2, dir = ((i - P_GENRE_PREV) % 2) ? 1 : -1, n = dim_count(p, d);
            set_dim(p, d, (p->dim[d] + dir + n) % n);
        }
        else if (i == P_PAGE_PREV || i == P_PAGE_NEXT)
        {
            int n = page_count(p);
            stepper_set(p, P_PAGE, (p->page + (i == P_PAGE_NEXT ? 1 : -1) + n) % n);
        }
        else if (i == P_SOURCE_PREV || i == P_SOURCE_NEXT)
            stepper_set(p, P_SOURCE, (p->source + (i == P_SOURCE_NEXT ? 1 : -1) + NSOURCES) % NSOURCES);
        else if (i == P_CHANNEL_PREV || i == P_CHANNEL_NEXT)
        {
            int n = stepper_count(p, P_CHANNEL);
            stepper_set(p, P_CHANNEL, (p->chan + (i == P_CHANNEL_NEXT ? 1 : -1) + n) % n);
        }
        else if (i >= P_MIN_LEN_PREV && i <= P_MUSIC_NEXT)   /* arrows wrap */
        {
            int d = (i - P_MIN_LEN_PREV) / 2, dir = ((i - P_MIN_LEN_PREV) % 2) ? 1 : -1, sp = P_MIN_LEN + d, n = stepper_count(p, sp);
            stepper_set(p, sp, (stepper_index(p, sp) + dir + n) % n);
        }
        else if (i == P_KEYS) p->kb = true;
        else if (is_key(i))
        {
            // a repeat of the same key within KEY_REPEAT_MS is one tap delivered twice, not a second letter
            auto now = std::chrono::steady_clock::now();
            long ms = p->last_key == i ? (long)std::chrono::duration_cast<std::chrono::milliseconds>(now - p->last_key_at).count() : 1 << 20;
            if (ms >= KEY_REPEAT_MS) { p->last_key = i; p->last_key_at = now; type_key(p, PARAMS[i].key + 2); }
        }
        else if (i == P_FIND_SEARCH || i == P_SEARCH)
        {
            auto now = std::chrono::steady_clock::now();
            if (now - p->search_at > std::chrono::milliseconds(500)) { p->search_at = now; do_search(p, i == P_FIND_SEARCH); }
        }
        else if (i == P_PLAY_PAUSE && p->hold) { p->hold = false; core_set(p, "hold_start", "0"); }   // manual start while waiting for MPC's Play
        else if (i == P_PLAY_PAUSE)
        {
            if (core_get(p, "stream_url").empty()) play_result(p, std::atoi(core_get(p, "cratedig_result_index").c_str()));
            else core_set(p, "play_pause_step", "trigger");
        }
        else if (i == P_STOP) core_set(p, "stop_step", "trigger");
        else if (i == P_REWIND_15) core_set(p, "rewind_15_step", "trigger");
        else if (i == P_FORWARD_15) core_set(p, "forward_15_step", "trigger");
        dirty_.store(true);
    }

    void store(int i, float plain) { values_[(size_t)i]->store(param(i).toNormalised(plain), std::memory_order_relaxed); }

    // The value the host should show for a parameter, from the plugin's own state. Under lock.
    float want(int i)
    {
        switch (PARAMS[i].type)
        {
        case T_STEPPER: return (float)stepper_index(&e_, i);
        case T_OPTION: return e_.kb ? 1.0f : 0.0f;
        case T_FLOAT: return e_.gain;
        case T_SLOT: return current_result(&e_) == e_.page * SLOTS + (i - P_RESULT_1) ? 1.0f : 0.0f;
        case T_TRIGGER: return is_sticky(i) && sticky_on(&e_, i) ? 1.0f : 0.0f;
        case T_LEVEL:
            if (i == P_PLAY_STATE) return playState();
            return lamps(i == P_LEVEL_L ? peakL_.load() : peakR_.load());
        default: return 0.0f;
        }
    }

    // for the PLAY and STOP lamps: 0 stopped, 1 streaming, 2 paused, 3 buffering or waiting for MPC's Play. Under lock.
    float playState()
    {
        if (!e_.core) return 0.0f;
        const std::string st = core_get(&e_, "stream_status");
        if (e_.hold && !core_get(&e_, "stream_url").empty()) return 3.0f;
        if (st == "streaming") return 1.0f;
        if (st == "paused") return 2.0f;
        if (st == "buffering" || st == "loading") return 3.0f;
        return 0.0f;
    }

    // peak -> lit lamps 0..10 on a dB ladder (-48 .. 0)
    static float lamps(float peak)
    {
        static const float th[10] = {-48, -36, -24, -18, -12, -9, -6, -3, -1, 0};
        const float db = 20.0f * std::log10(std::max(peak, 1e-6f));
        int n = 0;
        for (float t : th) if (db >= t - 0.01f) ++n;
        return (float)n;
    }

    // One worker pass (every ~50 ms): release buttons, keep the host in step with the state, ask it to re-read changed text.
    void uiPass(bool force)
    {
        const long long pg = pendingAt_.load();
        if (pg && (force || nowMs() - pg >= 40))
        {
            pendingAt_.store(0);
            std::lock_guard<std::mutex> lk(e_.lock);
            if (pendingGenre_ != e_.dim[DIM_GENRE]) { stepper_set(&e_, P_GENRE, pendingGenre_); }
        }
        if (int edge = e_.transport_edge.exchange(0))
        {
            std::lock_guard<std::mutex> lk(e_.lock);
            if (e_.sync) transport_edge_locked(&e_, edge > 0);
        }
        for (int i = 0; i < NPARAMS; ++i)
            if (release_[i].load()) { release_[i].store(false); held_[i].store(false); last_[i] = 0.0f; store(i, 0.0f); notifyHostParameterChanged(i); }
        if (resync_.exchange(false)) { std::fill(shown_.begin(), shown_.end(), std::string("\x01")); }
        bool textChanged = false;
        std::vector<int> push;
        {
            std::lock_guard<std::mutex> lk(e_.lock);
            load_channels(&e_);
            for (int i = 0; i < NPARAMS; ++i)
            {
                if (PARAMS[i].type == T_TRIGGER && !is_sticky(i)) continue;
                // the host's stored value follows the plugin's state (a lit button the host just switched off lights again)
                if (PARAMS[i].type != T_READOUT && !(i == P_GENRE && pendingAt_.load()) && std::fabs(want(i) - get(i)) > 1e-4f) push.push_back(i);
                if (PARAMS[i].type != T_TRIGGER)
                {
                    std::string t = display(&e_, i);
                    if (t != shown_[(size_t)i])
                    {
                        shown_[(size_t)i] = t;
                        textChanged = true;
                        if (PARAMS[i].type == T_READOUT) push.push_back(i);   // the counter moves so the host sees an event
                    }
                }
            }
        }
        for (int i : push)
        {
            float v;
            if (PARAMS[i].type == T_READOUT) { counter_[i] = (counter_[i] + 1) & 255; v = (float)counter_[i]; }
            else { std::lock_guard<std::mutex> lk(e_.lock); v = want(i); }
            store(i, v);
            notifyHostParameterChanged(i);
        }
        if (textChanged) requestDisplayUpdate();
    }

    void workerMain()
    {
        if (!e_.api) { std::lock_guard<std::mutex> lk(e_.lock); e_.engine_error = "ENGINE API MISSING"; }
        else
        {
            std::string err;
            bool legacy = false;
            const std::string dir = locate_engine(err, legacy);
            std::lock_guard<std::mutex> lk(e_.lock);
            if (dir.empty()) e_.engine_error = err;
            else
            {
                e_.channels_path = (legacy ? dir : mpc::pluginFolder()) + "/channels.txt";
                e_.core = e_.api->create_instance(dir.c_str(), nullptr);
                if (!e_.core) e_.engine_error = "ENGINE FAILED TO START";
                else { core_set(&e_, "search_provider", "cratedig"); core_set(&e_, "gain", "1.000"); }
            }
            LOG("engine '%s' core=%p %s\n", dir.c_str(), e_.core, e_.engine_error.c_str());
        }
        int16_t block[BLOCK * 2];
        auto nextUi = std::chrono::steady_clock::now();
        while (!quit_.load())
        {
            auto now = std::chrono::steady_clock::now();
            if (now >= nextUi) { nextUi = now + std::chrono::milliseconds(50); uiPass(false); }
            uint32_t fill = e_.wpos.load() - e_.rpos.load();
            if (!e_.core || fill + BLOCK > (uint32_t)TARGET_FILL) { std::this_thread::sleep_for(std::chrono::milliseconds(2)); continue; }
            { std::lock_guard<std::mutex> lk(e_.lock); e_.api->render_block(e_.core, block, BLOCK); }
            uint32_t w = e_.wpos.load();
            for (int i = 0; i < BLOCK; ++i)
            {
                uint32_t k = (w + (uint32_t)i) & (RING - 1);
                e_.ring[k * 2] = block[i * 2];
                e_.ring[k * 2 + 1] = block[i * 2 + 1];
            }
            e_.wpos.store(w + BLOCK);
        }
    }

public:
#ifdef CD_TEST
    Engine &engine() { return e_; }
    void passNow() { uiPass(true); }
    std::string textOf(int i) { std::lock_guard<std::mutex> lk(e_.lock); return display(&e_, i); }
    float valueOf(int i) { return get(i); }
#endif
private:
    Engine e_;
    std::thread worker_;
    std::atomic<bool> quit_{false}, resync_{false}, dirty_{false}, sync_{false};
    std::atomic<long long> pendingAt_{0};
    std::atomic<float> peakL_{0.0f}, peakR_{0.0f};
    int pendingGenre_ = 0;
    std::atomic<bool> *held_ = nullptr, *release_ = nullptr;
    float *last_ = nullptr;
    std::vector<std::string> shown_;
    int counter_[NPARAMS] = {0};
    std::chrono::steady_clock::time_point pressAt_[NPARAMS];   // when each toggle last flipped
};

// The same entry as MPC_PLUGIN_ENTRY, plus two wrapped dispatcher ops: effSetChunk reads a 1.x wrapper project, and effGetParamDisplay lets the
// text parameters (status, now playing, result rows) be longer than the SDK's 31 characters (the MPC reads up to 100).
namespace {
VstIntPtr (*g_origDispatcher)(AEffect *, VstInt32, VstInt32, VstIntPtr, void *, float) = nullptr;

VstIntPtr cdDispatcher(AEffect *e, VstInt32 opcode, VstInt32 index, VstIntPtr value, void *ptr, float opt)
{
    if (opcode == effSetChunk && e->object && ptr)
    {
        CrateDigger *p = static_cast<CrateDigger *>(e->object);
        if (value >= 4 && std::memcmp(ptr, "MPCP", 4) == 0)
        {
            p->loading_.store(true);
            const VstIntPtr r = g_origDispatcher(e, opcode, index, value, ptr, opt);
            p->loading_.store(false);
            p->requestResync();
            return r;
        }
        return p->loadLegacy(static_cast<const char *>(ptr), (size_t)value) ? 1 : 0;
    }
    if (opcode == effGetParamDisplay && e->object && ptr && index >= 0 && index < NPARAMS && PARAMS[index].type != T_TRIGGER)
    {
        std::string s = static_cast<CrateDigger *>(e->object)->displayText(index);
        std::strncpy(static_cast<char *>(ptr), s.c_str(), 99);
        static_cast<char *>(ptr)[99] = 0;
        return 0;
    }
    return g_origDispatcher(e, opcode, index, value, ptr, opt);
}
} // namespace

extern "C" MPC_EXPORT AEffect *VSTPluginMain(audioMasterCallback host)
{
    if (host != nullptr && host(nullptr, audioMasterVersion, 0, 0, nullptr, 0.0f) == 0) return nullptr;   // host is VST1 only
    if (!g_log) g_log = std::fopen("/tmp/cratedigger_vst.log", "a");
    // A write to a dead child's pipe must not kill the MPC. Only touch SIGPIPE if the host left it at the default.
    struct sigaction sa;
    if (sigaction(SIGPIPE, nullptr, &sa) == 0 && sa.sa_handler == SIG_DFL) signal(SIGPIPE, SIG_IGN);
    AEffect *e = mpc::detail::createEffect(new CrateDigger(), host);
    if (e && !g_origDispatcher) g_origDispatcher = e->dispatcher;
    if (e) e->dispatcher = cdDispatcher;
    return e;
}
