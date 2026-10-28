/* =============================================================================
 * cratedigger_vst.cpp - Crate Digger as a VST2 instrument for the MPC OS plugin
 * host (see https://github.com/sd88me/mpc-vst-plugins). The same schwung-webstream
 * DSP core the Force host (src/cratedigger_host.cpp) links, built with
 * -DYT_POSIX_SPAWN (no fork() inside MPC), plus this host glue:
 *
 *  - The core renders on a worker thread into a ring buffer; MPC's audio callback
 *    only copies from the ring. The core starts ffmpeg pipelines, takes locks and
 *    reads pipes from inside render_block, none of which may happen on MPC's
 *    audio thread.
 *  - The Force host's control-socket glue (filter steppers, SEARCH, transport,
 *    result list) becomes VST parameters whose value text MPC polls for display
 *    (verified: mpc-vst-plugins docs/NOTES.md "Dynamic text in skins").
 *  - Parameter table: params.json -> build/params_gen.h (gen_params.py).
 * ========================================================================== */
#include <atomic>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <mutex>
#include <string>
#include <vector>
#include <thread>
#include <dlfcn.h>
#include <glob.h>
#include <signal.h>
#include <unistd.h>
#include <sys/stat.h>

#include "plugin_api_v1.h"
#include "cratedig_tables.h"
#include "params_gen.h"

extern "C" plugin_api_v2_t *move_plugin_init_v2(const host_api_v1_t *host);

/* ---- VST2 ABI (hand-written; no Steinberg SDK) ---------------------------- */
struct AEffect;
typedef intptr_t (*audioMasterCallback)(AEffect *, int32_t, int32_t, intptr_t, void *, float);
struct AEffect {
    int32_t magic;
    intptr_t (*dispatcher)(AEffect *, int32_t, int32_t, intptr_t, void *, float);
    void (*process)(AEffect *, float **, float **, int32_t);
    void (*setParameter)(AEffect *, int32_t, float);
    float (*getParameter)(AEffect *, int32_t);
    int32_t numPrograms, numParams, numInputs, numOutputs, flags;
    intptr_t resvd1, resvd2;
    int32_t initialDelay, realQualities, offQualities;
    float ioRatio;
    void *object, *user;
    int32_t uniqueID, version;
    void (*processReplacing)(AEffect *, float **, float **, int32_t);
    void (*processDoubleReplacing)(AEffect *, double **, double **, int32_t);
    char future[56];
};
enum {
    effOpen = 0, effClose = 1, effGetParamLabel = 6, effGetParamDisplay = 7, effGetParamName = 8,
    effSetSampleRate = 10, effSetBlockSize = 11, effMainsChanged = 12, effGetChunk = 23, effSetChunk = 24,
    effProcessEvents = 25, effCanBeAutomated = 26, effGetPlugCategory = 35, effGetEffectName = 45,
    effGetVendorString = 47, effGetProductString = 48, effGetVendorVersion = 49, effCanDo = 51, effGetVstVersion = 58,
};
enum { audioMasterAutomate = 0, audioMasterGetTime = 7, audioMasterUpdateDisplay = 42 };
enum { kVstTransportPlaying = 1 << 1 };
struct VstTimeInfo {
    double samplePos, sampleRate, nanoSeconds, ppqPos, tempo, barStartPos, cycleStartPos, cycleEndPos;
    int32_t timeSigNumerator, timeSigDenominator, smpteOffset, smpteFrameRate, samplesToNextClock, flags;
};
enum { effFlagsCanReplacing = 1 << 4, effFlagsProgramChunks = 1 << 5, effFlagsIsSynth = 1 << 8 };

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
static const long KEY_REPEAT_MS = 150;   /* same popup key twice inside this is one tap */
struct Channel { std::string link, name; };   /* one line of channels.txt */

