/* The deck's varispeed: read an interleaved stereo int16 ring at `rate` ring frames per output frame, cubic (Catmull-Rom) between
 * frames, as a turntable plays faster or slower (pitch and tempo together). Real-time safe: no allocation, no locks.
 *   ring, mask: the ring and its frame mask (frames - 1, a power of two minus one); r: the read position in frames; avail: frames
 *   readable from r; frac: where between frames the read is, carried from block to block. The frame before r must still be in the
 *   ring (the producer keeps far less than a ring ahead). Underrun: silence, and the read waits where the data ends.
 *   Returns the frames consumed; writes n frames to l and rr and the block's peaks. */
#pragma once
#include <algorithm>
#include <cmath>
#include <stdint.h>

static inline float vs_cubic(float y0, float y1, float y2, float y3, float t) {
    return y1 + 0.5f * t * (y2 - y0 + t * (2.0f * y0 - 5.0f * y1 + 4.0f * y2 - y3 + t * (3.0f * (y1 - y2) + y3 - y0)));
}

static inline uint32_t varispeed_read(const int16_t *ring, uint32_t mask, uint32_t r, uint32_t avail, double &frac, float rate,
                                      float *l, float *rr, int n, float &pkL, float &pkR) {
    double pos = frac;
    for (int i = 0; i < n; ++i)
    {
        const uint32_t ip = (uint32_t)pos;
        if (ip + 2 >= avail) { l[i] = rr[i] = 0.0f; continue; }
        const float t = (float)(pos - ip);
        float o[2];
        for (int c = 0; c < 2; ++c)
        {
            const float y0 = ring[((r + ip - 1) & mask) * 2 + c], y1 = ring[((r + ip) & mask) * 2 + c];
            const float y2 = ring[((r + ip + 1) & mask) * 2 + c], y3 = ring[((r + ip + 2) & mask) * 2 + c];
            o[c] = std::max(-1.0f, std::min(1.0f, vs_cubic(y0, y1, y2, y3, t) * (1.0f / 32768.0f)));
        }
        l[i] = o[0];
        rr[i] = o[1];
        pkL = std::max(pkL, std::fabs(o[0]));
        pkR = std::max(pkR, std::fabs(o[1]));
        pos += rate;
    }
    uint32_t used = (uint32_t)pos;
    if (used + 2 >= avail) { used = avail > 2 ? avail - 2 : 0; frac = 0.0; }
    else frac = pos - used;
    return used;
}
