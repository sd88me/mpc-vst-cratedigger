/* The deck skin's centre-label colours: the frames of its label film strip, in this order (tools/make_tui.py reads this file, so the
 * art and the plugin agree). The plugin picks the one closest to the playing record's cover (CrateDiggerPlugin.cpp, pick_tint). */
#pragma once
static const unsigned char LABEL_TINTS[][3] = {
    {232, 221, 196},   /*  0 cream (no cover yet) */
    {240, 238, 232},   /*  1 white */
    {236, 206, 72},    /*  2 lemon */
    {200, 150, 40},    /*  3 mustard */
    {226, 110, 36},    /*  4 orange */
    {196, 40, 32},     /*  5 red */
    {140, 24, 28},     /*  6 deep red */
    {96, 26, 30},      /*  7 maroon */
    {226, 130, 150},   /*  8 pink */
    {190, 40, 110},    /*  9 magenta */
    {110, 50, 130},    /* 10 purple */
    {140, 110, 190},   /* 11 violet */
    {30, 40, 90},      /* 12 navy */
    {40, 80, 170},     /* 13 blue */
    {110, 170, 220},   /* 14 sky */
    {30, 120, 120},    /* 15 teal */
    {60, 170, 170},    /* 16 turquoise */
    {40, 120, 60},     /* 17 green */
    {120, 120, 50},    /* 18 olive */
    {150, 190, 70},    /* 19 lime */
    {110, 70, 40},     /* 20 brown */
    {190, 150, 100},   /* 21 tan */
    {140, 140, 136},   /* 22 grey */
    {26, 26, 28},      /* 23 black */
};
static const int N_LABEL_TINTS = (int)(sizeof LABEL_TINTS / sizeof LABEL_TINTS[0]);

/* The label colour for a small picture of the cover (rgb, n pixels): every pixel votes for its nearest tint, the more saturated the pixel
 * the stronger its vote, so a cover's dominant colour wins over its muddy average. */
static inline int pick_tint(const unsigned char *rgb, int n) {
    double score[N_LABEL_TINTS] = {0};
    for (int i = 0; i < n; ++i) {
        const int r = rgb[i * 3], g = rgb[i * 3 + 1], b = rgb[i * 3 + 2];
        int best = 0;
        long bestD = -1;
        for (int t = 0; t < N_LABEL_TINTS; ++t) {
            const long dr = r - LABEL_TINTS[t][0], dg = g - LABEL_TINTS[t][1], db = b - LABEL_TINTS[t][2];
            const long d = 2 * dr * dr + 4 * dg * dg + 3 * db * db;
            if (bestD < 0 || d < bestD) { bestD = d; best = t; }
        }
        const int mx = r > g ? (r > b ? r : b) : (g > b ? g : b), mn = r < g ? (r < b ? r : b) : (g < b ? g : b);
        score[best] += 0.25 + (mx - mn) / 255.0;
    }
    int win = 0;
    for (int t = 1; t < N_LABEL_TINTS; ++t) if (score[t] > score[win]) win = t;
    return win;
}
