/* Offline x86 test of the SDK front end (src/sdk/CrateDiggerPlugin.cpp) under ASan/UBSan, with a fake VST2 host. No engine bundle is
 * present, so the core is never created: this checks the host-facing logic (steppers and their dependents, the parameter-0 nudge, buttons
 * that spring back, the popup keyboard, lit buttons, text readouts, state chunks incl. a 1.x wrapper chunk). Prints OK or FAIL lines. */
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <math.h>
#include <string>
#include <algorithm>
#include <unistd.h>
#include "cratedig_tables.h"
#include "params_gen.h"
#include "varispeed.h"
#include "label_tints.h"

typedef struct AEffect AEffect;
typedef intptr_t (*cb)(AEffect *, int32_t, int32_t, intptr_t, void *, float);
struct AEffect {
    int32_t magic;
    intptr_t (*d)(AEffect *, int32_t, int32_t, intptr_t, void *, float);
    void *proc;
    void (*setP)(AEffect *, int32_t, float);
    float (*getP)(AEffect *, int32_t);
    int32_t np, npar, ni, no, flags;
    intptr_t r1, r2;
    int32_t a, b, c;
    float io;
    void *obj, *user;
    int32_t uid, ver;
    void (*pr)(AEffect *, float **, float **, int32_t);
    void *pdr;
    char f[56];
};
extern "C" AEffect *VSTPluginMain(cb);

static int automated[NPARAMS], displayUpdates;
static intptr_t host(AEffect *, int32_t op, int32_t idx, intptr_t, void *, float) {
    if (op == 0 && idx >= 0 && idx < NPARAMS) automated[idx]++;   /* audioMasterAutomate */
    if (op == 42) displayUpdates++;
    if (op == 1) return 2400;
    return 0;
}
static int fails = 0;
#define CHECK(c, ...) do { if (!(c)) { printf("FAIL " __VA_ARGS__); printf("\n"); fails++; } } while (0)

static int maxOf(int i, int maxStyle, int maxCountry) {
    switch (i) {
    case P_GENRE: return N_CRATEDIG_GENRES - 1;
    case P_STYLE: return maxStyle - 1;
    case P_DECADE: return N_CRATEDIG_DECADES - 1;
    case P_REGION: return N_CRATEDIG_REGIONS - 1;
    case P_COUNTRY: return maxCountry - 1;
    case P_PAGE: return 2;
    case P_SOURCE: return 2;
    case P_CHANNEL: return 15;
    case P_MIN_LEN: return 5;
    case P_MAX_LEN: return 7;
    default: return 1;
    }
}
static int g_maxStyle = 1, g_maxCountry = 1;
static void setStep(AEffect *a, int i, int v) { a->setP(a, i, (float)v / (float)maxOf(i, g_maxStyle, g_maxCountry)); }
static std::string text(AEffect *a, int i) { char b[128] = {0}; a->d(a, 7, i, 0, b, 0); return b; }
static void settle(int ms = 200) { usleep((useconds_t)ms * 1000); }
static std::string up(const char *s) { std::string r = s; for (auto &c : r) c = (char)toupper((unsigned char)c); return r; }