struct Plugin {
    AEffect fx;
    audioMasterCallback master;
    plugin_api_v2_t *api;
    void *core;
    std::mutex lock;                      /* serialises every core call */
    int16_t ring[RING * 2];
    std::atomic<uint32_t> wpos{0}, rpos{0};
    std::thread worker;
    std::atomic<bool> running{false};
    int dim[NDIMS] = {0, 0, 0, 0, 0};     /* filter selection (like the host's g_cd_*_idx) */
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
    int last_key = -1;                    /* the popup keyboard's last key and when, to drop MPC's repeat of one tap */
    std::chrono::steady_clock::time_point last_key_at;
    std::chrono::steady_clock::time_point press_at[NPARAMS];   /* when each sticky button last went down, and the last search press */
    std::chrono::steady_clock::time_point search_at;
    std::atomic<bool> sticky_dirty{false};   /* a sticky button was set: push the lit states back to MPC */
    int searched_source = SRC_DISCOGS;    /* what the last SEARCH asked, for the status text */
    volatile char release[NPARAMS];       /* triggers to report back to 0 */
    float step_seen[NPARAMS];             /* last raw value MPC sent to each stepper (-1 = none yet) */
    float last[NPARAMS];                  /* last value MPC set, per param (triggers fire on change) */
    /* Transport Sync: a tapped result loads and buffers, then waits for MPC's Play. */
    bool sync = false;                    /* under lock */
    bool hold = false;                    /* under lock: a track is buffered and waiting */
    bool sync_started = false;            /* under lock: MPC Play released the current track */
    std::atomic<bool> transport_playing{false};
    std::atomic<int> transport_edge{0};   /* +1 = MPC started, -1 = MPC stopped; worker consumes */
    std::string shown;                    /* all display text at the last UpdateDisplay */
    char chunk[320];
};

/* ---- small helpers -------------------------------------------------------- */
static FILE *g_log;
/* [sec.msec] prefix lines up against the engine's own /tmp/webstream-runtime.log (also
 * wall-clock-stamped), so a bug report's two log files can be read as one timeline. */
#define LOG(...) do { if (g_log) { \
        auto __now = std::chrono::system_clock::now().time_since_epoch(); \
        long long __ms = std::chrono::duration_cast<std::chrono::milliseconds>(__now).count(); \
        std::fprintf(g_log, "[%lld.%03lld] ", __ms / 1000, __ms % 1000); \
        std::fprintf(g_log, __VA_ARGS__); std::fflush(g_log); \
    } } while (0)