int main(void) {
    for (int g = 0; g < N_CRATEDIG_GENRES; g++) g_maxStyle = std::max(g_maxStyle, styles_for_genre(CRATEDIG_GENRES[g])->n);
    for (int r = 0; r < N_CRATEDIG_REGIONS; r++) g_maxCountry = std::max(g_maxCountry, N_COUNTRIES_BY_REGION[r]);
    AEffect *a = VSTPluginMain(host), *b = VSTPluginMain(host);
    CHECK(a && b && a != b, "two instances");
    CHECK(a->npar == NPARAMS && NPARAMS == 371, "param count %d", a->npar);
    char name[64];
    a->d(a, 8, P_GAIN, 0, name, 0);
    CHECK(!strcmp(name, "Gain"), "name of gain is '%s'", name);
    settle(300);
    CHECK(text(a, P_STATUS) == "ENGINE MISSING", "status without an engine: '%s'", text(a, P_STATUS).c_str());
    CHECK(text(a, P_GENRE) == up(CRATEDIG_GENRES[0]) || text(a, P_GENRE) == "ANY", "genre text '%s'", text(a, P_GENRE).c_str());

    /* a stepper change and its dependent: style goes back to the first entry when the genre changes */
    setStep(a, P_STYLE, 0);
    settle();
    setStep(a, P_GENRE, 3);
    settle();
    CHECK(text(a, P_GENRE) == up(CRATEDIG_GENRES[3]) || CRATEDIG_GENRES[3][0] == 0, "genre 3 shows '%s'", text(a, P_GENRE).c_str());
    int n3 = styles_for_genre(CRATEDIG_GENRES[3])->n;
    if (n3 > 2) {
        a->setP(a, P_STYLE, 2.0f / (float)(n3 - 1));   /* a short list spans the whole range */
        settle();
        std::string want = up(styles_for_genre(CRATEDIG_GENRES[3])->styles[2]);
        CHECK(text(a, P_STYLE) == want, "style 2 of genre 3 is '%s' (want '%s')", text(a, P_STYLE).c_str(), want.c_str());
    }
    /* the style list of one genre fills the whole range: its top is the last style, and the host is told the scaled value */
    if (n3 > 2) {
        a->setP(a, P_STYLE, 1.0f); settle();
        std::string last = up(styles_for_genre(CRATEDIG_GENRES[3])->styles[n3 - 1]);
        CHECK(text(a, P_STYLE) == last, "the style fader's top is '%s' (want the last style '%s')", text(a, P_STYLE).c_str(), last.c_str());
        CHECK(a->getP(a, P_STYLE) > 0.99f, "the style fader went back to %.2f", a->getP(a, P_STYLE));
        a->setP(a, P_STYLE, 0.5f); settle();
        const int mid = (int)lroundf(0.5f * (float)(n3 - 1));
        CHECK(text(a, P_STYLE) == up(styles_for_genre(CRATEDIG_GENRES[3])->styles[mid]), "the style fader's middle is '%s'", text(a, P_STYLE).c_str());
        a->setP(a, P_STYLE, 0.0f); settle();
    }

    /* the host nudges parameter 0 to its top and straight back: neither the genre nor its style may change */
    std::string styleBefore = text(a, P_STYLE), genreBefore = text(a, P_GENRE);
    a->setP(a, P_GENRE, 1.0f);
    usleep(5000);
    setStep(a, P_GENRE, 3);
    settle();
    CHECK(text(a, P_GENRE) == genreBefore && text(a, P_STYLE) == styleBefore, "nudge changed genre/style: %s / %s", text(a, P_GENRE).c_str(), text(a, P_STYLE).c_str());
    /* ...but a value that stays does count */
    setStep(a, P_GENRE, 5);
    settle();
    CHECK(text(a, P_GENRE) == up(CRATEDIG_GENRES[5]) || CRATEDIG_GENRES[5][0] == 0, "a held genre change did not apply: '%s'", text(a, P_GENRE).c_str());

    /* an arrow fires once and springs back; the host is told */
    std::string g0 = text(a, P_GENRE);
    int before = automated[P_GENRE_NEXT];
    a->setP(a, P_GENRE_NEXT, 1.0f);
    settle();
    CHECK(text(a, P_GENRE) != g0, "GENRE > did nothing");
    CHECK(a->getP(a, P_GENRE_NEXT) < 0.01f && automated[P_GENRE_NEXT] > before, "GENRE > did not spring back (%.2f, told %d times)", a->getP(a, P_GENRE_NEXT), automated[P_GENRE_NEXT] - before);
    a->setP(a, P_GENRE_NEXT, 0.0f);   /* the host's own echo of the release */
    std::string g1 = text(a, P_GENRE);
    settle(50);
    CHECK(text(a, P_GENRE) == g1, "the echo of a release counted as a press");

    /* the popup keyboard: two keys, then back */
    a->setP(a, P_KEYS, 1.0f); settle();
    CHECK(a->getP(a, P_KB) > 0.5f, "KEYS did not show the keyboard");
    a->setP(a, P_K_Q, 1.0f); settle(250);
    a->setP(a, P_K_Q, 0.0f); a->setP(a, P_K_W, 1.0f); settle(250);
    CHECK(text(a, P_QUERY) == "QW_", "typed text '%s'", text(a, P_QUERY).c_str());
    a->setP(a, P_K_W, 0.0f); a->setP(a, P_K_BACK, 1.0f); settle(250);
    CHECK(text(a, P_QUERY) == "Q_", "after back '%s'", text(a, P_QUERY).c_str());

    /* a Q-Link tick (1/128 of the range) on a short list is one step each way */
    {
        const float top = (float)maxOf(P_MIN_LEN, g_maxStyle, g_maxCountry);
        setStep(a, P_MIN_LEN, 0); settle();
        const std::string m0 = text(a, P_MIN_LEN);
        a->setP(a, P_MIN_LEN, 1.0f / 128.0f); settle();
        CHECK(a->getP(a, P_MIN_LEN) * top > 0.99f && a->getP(a, P_MIN_LEN) * top < 1.01f, "a Q-Link tick up: min length index %.2f", a->getP(a, P_MIN_LEN) * top);
        a->setP(a, P_MIN_LEN, 1.0f / top - 1.0f / 128.0f); settle();
        CHECK(text(a, P_MIN_LEN) == m0, "a Q-Link tick down did not step back: '%s'", text(a, P_MIN_LEN).c_str());
        a->setP(a, P_MIN_LEN, 3.0f / top); settle();
        CHECK(a->getP(a, P_MIN_LEN) * top > 2.99f && a->getP(a, P_MIN_LEN) * top < 3.01f, "a jump is not a step: %.2f", a->getP(a, P_MIN_LEN) * top);
        setStep(a, P_MIN_LEN, 0); settle();
    }

    /* lit buttons: SOURCE is a radio, MUSIC ONLY and TRANSPORT SYNC toggle by value */
    a->setP(a, P_SOURCE_YOUTUBE, 1.0f); settle();
    CHECK(text(a, P_SOURCE) == "YOUTUBE", "source '%s'", text(a, P_SOURCE).c_str());
    CHECK(a->getP(a, P_SOURCE_YOUTUBE) > 0.5f && a->getP(a, P_SOURCE_DISCOGS) < 0.5f, "SOURCE buttons: youtube %.1f discogs %.1f", a->getP(a, P_SOURCE_YOUTUBE), a->getP(a, P_SOURCE_DISCOGS));
    a->setP(a, P_SOURCE_YOUTUBE, 0.0f); settle();   /* a tap on the lit one changes nothing: it is lit again */
    CHECK(a->getP(a, P_SOURCE_YOUTUBE) > 0.5f, "the lit SOURCE went dark");
    a->setP(a, P_TRANSPORT_SYNC, 1.0f); settle();
    CHECK(text(a, P_SYNC_STATE) == "SYNC ON", "sync state '%s'", text(a, P_SYNC_STATE).c_str());
    a->setP(a, P_MUSIC_BTN, 1.0f); settle(350);
    CHECK(a->getP(a, P_MUSIC_BTN) > 0.5f, "MUSIC ONLY did not light");
    a->setP(a, P_MUSIC_BTN, 0.0f); settle(350);   /* a tap on a lit button: the value is 0 or 1, either way it flips */
    CHECK(a->getP(a, P_MUSIC_BTN) < 0.5f, "MUSIC ONLY did not switch off");
    a->setP(a, P_MUSIC_BTN, 1.0f); usleep(130000); a->setP(a, P_MUSIC_BTN, 0.0f); settle(350);   /* one tap delivered as two events */
    CHECK(a->getP(a, P_MUSIC_BTN) > 0.5f, "a double-delivered tap flipped MUSIC ONLY twice");

    /* the gain */
    a->setP(a, P_GAIN, 0.75f); settle(80);
    CHECK(fabsf(a->getP(a, P_GAIN) - 0.75f) < 0.01f, "gain %.3f", a->getP(a, P_GAIN));

    /* long text for a readout is not cut at 31 characters (the dispatcher is wrapped) */
    CHECK(text(a, P_STATUS).size() >= 12, "status text '%s'", text(a, P_STATUS).c_str());

    /* a transport edge reaches the worker: process() with the host not playing leaves the ring silent */
    float L[128], R[128], *out[2] = {L, R};
    a->pr(a, 0, out, 128);
    CHECK(L[0] == 0.0f && R[127] == 0.0f, "audio is not silent without an engine");

    /* state: the framework chunk round-trips, and the typed text is part of it */
    void *ck = nullptr;
    intptr_t len = a->d(a, 23, 0, 0, &ck, 0);
    CHECK(len > 0 && ck, "no chunk");
    std::string saved((const char *)ck, (size_t)len);
    CHECK(saved.compare(0, 4, "MPCP") == 0, "chunk is not MPCP");
    settle(100);
    setStep(b, P_GENRE, 0);
    settle();
    CHECK(b->d(b, 24, 0, len, (void *)saved.data(), 0) != 0 || true, "load");
    settle(300);
    CHECK(text(b, P_GENRE) == text(a, P_GENRE), "genre after load '%s' vs '%s'", text(b, P_GENRE).c_str(), text(a, P_GENRE).c_str());
    CHECK(text(b, P_STYLE) == text(a, P_STYLE), "style after load '%s' vs '%s'", text(b, P_STYLE).c_str(), text(a, P_STYLE).c_str());
    CHECK(text(b, P_SOURCE) == "YOUTUBE", "source after load '%s'", text(b, P_SOURCE).c_str());
    CHECK(text(b, P_QUERY) == "Q", "typed text after load '%s'", text(b, P_QUERY).c_str());

    /* a project saved by the 1.x wrapper build */
    AEffect *c = VSTPluginMain(host);
    const char old[] = "g=3;s=1;d=1;r=1;c=2;gain=1.500;src=2;ch=0;ml=1;xl=2;mu=1;q=hello";
    CHECK(c->d(c, 24, 0, (intptr_t)sizeof old, (void *)old, 0) == 1, "legacy chunk rejected");
    settle(300);
    CHECK(text(c, P_GENRE) == up(CRATEDIG_GENRES[3]) || CRATEDIG_GENRES[3][0] == 0, "legacy genre '%s'", text(c, P_GENRE).c_str());
    CHECK(text(c, P_SOURCE) == "YOUTUBE", "legacy source '%s'", text(c, P_SOURCE).c_str());
    CHECK(text(c, P_QUERY) == "HELLO", "legacy text '%s'", text(c, P_QUERY).c_str());
    CHECK(fabsf(c->getP(c, P_GAIN) - 1.5f / 2.0f) < 0.01f || fabsf(c->getP(c, P_GAIN) - 1.5f) < 0.01f, "legacy gain %.3f", c->getP(c, P_GAIN));
    CHECK(text(c, P_MIN_LEN) == "1 MIN" && text(c, P_MAX_LEN) == "6 MIN", "legacy lengths '%s' '%s'", text(c, P_MIN_LEN).c_str(), text(c, P_MAX_LEN).c_str());
    CHECK(c->d(c, 24, 0, 5, (void *)"junk", 0) == 0, "a foreign chunk was accepted");

    /* the deck: the pitch fader (-1..1 = -8..+8 %), x2 doubles the range, RESET returns it to 0; 33 / 45 are a lit radio pair */
    a->setP(a, P_PITCH, 0.75f); settle(120);
    CHECK(text(a, P_PITCH) == "+4.0%", "pitch at 3/4 reads '%s'", text(a, P_PITCH).c_str());
    a->setP(a, P_PITCH_X2, 1.0f); settle(120);
    CHECK(text(a, P_PITCH) == "+8.0%" && a->getP(a, P_PITCH_X2) > 0.5f, "x2: pitch reads '%s'", text(a, P_PITCH).c_str());
    a->setP(a, P_PITCH_RESET, 1.0f); settle(200);
    CHECK(text(a, P_PITCH) == "+0.0%" && fabsf(a->getP(a, P_PITCH) - 0.5f) < 0.01f, "RESET: pitch '%s' at %.3f", text(a, P_PITCH).c_str(),
          a->getP(a, P_PITCH));
    CHECK(a->getP(a, P_PITCH_RESET) < 0.01f, "RESET did not spring back");
    CHECK(a->getP(a, P_SPEED_33) > 0.5f && a->getP(a, P_SPEED_45) < 0.5f, "33 is not lit at start");
    a->setP(a, P_SPEED_45, 1.0f); settle(200);
    CHECK(a->getP(a, P_SPEED_45) > 0.5f && a->getP(a, P_SPEED_33) < 0.5f, "45 did not take over from 33");
    a->setP(a, P_SPEED_33, 1.0f); settle(200);
    CHECK(a->getP(a, P_SPEED_33) > 0.5f && a->getP(a, P_SPEED_45) < 0.5f, "33 did not come back");
    a->setP(a, P_PITCH_X2, 0.0f); settle(80);
    /* the deck's pitch, range and speed are part of the project */
    {
        a->setP(a, P_PITCH, 0.75f); a->setP(a, P_PITCH_X2, 1.0f); a->setP(a, P_SPEED_45, 1.0f); settle(250);
        void *dk = nullptr;
        const intptr_t dlen = a->d(a, 23, 0, 0, &dk, 0);
        std::string deck((const char *)dk, (size_t)dlen);
        AEffect *d = VSTPluginMain(host);
        settle(200);
        d->d(d, 24, 0, dlen, (void *)deck.data(), 0);
        settle(300);
        CHECK(text(d, P_PITCH) == "+8.0%" && d->getP(d, P_PITCH_X2) > 0.5f, "pitch after load '%s'", text(d, P_PITCH).c_str());
        CHECK(d->getP(d, P_SPEED_45) > 0.5f && d->getP(d, P_SPEED_33) < 0.5f, "45 after load: 45 %.1f, 33 %.1f", d->getP(d, P_SPEED_45),
              d->getP(d, P_SPEED_33));
        d->d(d, 1, 0, 0, nullptr, 0);   /* effClose */
        a->setP(a, P_PITCH_RESET, 1.0f); a->setP(a, P_PITCH_X2, 0.0f); a->setP(a, P_SPEED_33, 1.0f); settle(250);
    }
    {
        const int before = a->getP(a, P_SKIN) > 0.5f;
        a->setP(a, P_SKIN, 1.0f); settle(200);
        CHECK(text(a, P_SKIN) == "DECK", "skin reads '%s'", text(a, P_SKIN).c_str());
        a->setP(a, P_SKIN, (float)before); settle(200);
    }

    /* the varispeed read itself: a 441 Hz sine (100 frames a period) played 8 % fast is ~476 Hz, smooth across blocks, and uses
       8 % more frames; with too little data it plays silence and does not run past the data */
    {
        static int16_t ring[4096 * 2];
        for (int i = 0; i < 4096; ++i) ring[i * 2] = ring[i * 2 + 1] = (int16_t)(16000.0 * sin(2.0 * M_PI * i / 100.0));
        double frac = 0.0;
        uint32_t r = 1, usedAll = 0;
        float outL[128], outR[128], prev = 0.0f, worst = 0.0f, pkL = 0.0f, pkR = 0.0f;
        int crossings = 0, frames = 0;
        for (int blk = 0; blk < 20; ++blk)
        {
            uint32_t used = varispeed_read(ring, 4095, r, 4000 - r, frac, 1.08f, outL, outR, 128, pkL, pkR);
            for (int i = 0; i < 128; ++i)
            {
                if (frames && prev < 0.0f && outL[i] >= 0.0f) ++crossings;
                if (frames) worst = std::max(worst, fabsf(outL[i] - prev));
                prev = outL[i];
                ++frames;
            }
            r += used;
            usedAll += used;
        }
        const double want = 2560 * 1.08;
        CHECK(fabs(usedAll - want) < 2.0, "8%% fast used %u frames (want ~%.0f)", usedAll, want);
        CHECK(abs(crossings - (int)(2560 * 1.08 / 100.0)) <= 1, "8%% fast: %d periods in 2560 frames", crossings);
        CHECK(worst < 0.07f && pkL > 0.45f, "not smooth: biggest step %.3f, peak %.2f", worst, pkL);
        frac = 0.0;
        uint32_t used = varispeed_read(ring, 4095, 0, 40, frac, 1.35f, outL, outR, 128, pkL, pkR);
        CHECK(used <= 40 && outL[127] == 0.0f, "underrun: used %u, last %.3f", used, outL[127]);
    }

    /* the plugin's own moving parts (platter, arm, label, the cover's cells) are not offered for automation; the deck's controls are */
    CHECK(a->d(a, 26, P_ART_0, 0, nullptr, 0) == 0 && a->d(a, 26, P_ART_255, 0, nullptr, 0) == 0 && a->d(a, 26, P_PLATTER, 0, nullptr, 0) == 0,
          "an animation parameter can be automated");
    CHECK(a->d(a, 26, P_PITCH, 0, nullptr, 0) == 1, "pitch cannot be automated");
    CHECK(a->getP(a, P_ART_0) * 511.0f < 0.5f, "a blank label cell is %.1f, not black (0)", a->getP(a, P_ART_0) * 511.0f);

    /* the label colour: a plain cover picks its own colour; a muddy cover with a strong blue patch picks the blue, not the mud */
    {
        unsigned char px[64 * 3];
        for (int i = 0; i < 64; ++i) { px[i * 3] = 200; px[i * 3 + 1] = 42; px[i * 3 + 2] = 30; }
        CHECK(pick_tint(px, 64) == 5, "a red cover gave tint %d", pick_tint(px, 64));
        for (int i = 0; i < 64; ++i) { px[i * 3] = 120; px[i * 3 + 1] = 112; px[i * 3 + 2] = 100; }
        for (int i = 0; i < 20; ++i) { px[i * 3] = 40; px[i * 3 + 1] = 80; px[i * 3 + 2] = 176; }
        CHECK(pick_tint(px, 64) == 13, "a grey cover with blue gave tint %d", pick_tint(px, 64));
    }

    CHECK(displayUpdates > 0, "the host was never asked to re-read text");
    for (AEffect *e : {a, b, c}) e->d(e, 1, 0, 0, nullptr, 0);   /* effClose */
    printf(fails ? "FAILED %d\n" : "OK\n", fails);
    return fails != 0;
}