static std::string core_get(Plugin *p, const char *key) {
    char buf[512];
    int n = p->api->get_param(p->core, key, buf, sizeof buf);
    return n > 0 ? std::string(buf, (size_t)(n < (int)sizeof buf ? n : (int)sizeof buf - 1)) : std::string();
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
static void copy_str(void *dst, const std::string &s, size_t max) {
    std::strncpy((char *)dst, s.c_str(), max - 1);
    ((char *)dst)[max - 1] = 0;
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
    p->dim[d] = i;
    if (d == DIM_GENRE) p->dim[DIM_STYLE] = 0;       /* style list depends on genre */
    if (d == DIM_REGION) p->dim[DIM_COUNTRY] = 0;    /* country list depends on region */
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
    p->api->set_param(p->core, "hold_start", p->hold ? "1" : "0");
    p->api->set_param(p->core, "stream_provider", prov.empty() ? "youtube" : prov.c_str());
    p->api->set_param(p->core, "stream_url", url.c_str());
    p->api->set_param(p->core, "cratedig_result_index", s);
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

/* The popup keyboard: letters and digits are typed lower case (the search ignores case), the keys' names are in params.json. */
/* The FIND tab's lit buttons (SOURCE x3, MUSIC ONLY) are sticky like TRANSPORT SYNC: a tap picks the value, getParameter reports it. */
static bool is_sticky(int i) { return i == P_TRANSPORT_SYNC || (i >= P_SOURCE_DISCOGS && i <= P_MUSIC_BTN); }
static bool sticky_on(Plugin *p, int i) {
    if (i == P_TRANSPORT_SYNC) return p->sync;
    if (i == P_MUSIC_BTN) return p->music;
    return p->source == i - P_SOURCE_DISCOGS;
}
/* A sticky toggle's new state. MPC sends a tap on a lit button as two events ~130 ms apart (a Live III log: 1 then 0 when off, 0 then 1
 * when on): the first is the tap, the second puts the old value back. The value therefore means nothing; each tap flips the state once
 * and events within TAP_GAP_MS of it are that second event (a Force, which sends one event, is covered too). */
static const long TAP_GAP_MS = 300;
static bool sticky_toggle(Plugin *p, int i, bool &state) {
    auto now = std::chrono::steady_clock::now();
    if (std::chrono::duration_cast<std::chrono::milliseconds>(now - p->press_at[i]).count() < TAP_GAP_MS) return false;
    p->press_at[i] = now;
    state = !state;
    return true;
}

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
    p->api->set_param(p->core, "cratedig_filter", json.c_str());
}

static std::string display(Plugin *p, int i);

/* MPC only re-reads parameter text after audioMasterUpdateDisplay (verified: without it,
 * readouts stay frozen). Called from the worker a few times a second; notifies only on change. */
static void refresh_display(Plugin *p) {
    std::string all;
    {
        std::lock_guard<std::mutex> lk(p->lock);
        load_channels(p);
        for (int i = 0; i < NPARAMS; i++)
            if (PARAMS[i].type != T_TRIGGER) { all += display(p, i); all += '\x1f'; }
    }
    if (all != p->shown) {
        p->shown = all;
        p->master(&p->fx, audioMasterUpdateDisplay, 0, 0, nullptr, 0.0f);
    }
}

/* Triggers go back to 0 from here, not the audio callback (MPC may not call process() for a
 * silent track). */
static void flush_releases(Plugin *p) {
    if (p->sticky_dirty.exchange(false))
        for (int i = P_TRANSPORT_SYNC; i <= P_MUSIC_BTN; i = i == P_TRANSPORT_SYNC ? P_SOURCE_DISCOGS : i + 1)
            p->master(&p->fx, audioMasterAutomate, i, 0, nullptr, sticky_on(p, i) ? 1.0f : 0.0f);
    for (int i = 0; i < NPARAMS; i++)
        if (p->release[i]) { p->release[i] = 0; p->last[i] = 0.0f; p->master(&p->fx, audioMasterAutomate, i, 0, nullptr, 0.0f); }
}

/* MPC Play releases a buffered track (or resumes a paused one); MPC Stop pauses it. */
static void transport_edge_locked(Plugin *p, bool playing) {
    std::string st = core_get(p, "stream_status");
    LOG("transport %s: hold=%d stream_status=%s\n", playing ? "play" : "stop", p->hold, st.c_str());
    if (playing) {
        if (p->hold) {
            p->hold = false;
            p->sync_started = true;
            p->api->set_param(p->core, "hold_start", "0");
        } else if (st == "paused") {
            p->api->set_param(p->core, "play_pause_toggle", "1");
        }
    } else if (!p->hold && (st == "streaming" || st == "buffering")) {
        p->api->set_param(p->core, "play_pause_toggle", "1");
    }
}

/* ---- worker: the core renders here, never on MPC's audio thread ------------ */
static void worker_main(Plugin *p) {
    int16_t block[BLOCK * 2];
    auto next_ui = std::chrono::steady_clock::now();
    while (p->running.load()) {
        auto now = std::chrono::steady_clock::now();
        if (now >= next_ui) {
            next_ui = now + std::chrono::milliseconds(200);
            flush_releases(p);
            refresh_display(p);
        }
        if (int edge = p->transport_edge.exchange(0)) {
            std::lock_guard<std::mutex> lk(p->lock);
            if (p->sync) transport_edge_locked(p, edge > 0);
        }
        uint32_t fill = p->wpos.load() - p->rpos.load();
        if (fill + BLOCK > (uint32_t)TARGET_FILL) {
            std::this_thread::sleep_for(std::chrono::milliseconds(2));
            continue;
        }
        {
            std::lock_guard<std::mutex> lk(p->lock);
            p->api->render_block(p->core, block, BLOCK);
        }
        uint32_t w = p->wpos.load();
        for (int i = 0; i < BLOCK; i++) {
            uint32_t k = (w + i) & (RING - 1);
            p->ring[k * 2] = block[i * 2];
            p->ring[k * 2 + 1] = block[i * 2 + 1];
        }
        p->wpos.store(w + BLOCK);
    }
}

static void processReplacing(AEffect *e, float **in, float **out, int32_t n) {
    Plugin *p = (Plugin *)e->object;
    (void)in;
    if (p->sync) {
        VstTimeInfo *ti = (VstTimeInfo *)p->master(&p->fx, audioMasterGetTime, 0, kVstTransportPlaying, nullptr, 0.0f);
        bool now = ti && (ti->flags & kVstTransportPlaying);
        if (now != p->transport_playing.load()) {
            p->transport_playing.store(now);
            p->transport_edge.store(now ? 1 : -1);
        }
    }
    uint32_t r = p->rpos.load(), avail = p->wpos.load() - r;
    for (int32_t i = 0; i < n; i++) {
        if ((uint32_t)i < avail) {
            uint32_t k = (r + i) & (RING - 1);
            out[0][i] = p->ring[k * 2] * (1.0f / 32768.0f);
            out[1][i] = p->ring[k * 2 + 1] * (1.0f / 32768.0f);
        } else {
            out[0][i] = out[1][i] = 0.0f;   /* underrun: silence, never wait */
        }
    }
    p->rpos.store(r + ((uint32_t)n < avail ? (uint32_t)n : avail));
}

/* ---- parameters ----------------------------------------------------------- */
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
    return p->dim[i];
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

static float getParameter(AEffect *e, int32_t i) {
    Plugin *p = (Plugin *)e->object;
    if (i < 0 || i >= NPARAMS) return 0;
    std::lock_guard<std::mutex> lk(p->lock);
    switch (PARAMS[i].type) {
    case T_STEPPER: {
        int n = stepper_count(p, i);
        return n > 1 ? (float)stepper_index(p, i) / (n - 1) : 0.0f;
    }
    case T_OPTION: return p->kb ? 1.0f : 0.0f;
    case T_FLOAT: return (p->gain - PARAMS[i].min) / (PARAMS[i].max - PARAMS[i].min);
    case T_SLOT: return current_result(p) == p->page * SLOTS + (i - P_RESULT_1) ? 1.0f : 0.0f;
    case T_TRIGGER: return is_sticky(i) && sticky_on(p, i) ? 1.0f : 0.0f;   /* sticky: lights the button */
    default: return 0.0f;
    }
}

static void setParameter(AEffect *e, int32_t i, float v) {
    Plugin *p = (Plugin *)e->object;
    if (i < 0 || i >= NPARAMS) return;
    std::lock_guard<std::mutex> lk(p->lock);
    switch (PARAMS[i].type) {
    case T_STEPPER: {
        /* Step relative to the last value MPC sent, not by rounding its absolute value: one
         * jog detent moves MPC's 0..1 value by well under half a step, so round(v*(n-1)) left
         * the index unchanged until several clicks piled up (the 1-2 s "delay" on a single
         * click), while a fast spin, whose values do cross steps, felt fine. Any change now
         * moves at least one step in its direction; a bigger jump moves proportionally more.
         * MPC echoing back the position we report (getParameter) is ignored.
         */
        int n = stepper_count(p, i);
        if (n < 2) return;
        v = v < 0 ? 0 : v > 1 ? 1 : v;
        int cur = stepper_index(p, i);
        float shown_v = (float)cur / (n - 1);
        float base = p->step_seen[i] < 0 ? shown_v : p->step_seen[i];
        p->step_seen[i] = v;
        if (std::fabs(v - shown_v) < 1e-4f) return;
        float dv = v - base;
        if (std::fabs(dv) < 1e-6f) dv = v - shown_v;
        int steps = (int)std::lround(std::fabs(dv) * (n - 1));
        if (steps < 1) steps = 1;
        int target = cur + (dv > 0 ? steps : -steps);
        if (target < 0) target = 0; else if (target > n - 1) target = n - 1;
        stepper_set(p, i, target);
        return;
    }
    case T_OPTION:
        if (i == P_KB) p->kb = v > 0.5f;
        return;
    case T_FLOAT: {
        char s[32];
        p->gain = PARAMS[i].min + (PARAMS[i].max - PARAMS[i].min) * (v < 0 ? 0 : v > 1 ? 1 : v);
        std::snprintf(s, sizeof s, "%.3f", p->gain);
        p->api->set_param(p->core, "gain", s);
        return;
    }
    case T_SLOT: {
        /* A touch toggles the row's value (it reads 1 while that row plays): play on any change. */
        bool fire = std::fabs(v - p->last[i]) > 0.25f;
        p->last[i] = v;
        int idx = p->page * SLOTS + (i - P_RESULT_1);
        if (fire && idx < result_count(p)) play_result(p, idx);
        return;
    }
    case T_TRIGGER:
        if (i >= P_SOURCE_DISCOGS && i <= P_MUSIC_BTN) {
            LOG("sticky %s v=%.2f (source=%d music=%d)\n", PARAMS[i].key, v, p->source, p->music ? 1 : 0);
            /* A tap on SOURCE picks that source (a tap on the lit one changes nothing); MUSIC ONLY follows MPC's toggle. Either way
             * MPC is told the real states again, so a tap that MPC turned "off" lights up again. */
            if (i == P_MUSIC_BTN) sticky_toggle(p, i, p->music);
            else if (v > 0.5f) p->source = i - P_SOURCE_DISCOGS;
            p->sticky_dirty = true;
            return;
        }
        if (i == P_TRANSPORT_SYNC) {
            /* A sticky on/off, not a momentary trigger: the button stays lit while sync is on. */
            bool on = p->sync;
            if (!sticky_toggle(p, i, on)) return;
            p->sync = on;
            p->transport_playing.store(false);
            p->transport_edge.store(0);
            if (!on && p->hold) { p->hold = false; p->api->set_param(p->core, "hold_start", "0"); }
            p->sticky_dirty = true;
            LOG("transport sync %s\n", on ? "on" : "off");
            return;
        }
        break;
    default: return;
    }
    /* A tap on a button toggles its value; fire on any change, so a button MPC still shows as
     * "on" works on the next tap too. Our own spring-back to 0 is excluded (release sets last). */
    bool fire = std::fabs(v - p->last[i]) > 0.25f;
    p->last[i] = v;
    if (!fire) return;
    p->release[i] = 1;
    if (i >= P_GENRE_PREV && i <= P_COUNTRY_NEXT) {   /* arrows wrap: ANY <-> last entry */
        int d = (i - P_GENRE_PREV) / 2, dir = ((i - P_GENRE_PREV) % 2) ? 1 : -1, n = dim_count(p, d);
        set_dim(p, d, (p->dim[d] + dir + n) % n);
    } else if (i == P_PAGE_PREV || i == P_PAGE_NEXT) {
        int n = page_count(p);
        stepper_set(p, P_PAGE, (p->page + (i == P_PAGE_NEXT ? 1 : -1) + n) % n);
    } else if (i == P_SOURCE_PREV || i == P_SOURCE_NEXT) {
        stepper_set(p, P_SOURCE, (p->source + (i == P_SOURCE_NEXT ? 1 : -1) + NSOURCES) % NSOURCES);
    } else if (i == P_CHANNEL_PREV || i == P_CHANNEL_NEXT) {
        int n = stepper_count(p, P_CHANNEL);
        stepper_set(p, P_CHANNEL, (p->chan + (i == P_CHANNEL_NEXT ? 1 : -1) + n) % n);
    } else if (i >= P_MIN_LEN_PREV && i <= P_MUSIC_NEXT) {   /* arrows wrap */
        int d = (i - P_MIN_LEN_PREV) / 2, dir = ((i - P_MIN_LEN_PREV) % 2) ? 1 : -1, sp = P_MIN_LEN + d, n = stepper_count(p, sp);
        stepper_set(p, sp, (stepper_index(p, sp) + dir + n) % n);
    } else if (i == P_KEYS) {
        p->kb = true;
    } else if (is_key(i)) {
        /* MPC can deliver one tap on a button more than once (a second "on" after the spring-back): a repeat of the same key
         * within KEY_REPEAT_MS is that, not a second letter. */
        auto now = std::chrono::steady_clock::now();
        long ms = p->last_key == i ? (long)std::chrono::duration_cast<std::chrono::milliseconds>(now - p->last_key_at).count() : 1 << 20;
        LOG("key %s v=%.2f (%ld ms since the same key)%s\n", PARAMS[i].key, v, ms < (1 << 20) ? ms : -1L, ms < KEY_REPEAT_MS ? " dropped" : "");
        if (ms >= KEY_REPEAT_MS) {
            p->last_key = i;
            p->last_key_at = now;
            type_key(p, PARAMS[i].key + 2);
        }
    } else if (i == P_FIND_SEARCH || i == P_SEARCH) {
        /* one tap can arrive twice ~130 ms apart (the log showed two searches); the second one only restarts the first */
        auto now = std::chrono::steady_clock::now();
        if (now - p->search_at > std::chrono::milliseconds(500)) {
            p->search_at = now;
            do_search(p, i == P_FIND_SEARCH);
        }
    } else if (i == P_PLAY_PAUSE && p->hold) {
        /* Manual start while waiting for MPC's Play. */
        p->hold = false;
        p->api->set_param(p->core, "hold_start", "0");
    } else if (i == P_PLAY_PAUSE) {
        /* Like the host: with nothing loaded, play the highlighted result. */
        if (core_get(p, "stream_url").empty()) play_result(p, std::atoi(core_get(p, "cratedig_result_index").c_str()));
        else p->api->set_param(p->core, "play_pause_step", "trigger");
    } else if (i == P_STOP) {
        p->api->set_param(p->core, "stop_step", "trigger");
    } else if (i == P_REWIND_15) {
        p->api->set_param(p->core, "rewind_15_step", "trigger");
    } else if (i == P_FORWARD_15) {
        p->api->set_param(p->core, "forward_15_step", "trigger");
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
        if (i == P_STATUS) return stream_text(p);
        if (i == P_SYNC_STATE) return p->sync ? "SYNC ON" : "SYNC OFF";
        if (i == P_TIME) return core_get(p, "playback_time");
        if (i == P_SEARCH_STATUS) return search_text(p);
        if (i == P_QUERY) return p->query.empty() ? std::string(p->kb ? "_" : "TAP KEYS TO TYPE") : upper(p->query) + (p->kb ? "_" : "");
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

/* ---- module dir: where bin/yt-dlp, bin/python3, bin/ffmpeg live ---------- */
static bool has_bin(const std::string &d) {
    struct stat sb;
    return !d.empty() && stat((d + "/bin/yt-dlp").c_str(), &sb) == 0;
}
static std::string find_module_dir() {
    Dl_info info;
    std::string so_dir;
    if (dladdr((void *)&find_module_dir, &info) && info.dli_fname) {
        so_dir = info.dli_fname;
        so_dir = so_dir.substr(0, so_dir.rfind('/'));
    }
    if (has_bin(so_dir + "/cratedigger")) return so_dir + "/cratedigger";
    if (FILE *f = std::fopen((so_dir + "/cratedigger_module_dir.txt").c_str(), "r")) {
        char line[512] = {0};
        if (std::fgets(line, sizeof line, f)) line[std::strcspn(line, "\r\n")] = 0;
        std::fclose(f);
        if (has_bin(line)) return line;
    }
    glob_t g;
    std::string found;
    if (glob("/media/*/AddOns/ForceCrateDigger", 0, nullptr, &g) == 0) {
        for (size_t i = 0; i < g.gl_pathc && found.empty(); i++)
            if (has_bin(g.gl_pathv[i])) found = g.gl_pathv[i];
        globfree(&g);
    }
    return found;
}

/* ---- dispatcher ----------------------------------------------------------- */
static intptr_t dispatcher(AEffect *e, int32_t op, int32_t idx, intptr_t v, void *ptr, float opt) {
    Plugin *p = (Plugin *)e->object;
    (void)opt;
    switch (op) {
    case effOpen: return 1;
    case effClose:
        p->running = false;
        if (p->worker.joinable()) p->worker.join();
        p->api->destroy_instance(p->core);
        delete p;
        return 1;
    case effGetPlugCategory: return 2;
    case effGetEffectName: case effGetProductString: copy_str(ptr, PLUG_NAME, 32); return 1;
    case effGetVendorString: copy_str(ptr, PLUG_VENDOR, 32); return 1;
    case effGetVendorVersion: return PLUG_VERSION;
    case effGetVstVersion: return 2400;
    case effCanBeAutomated: return idx >= 0 && idx < NPARAMS && PARAMS[idx].type != T_READOUT;
    case effGetParamName:
        if (idx >= 0 && idx < NPARAMS) copy_str(ptr, PARAMS[idx].name, 32);
        return 1;
    case effGetParamLabel: copy_str(ptr, "", 8); return 1;
    case effGetParamDisplay:
        if (idx >= 0 && idx < NPARAMS) {
            std::lock_guard<std::mutex> lk(p->lock);
            copy_str(ptr, display(p, idx), 100);
        }
        return 1;
    case effSetSampleRate: case effSetBlockSize: case effMainsChanged: return 1;
    case effProcessEvents: return 1;   /* no MIDI (yet) */
    case effCanDo: return -1;
    case effGetChunk: {
        std::lock_guard<std::mutex> lk(p->lock);
        std::snprintf(p->chunk, sizeof p->chunk, "g=%d;s=%d;d=%d;r=%d;c=%d;gain=%.3f;src=%d;ch=%d;ml=%d;xl=%d;mu=%d;q=%s",
                      p->dim[0], p->dim[1], p->dim[2], p->dim[3], p->dim[4], p->gain, p->source, p->chan, p->min_len, p->max_len, p->music ? 1 : 0, p->query.c_str());
        *(void **)ptr = p->chunk;
        return (intptr_t)std::strlen(p->chunk) + 1;
    }
    case effSetChunk: {
        if (v <= 0 || v > (intptr_t)sizeof p->chunk) return 0;
        char s[320];
        std::memcpy(s, ptr, (size_t)v);
        s[v - 1] = 0;
        int g = 0, st = 0, d = 0, r = 0, c = 0;
        float gn = 1.0f;
        int got = std::sscanf(s, "g=%d;s=%d;d=%d;r=%d;c=%d;gain=%f", &g, &st, &d, &r, &c, &gn);
        LOG("effSetChunk '%s' parsed=%d\n", s, got);
        if (got < 5) return 0;   /* not one of ours: keep the current filters */
        int src = SRC_DISCOGS, ch = 0;
        const char *tail = std::strstr(s, ";src=");
        int ml = 0, xl = 0, mu = 0;
        if (tail) std::sscanf(tail, ";src=%d;ch=%d;ml=%d;xl=%d;mu=%d", &src, &ch, &ml, &xl, &mu);
        if (got < 6 || !(gn >= 0.0f && gn <= 4.0f)) gn = 1.0f;
        std::lock_guard<std::mutex> lk(p->lock);
        p->page = 0;
        p->source = src < 0 || src >= NSOURCES ? SRC_DISCOGS : src;
        p->chan = ch < 0 ? 0 : ch;
        p->min_len = ml < 0 || ml >= NMIN_LENS ? 0 : ml;
        p->max_len = xl < 0 || xl >= NMAX_LENS ? 0 : xl;
        p->music = mu == 1;
        p->query.clear();
        if (const char *q = std::strstr(s, ";q=")) p->query = std::string(q + 3).substr(0, QUERY_MAX);
        for (int i = 0; i < NPARAMS; i++) p->step_seen[i] = -1.0f;
        set_dim(p, DIM_GENRE, g); set_dim(p, DIM_STYLE, st); set_dim(p, DIM_DECADE, d);
        set_dim(p, DIM_REGION, r); set_dim(p, DIM_COUNTRY, c);
        char gs[32];
        p->gain = gn;
        std::snprintf(gs, sizeof gs, "%.3f", gn);
        p->api->set_param(p->core, "gain", gs);
        return 1;
    }
    default: return 0;
    }
}

extern "C" __attribute__((visibility("default"))) AEffect *VSTPluginMain(audioMasterCallback master) {
    if (!g_log) g_log = std::fopen("/tmp/cratedigger_vst.log", "a");
    /* A write to a dead child's pipe must not kill MPC. Only touch SIGPIPE if the host
     * left it at the default (children get the default back via posix_spawn). */
    struct sigaction sa;
    if (sigaction(SIGPIPE, nullptr, &sa) == 0 && sa.sa_handler == SIG_DFL) {
        signal(SIGPIPE, SIG_IGN);
        LOG("SIGPIPE was default in host; now ignored\n");
    }
    std::string dir = find_module_dir();
    LOG("VSTPluginMain: module dir '%s'\n", dir.c_str());
    if (dir.empty()) return nullptr;   /* no engine bundle: refuse to load rather than half-work */

    plugin_api_v2_t *api = move_plugin_init_v2(nullptr);
    if (!api) return nullptr;
    Plugin *p = new Plugin();
    for (int i = 0; i < NPARAMS; i++) p->step_seen[i] = -1.0f;
    p->api = api;
    p->master = master;
    std::memset((void *)p->release, 0, sizeof p->release);
    for (int i = 0; i < NPARAMS; i++) p->last[i] = 0.0f;
    p->channels_path = dir + "/channels.txt";
    p->core = api->create_instance(dir.c_str(), nullptr);
    if (!p->core) { delete p; return nullptr; }
    api->set_param(p->core, "search_provider", "cratedig");
    api->set_param(p->core, "gain", "1.000");

    AEffect *e = &p->fx;
    std::memset(e, 0, sizeof *e);
    e->magic = 0x56737450; /* 'VstP' */
    e->dispatcher = dispatcher;
    e->setParameter = setParameter;
    e->getParameter = getParameter;
    e->processReplacing = processReplacing;
    e->numParams = NPARAMS;
    e->numInputs = 0;
    e->numOutputs = 2;
    e->flags = effFlagsCanReplacing | effFlagsIsSynth | effFlagsProgramChunks;
    e->uniqueID = PLUG_UID;
    e->version = PLUG_VERSION;
    e->object = p;

    p->running = true;
    p->worker = std::thread(worker_main, p);
    return e;
}
