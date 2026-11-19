#!/usr/bin/env python3
"""Mock-up of a second Crate Digger skin, "Deck & Crate": the record-playing side of digging instead of the sampler.
Left: a silver direct-drive turntable seen from above, the record cropped by the top-left corner so its centre label (the
display: now playing, status, time, amber behind smoked glass) sits large in that corner. The tonearm rides the groove, the gain
is the pitch fader, the strobe light shows play, the deck's own keys are the transport, a meter strip sits by the maker's plate.
Right: a plywood record crate. On PLAY the results are the sleeves in it (the playing one pulled up), the page keys are divider
cards; on FILTERS the five filters are index cards; on FIND the sources are shop bins. Status and the search text are Dymo tape.
One light from the top left, a warm grade, film grain and dust: worn, played and handled, not new.
Pictures only, no TUI wiring:   python3 tools/mockup_skin_deck.py   ->  docs/skin-mockups/v6-deck/{play,filters,find}.png"""
import math, os, random
from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageFilter
import mockup_skin as M          # only for the Titillium Web font paths (the MPC draws live text in it)

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUT = os.path.join(ROOT, "docs", "skin-mockups", "v6-deck")
S = 2
W, H = 1280, 628
rng = random.Random(7)

AMBER, AMBER_DIM, AMBER_LOW = (255, 176, 66), (200, 116, 40), (128, 70, 26)
INK = (44, 34, 26)
PAPER = (232, 221, 196)
CX, CY = 190, 180                                         # platter centre: the label sits in the top-left corner
R_PLATTER, R_VINYL, R_LABEL, R_DISP = 350, 328, 172, 148
PLINTH_X = 612
PIVOT, STYLUS_HEAD = (578, 118), (414, 344)
CRATE_TOP, CRATE_FRONT = 48, 458                          # the crate's back rim and the top of its front panel
ROW0, ROW_H = 66, 49                                      # the first sleeve's top, the sleeves' pitch
STATUS_BOX, SEARCH_BOX = (652, 576, 1104, 618), (1116, 574, 1258, 620)   # along the bottom on every tab
SKIN_BOX = (1112, 504, 1248, 548)                         # FIND only: the switch back to the sampler look
LIVE = True        # the mock-up draws everything; tools/skin_deck.py turns this off to draw only the art under the TUI's moving parts


def font(size, bold=True):
    return ImageFont.truetype(M.TITB if bold else M.TIT, int(size * S))


def s(v):
    return int(round(v * S))


def B(b):
    return tuple(s(v) for v in b)


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(len(a)))


def layer():
    return Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))


def mask_layer():
    return Image.new("L", (W * S, H * S), 0)


def clip(L, mask):
    L.putalpha(ImageChops.multiply(L.getchannel("A"), mask))
    return L


def grad(im, box, top, bot, r=0, horizontal=False):
    x0, y0, x1, y1 = B(box)
    w, h = max(1, x1 - x0), max(1, y1 - y0)
    top, bot = tuple(top) + (255,) * (4 - len(top)), tuple(bot) + (255,) * (4 - len(bot))
    n = w if horizontal else h
    strip = Image.new("RGBA", (n, 1))
    for i in range(n):
        strip.putpixel((i, 0), lerp(top, bot, i / max(1, n - 1)))
    if horizontal:
        g = strip.resize((w, h))
    else:
        g = strip.transpose(Image.Transpose.ROTATE_270).transpose(Image.Transpose.FLIP_LEFT_RIGHT).resize((w, h))
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), s(r), fill=255)
    tile = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    tile.paste(g, (0, 0), m)
    im.alpha_composite(tile, (x0, y0))


def soft_shadow(im, box, r=6, off=(2, 4), blur=6, alpha=120, ellipse=False):
    L = layer()
    d = ImageDraw.Draw(L)
    bb = B((box[0] + off[0], box[1] + off[1], box[2] + off[0], box[3] + off[1]))
    if ellipse:
        d.ellipse(bb, fill=(0, 0, 0, alpha))
    else:
        d.rounded_rectangle(bb, s(r), fill=(0, 0, 0, alpha))
    im.alpha_composite(L.filter(ImageFilter.GaussianBlur(s(blur))))


def text(im, xy, txt, size, fill, bold=True, anchor="mm", spacing=0):
    d = ImageDraw.Draw(im, "RGBA")
    f = font(size, bold)
    if not spacing:
        d.text(B(xy), txt, font=f, fill=fill, anchor=anchor)
        return
    widths = [f.getlength(c) + s(spacing) for c in txt]
    total = sum(widths) - s(spacing)
    x = s(xy[0]) - {"m": total / 2, "r": total}.get(anchor[0], 0)
    for c, w in zip(txt, widths):
        d.text((x, s(xy[1])), c, font=f, fill=fill, anchor="l" + anchor[1])
        x += w


def worn_text(im, xy, txt, size, fill, anchor="mm", spacing=0, wear=0.35, seed=1):
    """Stamped or stencilled ink that didn't take everywhere."""
    L = layer()
    text(L, xy, txt, size, fill, anchor=anchor, spacing=spacing)
    n = Image.effect_noise(L.size, 70).filter(ImageFilter.GaussianBlur(1.2))
    n = n.point(lambda v: 255 if v > 128 * (1 - wear) + 40 * wear else int(v * 0.4))
    im.alpha_composite(clip(L, n))


def glow_text(im, xy, txt, size, color, bold=True, anchor="mm", blur=5, strength=2):
    L = layer()
    text(L, xy, txt, size, color + (255,), bold, anchor)
    g = L.filter(ImageFilter.GaussianBlur(s(blur)))
    for _ in range(strength):
        im.alpha_composite(g)
    text(im, xy, txt, size, color, bold, anchor)


def circle(d, c, r, **kw):
    d.ellipse(B((c[0] - r, c[1] - r, c[0] + r, c[1] + r)), **kw)


def disc_mask(c, r_out, r_in=0):
    m = mask_layer()
    d = ImageDraw.Draw(m)
    circle(d, c, r_out, fill=255)
    if r_in:
        circle(d, c, r_in, fill=0)
    return m


def tri(d, cx, cy, size, direction, fill):
    k = size / 2
    pts = {"l": [(cx + k * 0.8, cy - k), (cx + k * 0.8, cy + k), (cx - k * 0.9, cy)],
           "r": [(cx - k * 0.8, cy - k), (cx - k * 0.8, cy + k), (cx + k * 0.9, cy)],
           "u": [(cx - k, cy + k * 0.8), (cx + k, cy + k * 0.8), (cx, cy - k * 0.9)],
           "d": [(cx - k, cy - k * 0.8), (cx + k, cy - k * 0.8), (cx, cy + k * 0.9)]}[direction]
    d.polygon([B(p) for p in pts], fill=fill)


def bezier(p0, p1, p2, p3, n=48):
    out = []
    for i in range(n + 1):
        t = i / n
        u = 1 - t
        out.append((u ** 3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t ** 3 * p3[0],
                    u ** 3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t ** 3 * p3[1]))
    return out


# ---- wear and tear ---------------------------------------------------------------------------------------------------------
def dust(im, box, n, light=True, hairs=0, mask=None, seed=0, big=1.0, alpha=(40, 160)):
    r = random.Random(seed)
    L = layer()
    d = ImageDraw.Draw(L)
    col = (236, 232, 222) if light else (46, 38, 30)
    for _ in range(n):
        x, y = r.uniform(box[0], box[2]), r.uniform(box[1], box[3])
        size = r.choice((0.45, 0.45, 0.45, 0.6, 0.6, 0.8, 1.1)) * (big if r.random() < 0.1 else 1)
        circle(d, (x, y), size, fill=col + (r.randint(*alpha),))
    for _ in range(hairs):
        x, y = r.uniform(box[0], box[2]), r.uniform(box[1], box[3])
        ln, a = r.uniform(7, 24), r.uniform(0, 6.28)
        p3 = (x + ln * math.cos(a), y + ln * math.sin(a))
        c1 = (x + ln * 0.3 * math.cos(a) + r.uniform(-5, 5), y + ln * 0.3 * math.sin(a) + r.uniform(-5, 5))
        c2 = (x + ln * 0.7 * math.cos(a) + r.uniform(-5, 5), y + ln * 0.7 * math.sin(a) + r.uniform(-5, 5))
        d.line([B(p) for p in bezier((x, y), c1, c2, p3, 14)], fill=col + (r.randint(60, 130),), width=1)
    if mask is not None:
        clip(L, mask)
    im.alpha_composite(L)


def stains(im, box, n, color=(120, 80, 40), alpha=(8, 22), size=(10, 40), mask=None, seed=0):
    r = random.Random(seed)
    L = layer()
    d = ImageDraw.Draw(L)
    for _ in range(n):
        x, y, rr = r.uniform(box[0], box[2]), r.uniform(box[1], box[3]), r.uniform(*size)
        circle(d, (x, y), rr, fill=color + (r.randint(*alpha),))
    L = L.filter(ImageFilter.GaussianBlur(s(6)))
    if mask is not None:
        clip(L, mask)
    im.alpha_composite(L)


def coffee_ring(im, c, r, alpha=90):
    L = layer()
    d = ImageDraw.Draw(L)
    circle(d, c, r, outline=(132, 74, 26, alpha), width=s(2.2))
    circle(d, (c[0] + 1.5, c[1] + 1), r - 2, outline=(150, 96, 40, alpha // 3), width=s(4))
    circle(d, (c[0] + 1, c[1] + 0.5), r - 4, fill=(170, 120, 60, alpha // 8))
    L = L.filter(ImageFilter.GaussianBlur(s(0.8)))
    gap = mask_layer()
    ImageDraw.Draw(gap).rectangle(B((0, 0, W, H)), fill=255)
    ImageDraw.Draw(gap).pieslice(B((c[0] - r - 4, c[1] - r - 4, c[0] + r + 4, c[1] + r + 4)), 300, 350, fill=60)
    im.alpha_composite(clip(L, gap))


def scuffs(im, box, n, light=True, seed=0, alpha=(18, 50)):
    r = random.Random(seed)
    d = ImageDraw.Draw(im, "RGBA")
    for _ in range(n):
        x, y = r.uniform(box[0], box[2]), r.uniform(box[1], box[3])
        ln, a = r.uniform(4, 22), r.uniform(-0.4, 0.4) + (0 if r.random() < 0.7 else 1.57)
        d.line(B((x, y, x + ln * math.cos(a), y + ln * math.sin(a))),
               fill=((255, 240, 220) if light else (30, 20, 12)) + (r.randint(*alpha),), width=1)


def finish(im):
    """The whole page under one light: warm grade, vignette, film grain."""
    base = im.convert("RGB")
    base = ImageChops.multiply(base, Image.new("RGB", base.size, (255, 247, 234)))
    v = Image.new("L", (W // 4, H // 4), 0)
    ImageDraw.Draw(v).ellipse((-W * 0.06, -H * 0.12, W / 4 + W * 0.06, H / 4 + H * 0.16), fill=255)
    v = v.filter(ImageFilter.GaussianBlur(W / 26)).resize(base.size, Image.Resampling.BICUBIC)
    dark = Image.new("RGB", base.size, (8, 6, 4))
    base = Image.composite(base, dark, v.point(lambda p: int(255 - (255 - p) * 0.42)))
    # the key light: a warm lamp above the deck's top right, falling off across the crate
    pool = Image.new("L", (W // 4, H // 4), 0)
    ImageDraw.Draw(pool).ellipse((W * 0.04 / 4, -H * 0.55 / 4, W * 0.78 / 4, H * 0.62 / 4), fill=150)
    pool = pool.filter(ImageFilter.GaussianBlur(W / 22)).resize(base.size, Image.Resampling.BICUBIC)
    lit = ImageChops.screen(base, Image.new("RGB", base.size, (60, 46, 30)))
    base = Image.composite(lit, base, pool)
    n = Image.effect_noise(base.size, 28).convert("RGB")
    grained = Image.blend(base, ImageChops.soft_light(base, n), 0.55)
    keep = Image.new("L", base.size, 255)                     # no grain on the vinyl: it read as dust
    ImageDraw.Draw(keep).ellipse((CX - R_VINYL, CY - R_VINYL, CX + R_VINYL, CY + R_VINYL), fill=40)
    return Image.composite(grained, base, keep.filter(ImageFilter.GaussianBlur(3)))


# ---- materials ---------------------------------------------------------------------------------------------------------------
def brushed(im, box, top, bot, r=0, seed=3):
    rr = random.Random(seed)
    grad(im, box, top, bot, r)
    L = Image.new("RGBA", (s(box[2] - box[0]), s(box[3] - box[1])), (0, 0, 0, 0))
    d = ImageDraw.Draw(L)
    for y in range(L.height):
        a = rr.randint(0, 12)
        d.line((0, y, L.width, y), fill=(255, 255, 255, a) if rr.random() < 0.5 else (0, 0, 0, a))
    m = Image.new("L", L.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, L.width - 1, L.height - 1), s(r), fill=255)
    L.putalpha(ImageChops.multiply(L.getchannel("A"), m))
    im.alpha_composite(L, B(box[:2]))


def wood(im, box, base=(150, 112, 76), vertical=False, seed=1):
    r = random.Random(seed)
    grad(im, box, lerp(base, (255, 236, 200), 0.10), lerp(base, (0, 0, 0), 0.16), 0, horizontal=vertical)
    w, h = s(box[2] - box[0]), s(box[3] - box[1])
    L = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(L)
    length, across = (h, w) if vertical else (w, h)
    for _ in range(int(across / 2.6)):
        o = r.uniform(0, across)
        amp, per, ph = r.uniform(1, 6) * S, r.uniform(140, 420) * S, r.uniform(0, 6.3)
        col = lerp(base, (52, 30, 14), r.uniform(0.25, 0.6)) + (r.randint(26, 80),)
        pts = []
        for t in range(0, length + 8, 8):
            v = o + amp * math.sin(t / per * 6.28 + ph)
            pts.append((v, t) if vertical else (t, v))
        d.line(pts, fill=col, width=r.choice((1, 1, 2)))
    for _ in range(2):
        kx, ky = r.uniform(0.1, 0.9) * w, r.uniform(0.2, 0.8) * h
        for k in range(5):
            d.ellipse((kx - (14 - k * 2) * S, ky - (5 - k) * S, kx + (14 - k * 2) * S, ky + (5 - k) * S),
                      outline=lerp(base, (40, 22, 10), 0.5) + (64,), width=1)
    im.alpha_composite(L, B(box[:2]))
    scuffs(im, box, int((box[2] - box[0]) * (box[3] - box[1]) / 900), light=True, seed=seed + 40)
    dust(im, box, int((box[2] - box[0]) * (box[3] - box[1]) / 260), light=True, seed=seed + 41, alpha=(20, 70))


def ply_edge(im, box, vertical=False):
    """The laminated edge of plywood: thin pale and dark layers."""
    d = ImageDraw.Draw(im, "RGBA")
    cols = [(214, 182, 140), (128, 92, 58), (206, 172, 128), (118, 84, 52), (200, 166, 122)]
    n = len(cols)
    for i, c in enumerate(cols):
        if vertical:
            a = box[0] + (box[2] - box[0]) * i / n
            d.rectangle(B((a, box[1], a + (box[2] - box[0]) / n, box[3])), fill=c)
        else:
            a = box[1] + (box[3] - box[1]) * i / n
            d.rectangle(B((box[0], a, box[2], a + (box[3] - box[1]) / n)), fill=c)
    scuffs(im, box, int(max(box[2] - box[0], box[3] - box[1]) / 6), light=False, seed=int(box[0] + box[1]), alpha=(40, 90))


# ---- hardware ----------------------------------------------------------------------------------------------------------------
KEY_STYLES = {
    "silver": ((226, 226, 220), (164, 164, 158), (36, 34, 32)),
    "black": ((70, 70, 72), (28, 28, 30), (232, 226, 210)),
    "red": ((206, 64, 46), (150, 32, 22), (255, 244, 232)),
    "cream": ((244, 236, 218), (208, 196, 172), INK),
}


def key(im, box, style="silver", label=None, size=13, arrow=None, lamp=None, r=4):
    top, bot, ink = KEY_STYLES[style]
    soft_shadow(im, box, r, off=(2, 3), blur=3, alpha=160)
    d = ImageDraw.Draw(im, "RGBA")
    d.rounded_rectangle(B(box), s(r), fill=(18, 18, 18))
    inner = (box[0] + 1, box[1] + 1, box[2] - 1, box[3] - 3)
    grad(im, inner, top, bot, r - 1)
    d.line(B((inner[0] + r, inner[1] + 1, inner[2] - r, inner[1] + 1)), fill=(255, 255, 255, 80), width=s(1))
    d.line(B((inner[0] + r, inner[3] + 1, inner[2] - r, inner[3] + 1)), fill=(0, 0, 0, 120), width=s(1))
    dust(im, inner, int((box[2] - box[0]) / 6), light=style != "cream", seed=int(box[0] * 7 + box[1]), alpha=(20, 60))
    cx, cy = (box[0] + box[2]) / 2, (inner[1] + inner[3]) / 2
    if arrow:
        for i, a in enumerate(arrow):
            tri(d, cx + (i - (len(arrow) - 1) / 2) * size * 0.85, cy, size, a, ink)
    if label:
        text(im, (cx, cy), label, size, ink, spacing=0.4)
    if lamp is not None:
        lx, ly = box[2] - 9, box[1] + 8
        if lamp:
            L = layer()
            circle(ImageDraw.Draw(L), (lx, ly), 6, fill=AMBER + (190,))
            im.alpha_composite(L.filter(ImageFilter.GaussianBlur(s(4))))
        circle(d, (lx, ly), 3, fill=AMBER if lamp else (86, 58, 34), outline=(30, 20, 10))


def knob(im, cx, cy, r, val=0.3, dots=True, ink=(70, 56, 42), body=True):
    d = ImageDraw.Draw(im, "RGBA")
    if dots:
        for i in range(11):
            a = math.radians(-135 + i * 27)
            circle(d, (cx + (r + 10) * math.sin(a), cy - (r + 10) * math.cos(a)), 1.5 if i % 5 else 2.3, fill=ink)
    if not body:
        return
    soft_shadow(im, (cx - r, cy - r, cx + r, cy + r), off=(3, 5), blur=5, alpha=160, ellipse=True)
    circle(d, (cx, cy), r, fill=(24, 24, 26))
    for i in range(48):
        a = math.radians(i * 7.5)
        d.line(B((cx + r * 0.84 * math.sin(a), cy - r * 0.84 * math.cos(a), cx + r * 0.98 * math.sin(a), cy - r * 0.98 * math.cos(a))),
               fill=(66, 66, 70), width=s(1))
    rc = r * 0.76
    L = Image.new("RGBA", (s(2 * rc), s(2 * rc)), (0, 0, 0, 0))
    grad(L, (0, 0, 2 * rc, 2 * rc), (236, 236, 230), (138, 138, 132))
    ld = ImageDraw.Draw(L)
    for k in range(3, int(rc), 2):
        ld.ellipse((s(rc - k), s(rc - k), s(rc + k), s(rc + k)), outline=(255, 255, 255, 24 if k % 4 else 12), width=1)
    hl = Image.new("RGBA", L.size, (0, 0, 0, 0))
    hd = ImageDraw.Draw(hl)
    hd.pieslice((0, 0, s(2 * rc), s(2 * rc)), 205, 245, fill=(255, 255, 255, 70))
    hd.pieslice((0, 0, s(2 * rc), s(2 * rc)), 25, 65, fill=(255, 255, 255, 40))
    L.alpha_composite(hl.filter(ImageFilter.GaussianBlur(s(rc * 0.18))))
    m = Image.new("L", L.size, 0)
    ImageDraw.Draw(m).ellipse((0, 0, L.width - 1, L.height - 1), fill=255)
    L.putalpha(ImageChops.multiply(L.getchannel("A"), m))
    im.alpha_composite(L, (s(cx - rc), s(cy - rc)))
    circle(d, (cx, cy), rc, outline=(56, 56, 58), width=s(1))
    a = math.radians(-135 + val * 270)
    d.line(B((cx + rc * 0.25 * math.sin(a), cy - rc * 0.25 * math.cos(a), cx + rc * 0.92 * math.sin(a), cy - rc * 0.92 * math.cos(a))),
           fill=(30, 30, 32), width=s(3))
    d.line(B((cx + r * 0.84 * math.sin(a), cy - r * 0.84 * math.cos(a), cx + r * 0.99 * math.sin(a), cy - r * 0.99 * math.cos(a))),
           fill=(236, 230, 216), width=s(2))
    dust(im, (cx - rc, cy - rc, cx + rc, cy + rc), int(rc), light=False, seed=int(cx), alpha=(30, 90),
         mask=disc_mask((cx, cy), rc))


def dymo(im, box, txt, size=15, color=(24, 24, 26), seed=0):
    soft_shadow(im, box, 3, off=(1, 2), blur=2, alpha=150)
    d = ImageDraw.Draw(im, "RGBA")
    d.rounded_rectangle(B(box), s(2.5), fill=color)
    L = Image.effect_noise((s(box[2] - box[0]), s(box[3] - box[1])), 30).convert("RGBA")
    L.putalpha(16)
    im.alpha_composite(L, B(box[:2]))
    d.line(B((box[0] + 3, box[1] + 2, box[2] - 3, box[1] + 2)), fill=(255, 255, 255, 34), width=s(1))
    d.line(B((box[0] + 3, box[3] - 2, box[2] - 3, box[3] - 2)), fill=(0, 0, 0, 100), width=s(1))
    cy = (box[1] + box[3]) / 2
    text(im, (box[0] + 13, cy + 1), txt, size, (0, 0, 0, 170), anchor="lm", spacing=2.2)
    text(im, (box[0] + 12, cy), txt, size, (234, 232, 224), anchor="lm", spacing=2.2)
    dust(im, box, int((box[2] - box[0]) / 3), light=True, seed=seed, alpha=(20, 70))


# ---- the deck ----------------------------------------------------------------------------------------------------------------
def ring_text(im, c, R, txt, size, fill, start=-1.9, size_im=None):
    f = font(size)
    R2 = R * S
    ang = start
    L = Image.new("RGBA", size_im, (0, 0, 0, 0)) if size_im else layer()
    for ch in txt:
        w = f.getlength(ch)
        a = ang + w / (2 * R2)
        ang += w / R2
        if ch == " ":
            continue
        g = Image.new("RGBA", (int(w) + s(size) * 2, s(size) * 3), (0, 0, 0, 0))
        ImageDraw.Draw(g).text((g.width / 2, g.height / 2), ch, font=f, fill=fill, anchor="mm")
        g = g.rotate(-math.degrees(a), resample=Image.Resampling.BICUBIC, expand=True)
        x, y = s(c[0]) + R2 * math.sin(a), s(c[1]) - R2 * math.cos(a)
        L.alpha_composite(g, (int(x - g.width / 2), int(y - g.height / 2)))
    n = Image.effect_noise(L.size, 60).filter(ImageFilter.GaussianBlur(1)).point(lambda v: 255 if v > 70 else 120)
    im.alpha_composite(clip(L, n))


# the strobe dots: four rows on the rim's bevel, each with its own count (on the real deck one row per speed and mains frequency)
STROBE_ROWS = [(R_VINYL + 5.0, 600), (R_VINYL + 9.2, 610), (R_VINYL + 13.4, 622), (R_VINYL + 17.4, 632)]


def platter_and_record(im):
    d = ImageDraw.Draw(im, "RGBA")
    # the recess the platter sits in, and the platter's own shadow
    circle(d, (CX, CY), R_PLATTER + 6, fill=(44, 44, 42))
    circle(d, (CX, CY), R_PLATTER + 6, outline=(232, 232, 226, 120), width=s(1))       # the recess's lit lip
    soft_shadow(im, (CX - R_PLATTER, CY - R_PLATTER, CX + R_PLATTER, CY + R_PLATTER), off=(8, 13), blur=12, alpha=220, ellipse=True)
    # the platter's rim: a bevel turned away from the light, four rows of machined strobe dots on it, a chrome lip at its edge
    rim = disc_mask((CX, CY), R_PLATTER, R_VINYL)
    for k in range(int((R_PLATTER - R_VINYL) * S)):                  # the bevel: lighter where it turns up to the lip
        rr = R_VINYL + k / S
        v = int(lerp((70,), (128,), (k / S / (R_PLATTER - R_VINYL)) ** 1.6)[0])
        circle(d, (CX, CY), rr, outline=(v, v, v + 2), width=2)
    L = layer()
    ld = ImageDraw.Draw(L)
    box = B((CX - R_PLATTER, CY - R_PLATTER, CX + R_PLATTER, CY + R_PLATTER))
    for a0, a1, al in ((-20, 40, 120), (40, 70, 50), (190, 250, 70)):    # the lamp's highlight off the bevel, and the room's
        ld.pieslice(box, a0, a1, fill=(255, 255, 255, al))
    im.alpha_composite(clip(L.filter(ImageFilter.GaussianBlur(s(14))), rim))
    for rr, n in STROBE_ROWS:
        for i in range(n):
            a = 2 * math.pi * i / n
            x, y = CX + rr * math.cos(a), CY + rr * math.sin(a)
            if -4 < x < PLINTH_X and -4 < y < H + 4:
                lit = 0.55 + 0.45 * max(0.0, math.cos(a - math.radians(-25)))   # facing the lamp: brighter
                circle(d, (x + 0.35, y + 0.45), 1.15, fill=(20, 20, 22, 200))          # each dot's shade
                circle(d, (x, y), 1.1, fill=lerp((120, 120, 118), (236, 236, 230), lit))
                circle(d, (x - 0.35, y - 0.35), 0.4, fill=(255, 255, 252, int(200 * lit)))
    d.arc(B((CX - R_PLATTER + 1, CY - R_PLATTER + 1, CX + R_PLATTER - 1, CY + R_PLATTER - 1)), 0, 360, fill=(188, 188, 184), width=s(2.2))
    d.arc(B((CX - R_PLATTER + 1, CY - R_PLATTER + 1, CX + R_PLATTER - 1, CY + R_PLATTER - 1)), 200, 330, fill=(246, 246, 242), width=s(1.2))
    d.arc(B((CX - R_PLATTER + 1, CY - R_PLATTER + 1, CX + R_PLATTER - 1, CY + R_PLATTER - 1)), 20, 150, fill=(96, 96, 94), width=s(1.2))
    circle(d, (CX, CY), R_PLATTER, outline=(46, 46, 46), width=s(1))
    circle(d, (CX, CY), R_VINYL + 1, outline=(26, 26, 28, 200), width=s(1))

    # the record: grooves, the gaps between tracks, lead-in and run-out
    circle(d, (CX, CY), R_VINYL, fill=(13, 13, 15))
    r = R_VINYL - 2
    gaps = (222, 258, 290, 318)
    while r > R_LABEL + 12:
        if r > R_VINYL - 9 or r < R_LABEL + 22:
            v = 20
        else:
            v = 24 + int(9 * (0.5 + 0.5 * math.sin(r * 2.7))) + rng.randint(-4, 4)
            if any(abs(r - g) < 1.8 for g in gaps):
                v = 8
        circle(d, (CX, CY), r, outline=(v, v, v + 2), width=1)
        r -= 0.62
    circle(d, (CX, CY), R_VINYL - 0.5, outline=(74, 74, 78), width=s(1))
    # anisotropic sheen: bright bands along the light's direction and its opposite
    L = layer()
    ld = ImageDraw.Draw(L)
    box = B((CX - R_VINYL, CY - R_VINYL, CX + R_VINYL, CY + R_VINYL))
    for a in range(0, 360, 2):
        k = max(0.0, math.cos(math.radians(2 * (a - 52)))) ** 30 * 104 + max(0.0, math.cos(math.radians(2 * (a - 14)))) ** 60 * 44
        if k > 2:
            ld.pieslice(box, a, a + 2, fill=(226, 220, 208, int(k)))
    groove_mask = disc_mask((CX, CY), R_VINYL - 3, R_LABEL + 4)
    im.alpha_composite(clip(L.filter(ImageFilter.GaussianBlur(s(5))), groove_mask))
    # the record's edge stands off the mat: a dark rim shadow on the platter, a fine lit bead on the vinyl's edge
    L = layer()
    circle(ImageDraw.Draw(L), (CX + 3, CY + 4), R_VINYL + 2, outline=(0, 0, 0, 170), width=s(5))
    im.alpha_composite(clip(L.filter(ImageFilter.GaussianBlur(s(3))), disc_mask((CX, CY), R_PLATTER, R_VINYL)))
    ImageDraw.Draw(im, "RGBA").arc(B((CX - R_VINYL + 1, CY - R_VINYL + 1, CX + R_VINYL - 1, CY + R_VINYL - 1)), 190, 330, fill=(200, 200, 196, 90), width=s(1))
    # handled: fingerprint haze, a few hairline scratches, dust and fluff
    L = layer()
    ld = ImageDraw.Draw(L)
    for c, rr in (((392, 420), 34), ((300, 470), 26)):
        for k in range(9):
            circle(ld, (c[0] + k * 0.6, c[1] - k * 0.4), rr - k * 3, outline=(255, 255, 255, 10), width=s(1.2))
    im.alpha_composite(clip(L.filter(ImageFilter.GaussianBlur(s(1.2))), groove_mask))
    r2 = random.Random(5)
    L = layer()
    ld = ImageDraw.Draw(L)
    for _ in range(7):
        a0 = r2.uniform(-0.3, 1.9)
        rr = r2.uniform(R_LABEL + 30, R_VINYL - 20)
        x, y = CX + rr * math.cos(a0), CY + rr * math.sin(a0)
        ln, a = r2.uniform(20, 70), r2.uniform(0, 6.28)
        ld.line(B((x, y, x + ln * math.cos(a), y + ln * math.sin(a))), fill=(255, 255, 255, r2.randint(14, 30)), width=1)
    im.alpha_composite(clip(L, groove_mask))


def label_paper(im, colour, c=None):
    """The label's paper ring in one colour: aged, with a printed rim line. c: its centre (the skin draws it on a small canvas)."""
    c = c or (CX, CY)
    d = ImageDraw.Draw(im, "RGBA")
    circle(d, c, R_LABEL, fill=colour)
    circle(d, c, R_DISP + 2, fill=(0, 0, 0, 0))
    L = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(L).ellipse(B((c[0] - R_LABEL, c[1] - R_LABEL, c[0] + R_LABEL * 0.6, c[1] + R_LABEL * 0.4)), fill=(255, 255, 255, 30))
    L = L.filter(ImageFilter.GaussianBlur(s(18)))
    m = Image.new("L", im.size, 0)
    ImageDraw.Draw(m).ellipse(B((c[0] - R_LABEL, c[1] - R_LABEL, c[0] + R_LABEL, c[1] + R_LABEL)), fill=255)
    ImageDraw.Draw(m).ellipse(B((c[0] - R_DISP - 2, c[1] - R_DISP - 2, c[0] + R_DISP + 2, c[1] + R_DISP + 2)), fill=0)
    im.alpha_composite(clip(L, m))
    edge = lerp(colour, (0, 0, 0), 0.22)
    circle(d, c, R_LABEL - 1.5, outline=edge + (200,), width=s(1))


def label_base(im, c=None):
    """The label under the cover's halftone dots: cream paper, lit from the upper left, darker to its edge. The skin's background."""
    c = c or (CX, CY)
    L = Image.new("RGBA", im.size, (0, 0, 0, 0))
    grad(L, (c[0] - R_LABEL, c[1] - R_LABEL, c[0] + R_LABEL, c[1] + R_LABEL), (240, 230, 206), (206, 192, 162), r=R_LABEL)
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    circle(ImageDraw.Draw(sh), c, R_LABEL - 6, outline=(70, 50, 30, 60), width=s(14))
    L.alpha_composite(sh.filter(ImageFilter.GaussianBlur(s(8))))
    im.alpha_composite(clip(L, disc_mask(c, R_LABEL)) if c == (CX, CY) else L)


def label_band(im, c):
    """The label's paper ring round the display (the skin's turning print sits on it): opaque, aged, lit from the upper left."""
    L = Image.new("RGBA", im.size, (0, 0, 0, 0))
    grad(L, (c[0] - R_LABEL, c[1] - R_LABEL, c[0] + R_LABEL, c[1] + R_LABEL), (240, 230, 206), (206, 192, 162), r=R_LABEL)
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    circle(ImageDraw.Draw(sh), c, R_LABEL - 6, outline=(70, 50, 30, 60), width=s(14))
    L.alpha_composite(sh.filter(ImageFilter.GaussianBlur(s(8))))
    m = Image.new("L", im.size, 0)
    ImageDraw.Draw(m).ellipse(B((c[0] - R_LABEL, c[1] - R_LABEL, c[0] + R_LABEL, c[1] + R_LABEL)), fill=255)
    ImageDraw.Draw(m).ellipse(B((c[0] - R_DISP - 3, c[1] - R_DISP - 3, c[0] + R_DISP + 3, c[1] + R_DISP + 3)), fill=0)
    im.alpha_composite(clip(L, m))


def label_print(im, c=None, period=4):
    """What is printed on the label, plus its dust and wear: it turns with the record. It repeats every 360/period degrees, so a turn
    shown over a knob's 270 degrees still wraps without a jump."""
    c = c or (CX, CY)
    d = ImageDraw.Draw(im, "RGBA")
    circle(d, c, R_LABEL - 5, outline=(120, 30, 24, 150), width=s(1))
    R = (R_LABEL + R_DISP) / 2 + 0.5
    seg = "CRATE DIGGER   \u00b7   33 RPM   \u00b7   SIDE A   \u00b7   "
    f = font(11)
    span = sum(f.getlength(ch) for ch in seg) / (R * S)
    for k in range(period):
        ring_text(im, c, R, seg, 11, (120, 30, 24, 210), start=k * 2 * math.pi / period - span / 2, size_im=im.size)
    r = random.Random(4)
    for _ in range(70):                                       # specks and wear, the same in every segment
        a, rr, sz, al = r.uniform(0, 2 * math.pi / period), r.uniform(R_DISP + 4, R_LABEL - 2), r.choice((0.5, 0.6, 0.8, 1.1)), r.randint(30, 110)
        light = r.random() < 0.4
        for k in range(period):
            t = a + k * 2 * math.pi / period
            circle(d, (c[0] + rr * math.cos(t), c[1] + rr * math.sin(t)), sz, fill=((240, 236, 226) if light else (60, 46, 34)) + (al,))


def label_display(im, now, status, time_):
    d = ImageDraw.Draw(im, "RGBA")
    if LIVE:   # in the skin the paper ring turns with its print (a rotating image) round the display, where the cover's dots light
        label_paper(im, PAPER)
        label_print(im)
    else:
        label_base(im)
        circle(ImageDraw.Draw(im, "RGBA"), (CX, CY), R_DISP + 3, fill=(14, 10, 9))
    if LIVE:   # in the skin the glass is its own translucent layer over the cover's cells (tools/skin_deck.py)
        display_glass(im)
        glow_text(im, (CX, CY - 86), status, 14, AMBER_DIM, blur=3, strength=1)
        glow_text(im, (CX, CY - 46), now, 20, AMBER, blur=4)
        glow_text(im, (CX, CY + 54), time_, 50, AMBER, blur=7)


def display_glass(im, c=None, alpha=180):
    """The display in the label: a bezel, smoked glass (alpha: how much of the label shows through it), a VFD mesh, its printed
    legends, a soft reflection, dust, the spindle. c: the centre (the skin draws it on a small canvas)."""
    cx, cy = c or (CX, CY)
    d = ImageDraw.Draw(im, "RGBA")
    circle(d, (cx, cy), R_DISP + 3, outline=(64, 60, 56), width=s(2))
    L = Image.new("RGBA", im.size, (0, 0, 0, 0))
    grad(L, (cx - R_DISP, cy - R_DISP, cx + R_DISP, cy + R_DISP), (32, 14, 8, alpha), (10, 6, 5, min(255, alpha + 30)), r=R_DISP)
    ld = ImageDraw.Draw(L)
    for yy in range(int(cy - R_DISP), int(cy + R_DISP), 2):
        ld.line(B((cx - R_DISP, yy, cx + R_DISP, yy)), fill=(0, 0, 0, 46), width=1)
    im.alpha_composite(clip(L, disc_mask((cx, cy), R_DISP) if c is None else
                            (lambda m: (ImageDraw.Draw(m).ellipse(B((cx - R_DISP, cy - R_DISP, cx + R_DISP, cy + R_DISP)), fill=255), m)[1])(
                                Image.new("L", im.size, 0))))
    glow_text(im, (cx, cy - 112), "NOW SPINNING", 9, AMBER_LOW, blur=2, strength=1)
    glow_text(im, (cx, cy + 100), "33   \u00b7   SIDE A", 9, AMBER_LOW, blur=2, strength=1)
    dm = Image.new("L", im.size, 0)
    ImageDraw.Draw(dm).ellipse(B((cx - R_DISP, cy - R_DISP, cx + R_DISP, cy + R_DISP)), fill=255)
    L = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(L).ellipse(B((cx - R_DISP * 1.15, cy - R_DISP * 1.25, cx + R_DISP * 0.55, cy - R_DISP * 0.15)), fill=(255, 255, 255, 22))
    im.alpha_composite(clip(L.filter(ImageFilter.GaussianBlur(s(10))), dm))
    dust(im, (cx - R_DISP, cy - R_DISP, cx + R_DISP, cy + R_DISP), 140, light=True, hairs=2, mask=dm, seed=9, alpha=(30, 110))
    circle(d, (cx, cy), R_DISP, outline=(0, 0, 0, 170), width=s(2))
    circle(d, (cx, cy), 8, fill=(190, 190, 184), outline=(56, 56, 56), width=s(1))       # spindle
    circle(d, (cx - 2, cy - 2), 3, fill=(250, 250, 246))


def tube(im, pts, w=9.0):
    """A chromed tube along pts: shadow edge, body, a soft and a sharp highlight on the lit (upper-left) side."""
    d = ImageDraw.Draw(im, "RGBA")
    d.line([B(p) for p in pts], fill=(36, 36, 38), width=s(w + 3), joint="curve")
    d.line([B(p) for p in pts], fill=(150, 150, 146), width=s(w), joint="curve")
    d.line([B((x - w * 0.12, y - w * 0.06)) for x, y in pts], fill=(196, 196, 190), width=s(w * 0.62), joint="curve")
    d.line([B((x - w * 0.22, y - w * 0.12)) for x, y in pts], fill=(236, 236, 230), width=s(w * 0.3), joint="curve")
    d.line([B((x - w * 0.26, y - w * 0.16)) for x, y in pts], fill=(255, 255, 252), width=s(1), joint="curve")


def local(origin, ux, uy):
    """Points given along (a) and across (b) a direction, as page coordinates."""
    qx, qy = -uy, ux
    return lambda a, b: (origin[0] + ux * a + qx * b, origin[1] + uy * a + qy * b)


def tonearm(im):
    d = ImageDraw.Draw(im, "RGBA")
    px, py = PIVOT
    # the base: a recessed plate, the height-adjust collar with its scale, the gimbal
    circle(d, PIVOT, 45, fill=(84, 84, 82))
    grad(im, (px - 43, py - 43, px + 43, py + 43), (214, 214, 208), (136, 136, 130), r=43)
    L = layer()
    ld = ImageDraw.Draw(L)
    for k in range(6, 43, 2):
        circle(ld, PIVOT, k, outline=(255, 255, 255, 22 if k % 4 else 10), width=1)
    im.alpha_composite(clip(L, disc_mask(PIVOT, 43)))
    circle(d, PIVOT, 43, outline=(70, 70, 68), width=s(1))
    circle(d, PIVOT, 29, fill=(30, 30, 32))
    for i in range(36):
        a = math.radians(i * 10)
        r0 = 25.5 if i % 3 else 23.5
        d.line(B((px + r0 * math.cos(a), py + r0 * math.sin(a), px + 28 * math.cos(a), py + 28 * math.sin(a))),
               fill=(220, 216, 206), width=1)
    # anti-skate dial on the base's plinth, clear of the arm and its counterweight
    circle(d, (603, 150), 8, fill=(24, 24, 26), outline=(120, 120, 116))
    for i in range(7):
        a = math.radians(-150 + i * 50)
        d.line(B((603 + 5 * math.cos(a), 150 + 5 * math.sin(a), 603 + 7 * math.cos(a), 150 + 7 * math.sin(a))), fill=(230, 226, 214), width=1)
    d.line(B((603, 150, 599, 145)), fill=(250, 120, 60), width=s(1.2))
    # the gimbal and the bearing cap over it (the arm, its counterweight and collar turn above it: arm_parts)
    circle(d, PIVOT, 19, fill=(178, 178, 172), outline=(54, 54, 52), width=s(1))
    grad(im, (px - 15, py - 15, px + 15, py + 15), (238, 238, 232), (120, 120, 116), r=15)
    circle(d, PIVOT, 7, fill=(34, 34, 36))
    circle(d, (px - 2, py - 2), 2.2, fill=(220, 220, 214))

    # the (empty) arm rest with its clip
    circle(d, (586, 254), 7.5, fill=(36, 36, 38))
    circle(d, (586, 254), 5, fill=(150, 150, 146))
    d.arc(B((578, 246, 594, 262)), 200, 340, fill=(220, 220, 214), width=s(1.4))

    if LIVE:
        arm_parts(im)


def arm_rot(p, rot):
    """p turned by rot radians round the pivot."""
    px, py = PIVOT
    c, sn = math.cos(rot), math.sin(rot)
    return (px + (p[0] - px) * c - (p[1] - py) * sn, py + (p[0] - px) * sn + (p[1] - py) * c)


# the S-shaped tube, as (along, across) fractions of the pivot-to-head distance: Bezier control points from the gimbal to the head.
# Its last leg sets the headshell's offset angle (about 22 degrees, turned in towards the spindle, as on a real S-arm).
ARM_S = ((0.036, 0.0), (0.40, 0.045), (0.72, -0.115), (1.0, 0.0))


def arm_curve(A, n, steps=40):
    """The tube's centre line in page coordinates."""
    pts = [A(a * n, b * n) for a, b in ARM_S]
    return bezier(*pts, n=steps)


def arm_frame(rot=0.0):
    """The arm turned by rot: (A, Q, head, length) where A(a, b) is a point a along the pivot-to-head line from the pivot (negative:
    behind it, where the counterweight is) and b across it, head the end of the tube, Q(a, b) the headshell's frame (along the tube's
    last leg: the offset angle)."""
    hx, hy = arm_rot(STYLUS_HEAD, rot)
    px, py = PIVOT
    n = math.hypot(hx - px, hy - py)
    ux, uy = (hx - px) / n, (hy - py) / n
    A = local(PIVOT, ux, uy)
    (a2, b2), (a3, b3) = ARM_S[2], ARM_S[3]
    tx, ty = A((a3 - a2) * n, (b3 - b2) * n)
    tx, ty = tx - px, ty - py
    m = math.hypot(tx, ty)
    vx, vy = tx / m, ty / m
    return A, local(local((hx, hy), vx, vy)(5, 0), vx, vy), (hx, hy), n


def stylus_tip(rot=0.0):
    """Where the stylus touches the record with the arm turned by rot."""
    return arm_frame(rot)[1](56, 0)


def cylinder(im, A, a0, a1, hw, top, bot, ribs=0):
    """A cylinder lying along the arm from a0 to a1, hw wide each side: shaded across, lit from the upper left."""
    d = ImageDraw.Draw(im, "RGBA")
    steps = int(hw * 2 * S)
    for i in range(steps + 1):
        b = -hw + 2 * hw * i / steps
        t = (b + hw) / (2 * hw)
        k = max(0.0, 1.0 - abs(t - 0.32) * 2.4)
        col = lerp(bot, top, k)
        d.line([B(A(a0, b)), B(A(a1, b))], fill=col, width=2)
    if ribs:
        lo, hi = sorted((a0, a1))
        a = lo + ribs
        while a < hi - 0.5:
            d.line([B(A(a, -hw)), B(A(a, hw))], fill=(255, 255, 255, 26), width=s(0.8))
            a += ribs
    d.polygon([B(p) for p in (A(a0, -hw), A(a1, -hw), A(a1, hw), A(a0, hw))], outline=(20, 20, 22))


def arm_parts(im, rot=0.0):
    """The tone arm, straight, as one piece turned by rot radians round the pivot: the tube, the rear stub and its counterweight, the
    collar at the gimbal, the headshell, and their shadow. The skin's arm frames."""
    d = ImageDraw.Draw(im, "RGBA")
    A, Q, head, n = arm_frame(rot)
    shell = [(0, -7), (10, -12), (50, -12), (54, -9), (54, 9), (50, 12), (10, 12), (0, 7)]
    # one shadow for the whole arm (it floats above the record; the light is upper left)
    L = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(L)
    sh = lambda p: B((p[0] + 12, p[1] + 15))
    ld.line([sh(A(-48, 0)), sh(A(10, 0))] + [sh(p) for p in arm_curve(A, n)], fill=(0, 0, 0, 130), width=s(10), joint="curve")
    ld.polygon([sh(A(a, b)) for a, b in ((-18, -14), (-50, -14), (-50, 14), (-18, 14))], fill=(0, 0, 0, 130))
    ld.polygon([sh(Q(a, b)) for a, b in shell], fill=(0, 0, 0, 160))
    im.alpha_composite(L.filter(ImageFilter.GaussianBlur(s(5))))
    # rear stub, then the counterweight: a chromed end cap, a knurled black body, a numbered scale ring nearest the pivot
    tube(im, [A(-6, 0), A(-50, 0)], 7)
    cylinder(im, A, -24, -46, 14, (86, 86, 90), (14, 14, 16), ribs=3)
    cylinder(im, A, -46, -52, 12, (240, 240, 234), (120, 120, 114))
    cylinder(im, A, -18, -24, 14.5, (248, 246, 238), (176, 172, 162))
    for i in range(9):
        b = -12 + i * 3
        d.line([B(A(-19, b)), B(A(-20.5 if i % 2 else -22, b))], fill=(30, 30, 30), width=1)
    # the S-shaped tube from the gimbal to the headshell, and its collar at the gimbal
    tube(im, arm_curve(A, n), 8.5)
    for a in (12, 15):
        circle(d, A(a, 0), 6.5, fill=(40, 40, 42))
    circle(d, A(13.5, 0), 4.2, fill=(176, 176, 170))
    circle(d, PIVOT, 8, fill=(196, 196, 190), outline=(60, 60, 60))
    circle(d, (PIVOT[0] - 2, PIVOT[1] - 2), 2.4, fill=(240, 240, 236))

    # headshell: locking collar, offset body, finger lift, screws, cartridge, stylus guard
    P = lambda a, b: Q(a - 5, b)                                       # the head's frame: Q starts 5 px past the head

    d.polygon([B(P(a, b)) for a, b in ((-4, -6.5), (5, -6.5), (5, 6.5), (-4, 6.5))], fill=(18, 18, 20))   # locking nut
    d.polygon([B(P(a, b)) for a, b in ((-2, -6.5), (0, -6.5), (0, 6.5), (-2, 6.5))], fill=(160, 160, 156))
    d.polygon([B(Q(a, b)) for a, b in shell], fill=(22, 22, 24), outline=(96, 96, 94))
    d.line([B(Q(a, -10.5)) for a in (12, 49)], fill=(255, 255, 255, 50), width=s(1))
    lift = bezier(Q(16, -12), Q(17, -21), Q(21, -28), Q(29, -32), 16)                                      # finger lift
    tube(im, lift, 3.0)
    cart = [(26, -8.5), (49, -8.5), (52, -6), (52, 6), (49, 8.5), (26, 8.5)]                                 # cartridge
    d.polygon([B(Q(a, b)) for a, b in cart], fill=(34, 34, 36), outline=(10, 10, 10))
    d.polygon([B(Q(a, b)) for a, b in ((28, -8.5), (47, -8.5), (47, -5), (28, -5))], fill=(176, 38, 26))
    d.polygon([B(Q(a, b)) for a, b in ((52, -4.5), (58, -4.5), (58, 4.5), (52, 4.5))], fill=(60, 60, 62))  # stylus guard
    for a in (16, 22):
        circle(d, Q(a, -4), 1.5, fill=(214, 214, 208), outline=(60, 60, 60))
        circle(d, Q(a, 4), 1.5, fill=(214, 214, 208), outline=(60, 60, 60))


def strobe_glow(im):
    """The strobe illuminator at the rim, bottom left, lights the dots red while the platter turns."""
    d = ImageDraw.Draw(im, "RGBA")
    a = math.radians(113)
    hx, hy = CX + (R_PLATTER + 16) * math.cos(a), CY + (R_PLATTER + 16) * math.sin(a)
    gx, gy = CX + (R_PLATTER - 6) * math.cos(a), CY + (R_PLATTER - 6) * math.sin(a)
    L = layer()
    circle(ImageDraw.Draw(L), (gx, gy), 34, fill=(255, 50, 30, 210))
    im.alpha_composite(clip(L.filter(ImageFilter.GaussianBlur(s(10))), disc_mask((CX, CY), R_PLATTER, R_VINYL)))
    for rr, n in STROBE_ROWS:
        for i in range(n):
            t = 2 * math.pi * i / n
            x, y = CX + rr * math.cos(t), CY + rr * math.sin(t)
            dist = math.hypot(x - gx, y - gy)
            if dist < 34:
                circle(d, (x, y), 1.1, fill=(255, 110, 80, int(255 * (1 - dist / 34))))
    strobe_lamp(im, True)


def strobe_lamp(im, lit):
    """The strobe lamp's housing at the rim, bottom left: its lens dark red when off, bright when the platter turns. The background always
    has the unlit lamp; the strobe's film strip (strobe_glow) lights it."""
    d = ImageDraw.Draw(im, "RGBA")
    a = math.radians(113)
    hx, hy = CX + (R_PLATTER + 16) * math.cos(a), CY + (R_PLATTER + 16) * math.sin(a)
    circle(d, (hx, hy), 11, fill=(40, 40, 42))
    if lit:
        circle(d, (hx, hy), 8, fill=(236, 54, 34))
        circle(d, (hx - 2, hy - 2), 3, fill=(255, 190, 170, 220))
    else:
        circle(d, (hx, hy), 8, fill=(78, 26, 22))
        circle(d, (hx - 2.5, hy - 2.5), 2.2, fill=(255, 255, 255, 46))
        circle(d, (hx, hy), 8, outline=(20, 8, 6, 160), width=s(1))


def small_key(im, box, label, led=None):
    """The deck's slim keys (33, 45, SKIN): a grey key, its legend, a red LED bar."""
    soft_shadow(im, box, 2, off=(1, 2), blur=2, alpha=150)
    d = ImageDraw.Draw(im, "RGBA")
    d.rounded_rectangle(B(box), s(2), fill=(26, 26, 26))
    grad(im, (box[0] + 1, box[1] + 1, box[2] - 1, box[3] - 2), (216, 216, 210), (168, 168, 162), r=2)
    x0, y0, x1, y1 = box
    h = y1 - y0
    text(im, (x0 + 7, (y0 + y1) / 2 - 1), label, max(7.5, h * 0.42), (36, 36, 34), anchor="lm")
    if led is not None:
        lx0, lx1, ly, lh = x1 - 22, x1 - 7, (y0 + y1) / 2 - 1, max(1.8, h * 0.09)
        if led:
            L = layer()
            ImageDraw.Draw(L).rectangle(B((lx0 - 2, ly - lh - 2, lx1 + 2, ly + lh + 2)), fill=(255, 40, 30, 170))
            im.alpha_composite(L.filter(ImageFilter.GaussianBlur(s(2.5))))
        d.rounded_rectangle(B((lx0, ly - lh, lx1, ly + lh)), s(1), fill=(255, 70, 50) if led else (90, 34, 30))


PITCH_LED = (563, 408)   # the fader's centre mark: lights green only with the pitch at 0 (the skin: a film strip on `pitch`)


def pitch_led(im, lit, c=None):
    cx, cy = c or PITCH_LED
    d = ImageDraw.Draw(im, "RGBA")
    circle(d, (cx, cy), 3.6, fill=(36, 36, 36))
    if lit:
        L = Image.new("RGBA", im.size, (0, 0, 0, 0))
        circle(ImageDraw.Draw(L), (cx, cy), 6, fill=(70, 255, 110, 200))
        im.alpha_composite(L.filter(ImageFilter.GaussianBlur(s(2.5))))
        circle(d, (cx, cy), 2.6, fill=(120, 255, 140))
        circle(d, (cx - 0.8, cy - 0.8), 1, fill=(230, 255, 230))
    else:
        circle(d, (cx, cy), 2.6, fill=(28, 70, 40))
        circle(d, (cx - 0.9, cy - 0.9), 0.9, fill=(255, 255, 255, 50))


def fader_cap(im, cx, cy):
    soft_shadow(im, (cx - 21, cy - 12, cx + 21, cy + 12), 3, off=(3, 4), blur=3, alpha=180)
    grad(im, (cx - 21, cy - 12, cx + 21, cy + 12), (236, 236, 230), (150, 150, 144), r=3)
    d = ImageDraw.Draw(im, "RGBA")
    for k in (-8, -5, -2, 2, 5, 8):
        d.line(B((cx - 18, cy + k, cx + 18, cy + k)), fill=(60, 60, 58, 130), width=s(1))
    d.line(B((cx - 18, cy, cx + 18, cy)), fill=(30, 30, 30), width=s(1.6))


def reset_button(im, cx, cy, pressed=False):
    soft_shadow(im, (cx - 9, cy - 9, cx + 9, cy + 9), off=(1, 1) if pressed else (2, 2), blur=2, alpha=150, ellipse=True)
    grad(im, (cx - 9, cy - 9, cx + 9, cy + 9), (200, 200, 194) if pressed else (240, 240, 234), (150, 150, 144), r=9)
    circle(ImageDraw.Draw(im, "RGBA"), (cx, cy), 9, outline=(80, 80, 78), width=s(1))


# the deck's keys: parameter -> (box, how it's drawn)
DECK_KEYS = {
    "play_pause": (10, 554, 126, 618), "speed_33": (140, 584, 196, 616), "speed_45": (204, 584, 260, 616),
    "rewind_15": (276, 566, 350, 616), "stop": (360, 566, 434, 616), "forward_15": (444, 566, 518, 616),
    "transport_sync": (530, 566, 606, 616),
}


def deck_key(im, k, lit=False, pressed=False, box=None):
    """One of the deck's keys, lit (LED / lamp on) or pressed. box: where (the skin draws it on a small canvas)."""
    b = box or DECK_KEYS[k]
    if k == "play_pause":
        key(im, b, "silver", None)
        text(im, (b[0] + 10, b[3] - 15), "START \u00b7 STOP", 11, (36, 36, 34), anchor="lm", spacing=0.4)
    elif k in ("speed_33", "speed_45"):
        small_key(im, b, {"speed_33": "33", "speed_45": "45"}[k], led=lit)
    elif k == "transport_sync":
        key(im, b, "silver", None, lamp=lit)
        text(im, (b[0] + 9, b[1] + 17), "SYNC", 13, (36, 36, 34), anchor="lm", spacing=0.3)
        text(im, (b[0] + 9, b[3] - 13), "WAIT MPC", 7, (70, 70, 66), anchor="lm", spacing=0.6)
    elif k == "skin":
        key(im, b, "silver", None, lamp=lit)
        text(im, ((b[0] + b[2]) / 2 - 6, (b[1] + b[3]) / 2 - 1), "DECK LOOK", 12, (36, 36, 34), spacing=0.6)
    else:
        key(im, b, "black", None, 13, arrow={"rewind_15": "ll", "forward_15": "rr"}.get(k))
        if k == "stop":
            cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2 - 1
            ImageDraw.Draw(im, "RGBA").rectangle(B((cx - 6, cy - 6, cx + 6, cy + 6)), fill=(232, 226, 210))
    if pressed:
        ImageDraw.Draw(im, "RGBA").rounded_rectangle(B((b[0] + 1, b[1] + 1, b[2] - 1, b[3] - 2)), s(3), fill=(0, 0, 0, 56))


def deck(im, now="OPEN SESAME - TREVOR NOVA", status="STREAMING", time_="0:42", pitch=0.42, playing=True):
    soft_shadow(im, (-20, -10, PLINTH_X, 640), 12, off=(9, 0), blur=10, alpha=210)
    brushed(im, (-20, 0, PLINTH_X, H), (214, 214, 210), (166, 166, 162), r=12)      # satin silver, lit from the top
    d = ImageDraw.Draw(im, "RGBA")
    grad(im, (-20, H - 16, PLINTH_X, H), (148, 148, 142, 0), (40, 40, 38, 200))      # the plinth's front edge turns away from the light
    d.line(B((0, 1, PLINTH_X - 8, 1)), fill=(255, 255, 255, 120), width=s(1))
    d.line(B((PLINTH_X - 1, 10, PLINTH_X - 1, H - 10)), fill=(60, 60, 58, 220), width=s(1))
    d.line(B((PLINTH_X - 3, 10, PLINTH_X - 3, H - 10)), fill=(255, 255, 255, 90), width=s(1))
    stains(im, (0, 0, PLINTH_X, H), 10, color=(60, 50, 40), alpha=(3, 8), size=(20, 60), seed=31)
    dust(im, (0, 0, PLINTH_X, H), 380, light=False, hairs=3, seed=32, alpha=(14, 50))

    platter_and_record(im)
    strobe_lamp(im, False)
    if playing and LIVE:
        strobe_glow(im)
    label_display(im, now, status, time_)

    # 45 adapter, top right
    soft_shadow(im, (514, 22, 542, 50), off=(3, 4), blur=3, alpha=150, ellipse=True)
    grad(im, (514, 22, 542, 50), (240, 240, 234), (130, 130, 124), r=14)
    L = layer()
    for k in range(3, 14, 2):
        circle(ImageDraw.Draw(L), (528, 36), k, outline=(255, 255, 255, 30), width=1)
    im.alpha_composite(L)
    circle(d, (528, 36), 14, outline=(70, 70, 68), width=s(1))
    circle(d, (528, 36), 3.5, fill=(200, 200, 194), outline=(70, 70, 68))

    tonearm(im)

    # pitch: the long fader, its +/-8 scale, centre LED and RESET
    d.rounded_rectangle(B((579, 290, 597, 528)), s(4), fill=(70, 70, 68))
    d.rounded_rectangle(B((584, 294, 592, 524)), s(3), fill=(14, 14, 16))
    for i, lab in enumerate(("8", "6", "4", "2", "0", "2", "4", "6", "8")):
        y = 302 + i * 26.5
        d.line(B((570, y, 576, y)), fill=(40, 40, 38), width=s(1))
        if lab == "0":
            pitch_led(im, LIVE and abs(pitch - 0.5) < 0.003)
        else:
            text(im, (562, y), lab, 6.5, (40, 40, 38))
        if i in (0, 8):
            text(im, (552, y), "+" if i == 0 else "\u2212", 7, (40, 40, 38))     # up is faster: the slider's top is its maximum
    if LIVE:
        fader_cap(im, 588, 302 + (1 - pitch) * 212)
    text(im, (588, 538), "PITCH", 7.5, (40, 40, 38), spacing=0.8)
    if LIVE:
        reset_button(im, 537, 537)
    text(im, (537, 553), "RESET", 6, (40, 40, 38), spacing=0.5)

    # bottom row, as on the deck it's drawn from: START.STOP in the corner, SPEED 33 / 45, then the transport, SYNC and SKIN
    if LIVE:
        for k in DECK_KEYS:
            deck_key(im, k, lit=k in ("speed_33", "transport_sync"))
    text(im, (200, 574), "SPEED", 8.5, (36, 36, 34), spacing=0.6)
    for x, lab in ((313, "-15 S"), (397, "STOP"), (481, "+15 S")):
        text(im, (x, 556), lab, 8.5, (36, 36, 34), spacing=0.5)


def vu_meter(im, box, level, label):
    """A small backlit analog VU meter: black bezel, warm lit face, scale with a red zone, a needle from below the window."""
    x0, y0, x1, y1 = box
    d = ImageDraw.Draw(im, "RGBA")
    soft_shadow(im, box, 3, off=(1, 2), blur=2, alpha=170)
    d.rounded_rectangle(B(box), s(3), fill=(18, 16, 14))
    face = (x0 + 3, y0 + 3, x1 - 3, y1 - 3)
    grad(im, face, (252, 232, 182), (226, 190, 128), r=2)
    L = layer()
    ImageDraw.Draw(L).ellipse(B((x0 + 6, y0 + 8, x1 - 6, y1 + 10)), fill=(255, 200, 110, 120))
    im.alpha_composite(clip(L.filter(ImageFilter.GaussianBlur(s(6))), (lambda m: (ImageDraw.Draw(m).rectangle(B(face), fill=255), m)[1])(mask_layer())))
    cx, cy, R = (x0 + x1) / 2, y1 + 6, (y1 - y0) * 0.86
    for i in range(11):
        a = math.radians(-48 + i * 9.6)
        r0 = R - (5 if i % 5 == 0 else 3)
        col = (190, 40, 26) if i >= 8 else (40, 30, 22)
        d.line(B((cx + r0 * math.sin(a), cy - r0 * math.cos(a), cx + R * math.sin(a), cy - R * math.cos(a))), fill=col, width=s(0.9))
    d.arc(B((cx - R, cy - R, cx + R, cy + R)), 270 - 48, 270 + 29, fill=(40, 30, 22), width=s(0.8))
    d.arc(B((cx - R, cy - R, cx + R, cy + R)), 270 + 29, 270 + 48, fill=(190, 40, 26), width=s(1.6))
    hh = y1 - y0
    text(im, (cx, y1 - hh * 0.24), "VU", hh * 0.15, (60, 44, 30))
    text(im, (x0 + hh * 0.18, y1 - hh * 0.2), label, hh * 0.12, (80, 60, 40))
    if level is not None:
        vu_needle(im, box, level)
    L = layer()                                                                     # the glass
    ImageDraw.Draw(L).polygon(B((x0 + 3, y0 + 3, x0 + 26, y0 + 3, x0 + 12, y1 - 3, x0 + 3, y1 - 3)), fill=(255, 255, 255, 30))
    im.alpha_composite(L)
    d.rectangle(B((x0 + 3, y1 - 6, x1 - 3, y1 - 3)), fill=(30, 24, 18))           # the needle's housing
    dust(im, face, 30, light=True, seed=int(x0), alpha=(30, 90))


def vu_needle(im, box, level):
    x0, y0, x1, y1 = box
    d = ImageDraw.Draw(im, "RGBA")
    cx, cy, R = (x0 + x1) / 2, y1 + 6, (y1 - y0) * 0.86
    a = math.radians(-48 + level * 96)
    L = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(L).line(B((cx + 1.5, cy + 1.5, cx + 1.5 + (R + 1) * math.sin(a), cy + 1.5 - (R + 1) * math.cos(a))), fill=(0, 0, 0, 90), width=s(1.2))
    im.alpha_composite(L.filter(ImageFilter.GaussianBlur(s(0.8))))
    d.line(B((cx, cy, cx + (R + 1) * math.sin(a), cy - (R + 1) * math.cos(a))), fill=(26, 20, 16), width=s(1.1))
    d.rectangle(B((x0 + 3, y1 - 6, x1 - 3, y1 - 3)), fill=(30, 24, 18))           # the needle comes out of its housing


VU_L, VU_R = (668, 494, 848, 560), (860, 494, 1040, 560)
GAIN_KNOB = (1196, 530, 28)
AMP_TOP = 466


def unit(im, top, seed=61):
    """A walnut-cheeked unit standing in front of the crate from top to the floor: the amp (PLAY) or its slim twin (the other tabs)."""
    box = (632, top, 1272, H + 12)
    L = layer()
    ImageDraw.Draw(L).rounded_rectangle(B((box[0] - 4, box[1] - 14, box[2] + 8, box[3])), s(6), fill=(0, 0, 0, 210))
    im.alpha_composite(L.filter(ImageFilter.GaussianBlur(s(12))))
    d = ImageDraw.Draw(im, "RGBA")
    d.rounded_rectangle(B(box), s(6), fill=(16, 12, 10))
    for x0, x1, sd in ((632, 646, seed), (1258, 1272, seed + 1)):                  # walnut cheeks
        wood(im, (x0, top + 1, x1, H), base=(96, 62, 40), vertical=True, seed=sd)
        d.line(B((x0 + 1, top + 2, x0 + 1, H)), fill=(230, 190, 140, 70), width=s(1))
    grad(im, (646, top + 1, 1258, top + 10), (54, 50, 44), (20, 18, 16))           # the lid's front edge
    brushed(im, (646, top + 10, 1258, H), (220, 208, 184), (150, 138, 114), r=1, seed=seed + 2)
    d.line(B((646, top + 10, 1258, top + 10)), fill=(255, 250, 236, 170), width=s(1))
    grad(im, (646, H - 10, 1258, H), (0, 0, 0, 0), (0, 0, 0, 90))                   # the face falls away to the floor
    stains(im, (646, top + 10, 1258, H), 6, color=(80, 60, 40), alpha=(6, 12), size=(10, 30), seed=seed + 3)
    dust(im, (646, top + 10, 1258, H), int((H - top) * 2), light=False, seed=seed + 4, alpha=(14, 50))
    for x in (653, 1251):
        for y in (top + 18, H - 8):
            circle(d, (x, y), 2.6, fill=(150, 144, 130), outline=(70, 64, 54))
            d.line(B((x - 1.7, y - 0.6, x + 1.7, y + 0.6)), fill=(70, 64, 54), width=s(0.8))
    vfd_panel(im, STATUS_BOX, screws=False)
    if LIVE:
        glow_text(im, (STATUS_BOX[0] + 22, (STATUS_BOX[1] + STATUS_BOX[3]) / 2), "DONE - 12 RESULTS IN 3.1S", 16, AMBER, anchor="lm", blur=3)
        key(im, SEARCH_BOX, "red", "SEARCH", 18, r=5)


def engraved(im, xy, txt, size, anchor="mm", spacing=1.0, ink=(54, 46, 36)):
    """Text engraved in the brushed face: a lit lower lip under dark ink."""
    text(im, (xy[0], xy[1] + 0.8), txt, size, (255, 250, 236, 110), anchor=anchor, spacing=spacing)
    text(im, xy, txt, size, ink, anchor=anchor, spacing=spacing)


def console(im, title, seed=71):
    """FILTERS and FIND: the crate gives way to a console that matches the amp (the same cheeks, face and foot), its controls
    mounted in it. The status display and SEARCH sit along its foot as on the amp."""
    unit(im, 14, seed=seed)
    engraved(im, (668, 32), title, 11.5, anchor="lm", spacing=1.6)
    d = ImageDraw.Draw(im, "RGBA")
    d.line(B((656, 566, 1248, 566)), fill=(90, 80, 64, 140), width=s(1))             # the foot's line, as on the amp
    d.line(B((656, 567, 1248, 567)), fill=(255, 250, 236, 90), width=s(1))


def vent(im, box, n=28):
    """A row of vent slots in the face."""
    d = ImageDraw.Draw(im, "RGBA")
    x0, y0, x1, y1 = box
    for i in range(n):
        x = x0 + (x1 - x0) * (i + 0.5) / n
        d.rounded_rectangle(B((x - 1.3, y0, x + 1.3, y1)), s(1.3), fill=(28, 22, 16, 220))
        d.line(B((x - 1, y1 + 0.8, x + 1, y1 + 0.8)), fill=(255, 250, 236, 90), width=s(1))


FILTER_VFD = (656, 38, 1248, 166)
FILTER_X = [718 + i * 116.75 for i in range(5)]


def filters_console(im):
    console(im, "CRATE DIGGER  \u00b7  DISCOGS SELECTOR")
    vfd_panel(im, FILTER_VFD, screws=False)
    d = ImageDraw.Draw(im, "RGBA")
    for i, (num, name, value, v) in enumerate(FILTERS):
        cx = FILTER_X[i]
        if i:
            d.line(B((cx - 58, FILTER_VFD[1] + 12, cx - 58, FILTER_VFD[3] - 12)), fill=AMBER_LOW + (110,), width=s(1))
        glow_text(im, (cx, 62), "%s  %s" % (num, name), 9, AMBER_LOW, blur=2, strength=1)
        fader_slot(im, cx, FADER_Y0, FADER_Y1)
    engraved(im, (952, 548), "STYLE FOLLOWS GENRE    \u00b7    COUNTRY FOLLOWS REGION", 8)


FADER_Y0, FADER_Y1 = 238, 458      # the filter faders' slots (the cap's centre runs FADER_Y0 + 10 .. FADER_Y1 - 10)


def fader_slot(im, cx, y0, y1, ticks=11):
    """A long fader's slot in the face, its scale to the left: the cap is the skin's slider thumb."""
    d = ImageDraw.Draw(im, "RGBA")
    d.rounded_rectangle(B((cx - 9, y0, cx + 9, y1)), s(4), fill=(60, 54, 46))
    d.rounded_rectangle(B((cx - 4, y0 + 4, cx + 4, y1 - 4)), s(3), fill=(12, 10, 9))
    d.line(B((cx - 9, y1 + 0.8, cx + 9, y1 + 0.8)), fill=(255, 250, 236, 100), width=s(1))
    for i in range(ticks):
        y = y0 + 10 + (y1 - y0 - 20) * i / (ticks - 1)
        d.line(B((cx - 24, y, cx - 15 if i % 5 else cx - 12, y)), fill=(54, 46, 36), width=s(1))


FIND_SRC = [("DISCOGS", "source_discogs", (660, 40, 842, 88)), ("YOUTUBE", "source_youtube", (854, 40, 1052, 88)),
            ("CHANNEL", "source_channel", (1064, 40, 1248, 88))]
FIND_VFD = (656, 100, 1248, 214)
FIND_COLS = [(664, 844), (856, 1052), (1064, 1240)]
FIND_YT, FIND_CH = (656, 226, 1050, 420), (1062, 226, 1248, 420)     # the YOUTUBE and CHANNEL sections under the display
FIND_KNOBS = [(1155, "CHANNEL", "channel")]
FIND_FADERS = [(905, "MIN LENGTH", "min_len"), (1003, "MAX LENGTH", "max_len")]   # each under its readout on the display
FIND_FADER_Y = (262, 404)
FIND_MUSIC = (680, 286, 836, 340)


def find_console(im):
    console(im, "CRATE DIGGER  \u00b7  SOURCE SELECTOR")
    vfd_panel(im, FIND_VFD, screws=False)
    d = ImageDraw.Draw(im, "RGBA")
    for i, (x0, x1) in enumerate(FIND_COLS):
        if i:
            d.line(B((x0 - 6, FIND_VFD[1] + 10, x0 - 6, FIND_VFD[3] - 10)), fill=AMBER_LOW + (110,), width=s(1))
    text(im, (672, 116), "FROM THE FILTERS TAB", 7, AMBER_LOW, anchor="lm", spacing=1)
    for j, cap in enumerate(("GENRE", "STYLE", "DECADE", "COUNTRY")):
        text(im, (672, 138 + j * 20), cap, 7, AMBER_LOW, anchor="lm", spacing=1)
    text(im, (954, 116), "MUSIC ONLY", 7, AMBER_LOW, spacing=1)
    for cx, cap, key in FIND_FADERS:
        text(im, (cx, 166), cap, 7, AMBER_LOW, spacing=1)
    text(im, (1072, 116), "CHANNELS.TXT", 7, AMBER_LOW, anchor="lm", spacing=1)
    for (x0, y0, x1, y1), title in ((FIND_YT, "YOUTUBE"), (FIND_CH, "YOUTUBE CHANNEL")):   # two sections, a bracket over each
        cx = (x0 + x1) / 2
        w = font(8).getlength(title) / S / 2 + 12
        d.line(B((x0 + 6, y0 + 8, cx - w, y0 + 8)), fill=(70, 60, 48, 170), width=s(1))
        d.line(B((cx + w, y0 + 8, x1 - 6, y0 + 8)), fill=(70, 60, 48, 170), width=s(1))
        for x in (x0 + 6, x1 - 6):
            d.line(B((x, y0 + 8, x, y0 + 16)), fill=(70, 60, 48, 170), width=s(1))
        engraved(im, (cx, y0 + 8), title, 8)
    for cx, cap, key in FIND_KNOBS:
        engraved(im, (cx, 252), cap, 7.5)
        knob(im, cx, 312, 38, 0.0, body=False, ink=(54, 46, 36))
    for cx, cap, key in FIND_FADERS:
        fader_slot(im, cx, *FIND_FADER_Y, ticks=6)
    engraved(im, ((FIND_MUSIC[0] + FIND_MUSIC[2]) / 2, FIND_MUSIC[1] - 12), "YOUTUBE MUSIC ONLY", 7.5)
    vfd_panel(im, FIND_TEXT, screws=False)
    x0, y0, x1, y1 = FIND_TEXT
    text(im, (x0 + 14, (y0 + y1) / 2), "TEXT", 8, AMBER_LOW, anchor="lm", spacing=1.2)
    kx, ky = x1 - 40, (y0 + y1) / 2                                   # a keyboard glyph: the panel is the key
    d.rounded_rectangle(B((kx - 18, ky - 10, kx + 18, ky + 10)), s(2), outline=AMBER_DIM + (200,), width=s(1))
    for r_, n in ((-5, 6), (0, 6), (5, 4)):
        for i in range(n):
            x = kx - (n - 1) * 2.8 + i * 5.6
            d.rectangle(B((x - 1.6, ky + r_ - 1.2, x + 1.6, ky + r_ + 1.2)), fill=AMBER_DIM + (200,))
    engraved(im, ((SKIN_BOX[0] + SKIN_BOX[2]) / 2, SKIN_BOX[1] - 9), "BACK TO THE SAMPLER", 6.5)
    vent(im, (700, 506, 1060, 540), n=36)


def amp(im, gain=0.62, levels=(0.62, 0.55)):
    """The pre-amp: the whole bottom of the crate on PLAY. The two VU meters and GAIN, the status display and SEARCH below them."""
    unit(im, AMP_TOP)
    d = ImageDraw.Draw(im, "RGBA")
    text(im, (668, 482), "CRATE DIGGER  \u00b7  PRE-AMP", 8, (54, 46, 36), anchor="lm", spacing=1.0)
    d.line(B((656, 568, 1248, 568)), fill=(90, 80, 64, 140), width=s(1))             # the face's two halves
    d.line(B((656, 569, 1248, 569)), fill=(255, 250, 236, 90), width=s(1))
    vu_meter(im, VU_L, levels[0] if LIVE else None, "L")
    vu_meter(im, VU_R, levels[1] if LIVE else None, "R")
    circle(d, (1098, 520), 5, fill=(255, 70, 40), outline=(60, 20, 10))             # jewel lamp
    L = layer()
    circle(ImageDraw.Draw(L), (1098, 520), 10, fill=(255, 60, 30, 150))
    im.alpha_composite(L.filter(ImageFilter.GaussianBlur(s(3))))
    text(im, (1098, 540), "POWER", 7, (70, 60, 48), spacing=1.0)
    gx, gy, gr = GAIN_KNOB
    text(im, (gx - 56, gy), "GAIN", 9, (54, 46, 36), spacing=1.0)
    knob(im, gx, gy, gr, gain, ink=(70, 58, 44), body=LIVE)
    text(im, (854, 482), "MAIN OUTPUT", 7, (70, 60, 48), spacing=1.2)


def vfd_panel(im, box, screws=True):
    """A small display: a bezel (with screws on its own), smoked glass, a dot mesh. The TUI writes the amber text over it."""
    x0, y0, x1, y1 = box
    soft_shadow(im, box, 4, off=(1, 2), blur=2, alpha=160) if not screws else soft_shadow(im, box, 4, off=(3, 5), blur=5, alpha=200)
    grad(im, box, (60, 56, 50), (24, 22, 20), r=4) if not screws else grad(im, box, (150, 148, 142), (88, 86, 82), r=4)
    d = ImageDraw.Draw(im, "RGBA")
    d.rounded_rectangle(B(box), s(4), outline=(30, 30, 30), width=s(1))
    if screws:
        for x in (x0 + 7, x1 - 7):
            circle(d, (x, (y0 + y1) / 2), 2.4, fill=(200, 198, 190), outline=(50, 50, 48))
    g = (x0 + 14, y0 + 5, x1 - 14, y1 - 5) if screws else (x0 + 4, y0 + 4, x1 - 4, y1 - 4)
    grad(im, g, (30, 13, 8), (10, 6, 5), r=2)
    L = layer()
    ld = ImageDraw.Draw(L)
    for yy in range(int(g[1]), int(g[3]), 2):
        ld.line(B((g[0], yy, g[2], yy)), fill=(0, 0, 0, 50), width=1)
    ld.polygon(B((g[0], g[1], g[0] + (g[2] - g[0]) * 0.35, g[1], g[0] + (g[2] - g[0]) * 0.25, g[3], g[0], g[3])), fill=(255, 255, 255, 14))
    im.alpha_composite(L)
    d.rounded_rectangle(B(g), s(2), outline=(0, 0, 0, 200), width=s(1))
    dust(im, g, int((g[2] - g[0]) / 2), light=True, seed=int(x0 + y0), alpha=(20, 70))


# ---- the crate ---------------------------------------------------------------------------------------------------------------
def wall(im, status="DONE - 12 RESULTS IN 3.1S"):
    grad(im, (PLINTH_X, 0, W, H), (40, 35, 31), (22, 19, 17))
    n = Image.effect_noise((s(W - PLINTH_X), s(H)), 40).filter(ImageFilter.GaussianBlur(2)).convert("RGBA")
    n.putalpha(14)
    im.alpha_composite(n, (s(PLINTH_X), 0))
    dust(im, (PLINTH_X, 0, W, CRATE_TOP), 160, light=True, seed=41, alpha=(10, 40))


def crate_back(im):
    soft_shadow(im, (626, CRATE_TOP - 6, 1276, H), 4, off=(0, 6), blur=10, alpha=230)   # the crate on the floor, against the wall
    wood(im, (632, CRATE_TOP, 1268, CRATE_TOP + 18), seed=3)
    ply_edge(im, (632, CRATE_TOP - 2, 1268, CRATE_TOP + 3))
    grad(im, (652, CRATE_TOP + 14, 1248, CRATE_FRONT), (4, 3, 3), (12, 10, 9))     # deep inside: darkest under the back rim


def crate_front(im, stamp="CRATE DIGGER  \u00b7  No. 01", extra=None, with_amp=True, hole=(840, 940)):
    d = ImageDraw.Draw(im, "RGBA")
    for x0, x1, seed in ((630, 654, 11), (1246, 1270, 12)):
        wood(im, (x0, CRATE_TOP, x1, H), vertical=True, seed=seed)
        ply_edge(im, (x0, CRATE_TOP - 4, x1, CRATE_TOP + 2))
        d.line(B((x0, CRATE_TOP, x0, H)), fill=(236, 200, 150, 90), width=s(1))
        d.line(B((x1 - 1, CRATE_TOP, x1 - 1, H)), fill=(30, 16, 6, 170), width=s(1))
    soft_shadow(im, (630, CRATE_FRONT, 1270, CRATE_FRONT + 20), 0, off=(0, -9), blur=8, alpha=230)
    wood(im, (630, CRATE_FRONT, 1270, H), base=(160, 120, 80), seed=5)
    ply_edge(im, (630, CRATE_FRONT - 2, 1270, CRATE_FRONT + 5))
    d.line(B((630, CRATE_FRONT + 5, 1270, CRATE_FRONT + 5)), fill=(60, 34, 14, 140), width=s(1))
    grad(im, (630, CRATE_FRONT + 5, 1270, CRATE_FRONT + 40), (255, 236, 200, 40), (255, 236, 200, 0))   # the light catches its top
    for x in (642, 1258):
        for y in (CRATE_FRONT + 14, CRATE_FRONT + 80):
            circle(d, (x, y), 3.4, fill=(92, 70, 48), outline=(36, 24, 14))
            d.line(B((x - 2.4, y - 1, x + 2.4, y + 1)), fill=(36, 24, 14), width=s(1))
    if not with_amp:
        L = layer()                                    # grime round the hand hole, where it gets handled
        ImageDraw.Draw(L).ellipse(B((hole[0] - 20, CRATE_FRONT + 22, hole[1] + 20, CRATE_FRONT + 80)), fill=(30, 18, 8, 90))
        im.alpha_composite(L.filter(ImageFilter.GaussianBlur(s(10))))
        hb = (hole[0], CRATE_FRONT + 38, hole[1], CRATE_FRONT + 64)
        d.rounded_rectangle(B(hb), s(13), fill=(8, 6, 5))
        d.line(B((hb[0] + 10, hb[1] + 2, hb[2] - 10, hb[1] + 2)), fill=(0, 0, 0, 200), width=s(3))
        d.arc(B(hb), 20, 160, fill=(236, 196, 146, 120), width=s(1))
        if stamp:
            worn_text(im, (664, CRATE_FRONT + 34), stamp, 11, (70, 34, 14, 190), anchor="lm", spacing=1.6, wear=0.4, seed=7)
        if extra:
            extra(im)
        unit(im, 556, seed=66)                         # the slim unit: the status display and SEARCH, as on the amp
    else:   # the amp stands in front of the crate on PLAY only
        amp(im)


def divider_tab(im, x0, x1, y0, label, arrow=None, seed=0):
    soft_shadow(im, (x0, y0, x1, y0 + 60), 7, off=(3, 4), blur=4, alpha=170)
    grad(im, (x0, y0, x1, y0 + 60), (240, 232, 212), (206, 194, 168), r=7)
    d = ImageDraw.Draw(im, "RGBA")
    d.polygon(B((x1 - 12, y0, x1, y0, x1, y0 + 12)), fill=(30, 26, 22))                      # dog-eared corner
    d.polygon(B((x1 - 12, y0, x1, y0 + 12, x1 - 10, y0 + 10)), fill=(196, 182, 152))
    stains(im, (x0, y0, x1, y0 + 60), 5, seed=seed, size=(6, 16))
    dust(im, (x0, y0, x1, y0 + 60), 60, light=False, seed=seed + 1, alpha=(20, 70))
    cx = (x0 + x1) / 2
    if arrow == "l":
        tri(d, x0 + 18, y0 + 17, 11, "l", INK)
        text(im, (cx + 8, y0 + 17), label, 12, INK, spacing=0.8)
    elif arrow == "r":
        tri(d, x1 - 20, y0 + 17, 11, "r", INK)
        text(im, (cx - 8, y0 + 17), label, 12, INK, spacing=0.8)
    else:
        text(im, (cx, y0 + 17), label, 14, INK, spacing=0.6)


CREAM = (234, 232, 224)
# An assortment, as a crate really is: (card colour, finish, print, text ink, sticker dot). The light cards take dark ink and the dark
# ones cream, each pair at a contrast of 4.5:1 or better; the print stays in the strip above the text (or faint under it).
SLEEVES = [((30, 29, 32), "gloss", "none", CREAM, (204, 64, 46)),               # black gloss jacket
           ((198, 160, 112), "kraft", "none", INK, (46, 112, 118)),              # brown cardboard
           ((140, 38, 32), "matte", "company", CREAM, (232, 196, 70)),          # a label's red company sleeve
           ((232, 228, 214), "paper", "none", INK, (54, 86, 146)),              # white paper inner sleeve, yellowed
           ((40, 88, 94), "faded", "none", CREAM, (226, 128, 52)),              # sun-faded teal
           ((206, 154, 56), "matte", "stripes", INK, (140, 38, 32)),            # 70s mustard with a stripe band
           ((30, 42, 74), "matte", "dots", CREAM, (232, 196, 70)),              # navy, printed with dots
           ((196, 192, 180), "kraft", "company", INK, (196, 70, 46))]           # grey board company sleeve
DOTS = [sl[4] for sl in SLEEVES]


def sleeve_texture(im, i, box, col, finish_, print_, mask):
    """One sleeve's card and print, clipped to its box."""
    x0, y0, x1, y1 = box
    r = random.Random(400 + i)
    dark = sum(col) < 360
    L = layer()
    d = ImageDraw.Draw(L)
    if finish_ == "kraft":                                         # fibres
        for _ in range(900):
            x, y = r.uniform(x0, x1), r.uniform(y0, y1)
            ln, a = r.uniform(1.5, 6), r.uniform(-0.5, 0.5)
            c = lerp(col, (255, 240, 210) if r.random() < 0.5 else (60, 40, 20), r.uniform(0.15, 0.35))
            d.line(B((x, y, x + ln * math.cos(a), y + ln * math.sin(a))), fill=c + (r.randint(50, 120),), width=1)
    elif finish_ == "paper":                                       # a soft crease and yellowing at the top edge
        d.rectangle(B((x0, y0, x1, y0 + 8)), fill=(196, 168, 100, 40))
        cx_ = r.uniform(x0 + 120, x1 - 120)
        d.line(B((cx_, y0, cx_ + 14, y1)), fill=(255, 255, 255, 70), width=s(1.5))
        d.line(B((cx_ + 2, y0, cx_ + 16, y1)), fill=(120, 100, 70, 40), width=s(1))
    elif finish_ == "faded":                                       # the end that faced the window is bleached
        pass
    if print_ == "company":                                        # two printed rules and small type along the top
        ink = lerp(col, CREAM if dark else (60, 40, 30), 0.55)
        d.rectangle(B((x0, y0 + 3.5, x1, y0 + 4.5)), fill=ink + (220,))
        d.rectangle(B((x0, y0 + 11, x1, y0 + 11.8)), fill=ink + (200,))
        f = font(6.5)
        t, x = "LONG PLAYING   ·   33⅓ R.P.M.   ·   STEREO   ·   HIGH FIDELITY   ·   ", x0 + 6 - r.uniform(0, 200)
        while x < x1:
            d.text((s(x), s(y0 + 7.8)), t, font=f, fill=ink + (230,), anchor="lm")
            x += f.getlength(t) / S
    elif print_ == "stripes":                                      # a three-colour band across the top
        for k, c in enumerate(((140, 38, 32), (214, 96, 40), (120, 74, 34))):
            d.rectangle(B((x0, y0 + 2 + k * 3.2, x1, y0 + 4.4 + k * 3.2)), fill=c + (235,))
    elif print_ == "dots":                                         # a faint printed dot field
        for yy in range(int(y0) + 4, int(y1), 9):
            off = 4.5 if (yy // 9) % 2 else 0
            for xx in range(int(x0) + 4, int(x1), 9):
                circle(d, (xx + off, yy), 1.3, fill=(110, 134, 190, 46))
    im.alpha_composite(clip(L, mask))
    # the light: a sheen across a gloss card, a sun-bleached end on a faded one
    L = layer()
    d = ImageDraw.Draw(L)
    if finish_ == "gloss":
        d.polygon(B((x0 + 140, y0, x0 + 300, y0, x0 + 250, y1, x0 + 90, y1)), fill=(255, 255, 255, 26))
        d.polygon(B((x0 + 320, y0, x0 + 350, y0, x0 + 300, y1, x0 + 270, y1)), fill=(255, 255, 255, 16))
        L = L.filter(ImageFilter.GaussianBlur(s(10)))
    elif finish_ == "faded":
        d.rectangle(B((x1 - 260, y0, x1, y1)), fill=(190, 200, 186, 70))
        L = L.filter(ImageFilter.GaussianBlur(s(60)))
    im.alpha_composite(clip(L, mask))
RESULTS = [("OPEN SESAME - TREVOR NOVA", "1996", "4:12"), ("AMEN BREAK - THE WINSTONS", "1969", "2:05"),
           ("ACID TRACKS - PHUTURE", "1987", "6:55"), ("DEEP SPACE - NOVA", "1994", "5:40"),
           ("MOVE YOUR BODY - MARSHALL", "1986", "3:30"), ("STRINGS OF LIFE - RHYTHIM", "1987", "5:12"),
           ("NO WAY BACK - ADONIS", "1986", "4:49"), ("(UNTITLED)", "1991", "7:03")]


def sleeves(im, selected=0):
    """The eight results as sleeves in the crate. In the skin (LIVE off) the art has no text and no record pulled up: the row's own
    component draws its text and lights the playing one."""
    d = ImageDraw.Draw(im, "RGBA")
    r = random.Random(12)
    if not LIVE:
        selected = None
    for i, (title, year, length) in enumerate(RESULTS):
        y = ROW0 + i * ROW_H
        x0, x1 = 654, 1246
        if i:
            L = layer()
            ImageDraw.Draw(L).rectangle(B((x0, y - 9, x1, y + 2)), fill=(0, 0, 0, 150))   # the sleeve in front shades this one
            im.alpha_composite(L.filter(ImageFilter.GaussianBlur(s(5))))
        col, finish_, print_, ink, dot = SLEEVES[i]
        dark = sum(col) < 360
        # each sleeve sits a little differently in the crate: a few pixels left or right, a slightly different height of card
        jx0, jx1 = x0 + r.choice((0, 2, 4, 6)), x1 - r.choice((0, 2, 4, 6))
        if i == selected:
            L = layer()
            ImageDraw.Draw(L).rounded_rectangle(B((jx0 - 2, y - 3, jx1 + 2, y + 52)), s(4), fill=AMBER + (170,))
            im.alpha_composite(L.filter(ImageFilter.GaussianBlur(s(8))))
        box = (jx0, y, jx1, y + 64)
        hi = 0.16 if dark else 0.10
        grad(im, box, lerp(col, (255, 255, 255), hi), lerp(col, (0, 0, 0), 0.16), r=2)
        sm = mask_layer()
        ImageDraw.Draw(sm).rounded_rectangle(B(box), s(2), fill=255)
        sleeve_texture(im, i, box, col, finish_, print_, sm)
        # ring wear: the record inside rubbing through (light on a dark card, dark on a light one)
        L = layer()
        ring = (255, 255, 255, 30) if dark else (70, 50, 30, 30)
        ImageDraw.Draw(L).ellipse(B(((jx0 + jx1) / 2 - 300, y + 30, (jx0 + jx1) / 2 + 300, y + 630)), outline=ring, width=s(5))
        im.alpha_composite(clip(L.filter(ImageFilter.GaussianBlur(s(1.5))), sm))
        stains(im, box, 3, seed=50 + i, size=(8, 24), alpha=(6, 18) if not dark else (4, 10), mask=sm)
        dust(im, box, 120, light=dark, seed=60 + i, alpha=(20, 70) if not dark else (14, 46))
        # the card's top edge catches the light; worn edges show the board underneath
        d.line(B((jx0 + 2, y + 1, jx1 - 2, y + 1)), fill=(255, 255, 255, 110 if dark else 140), width=s(1))
        edge = lerp(col, (200, 186, 160) if dark else (110, 90, 64), 0.5)
        for _ in range(30):
            wx = r.uniform(jx0 + 4, jx1 - 4)
            d.line(B((wx, y + 1, wx + r.uniform(4, 22), y + 1)), fill=edge + (130,), width=s(1))
        cx_ding = r.choice((jx0 + 3, jx1 - 3))
        d.polygon(B((cx_ding - 4, y, cx_ding + 4, y, cx_ding, y + 5)), fill=edge + (140,))
        if i == selected:
            d.line(B((jx0 + 2, y + 1, jx1 - 2, y + 1)), fill=AMBER, width=s(2))
        cy = y + 24
        soft_shadow(im, (680 - 9, cy - 9, 680 + 9, cy + 9), off=(0.6, 1.2), blur=1.2, alpha=90, ellipse=True)
        circle(d, (680, cy), 9, fill=dot)                                          # a colour-code sticker
        circle(d, (678, cy - 2.5), 4, fill=(255, 255, 255, 46))
        circle(d, (680, cy), 9, outline=(0, 0, 0, 70), width=s(1))
        if not LIVE:
            continue
        text(im, (704, cy), "%02d  %s  %s  %s" % (i + 1, title, year, length), 17, ink, anchor="lm")


def page_play():
    im = Image.new("RGBA", (W * S, H * S), (20, 18, 17, 255))
    wall(im)
    deck(im)
    crate_back(im)
    divider_tab(im, 664, 784, 60, "PAGE", "l", seed=71)
    divider_tab(im, 880, 1016, 64, "PAGE 1 / 2", seed=72)
    divider_tab(im, 1112, 1232, 60, "PAGE", "r", seed=73)
    sleeves(im, selected=1)
    crate_front(im)
    return im


FILTERS = [("01", "GENRE", "ELECTRONIC", 0.35), ("02", "STYLE", "ACID HOUSE", 0.55), ("03", "DECADE", "1990s", 0.7),
           ("04", "REGION", "EUROPE", 0.3), ("05", "COUNTRY", "GERMANY", 0.45)]


def card(im, x0, x1, y0, tab_off, tab_w, tab_label, body_top=None, dim=False, seed=0, bottom=CRATE_FRONT + 14):
    body_top = body_top or y0 + 28
    soft_shadow(im, (x0, y0, x1, bottom), 6, off=(4, 5), blur=5, alpha=180)
    paper = (236, 226, 204) if not dim else (206, 198, 180)
    if tab_w:
        grad(im, (x0 + tab_off, y0, x0 + tab_off + tab_w, body_top + 8), lerp(paper, (255, 255, 255), 0.18), paper, r=6)
    grad(im, (x0, body_top, x1, bottom), paper, lerp(paper, (0, 0, 0), 0.1), r=3)
    d = ImageDraw.Draw(im, "RGBA")
    for yy in range(int(body_top) + 26, bottom - 20, 24):
        d.line(B((x0 + 6, yy, x1 - 6, yy)), fill=(110, 140, 180, 36), width=s(1))
    d.line(B((x0 + 6, body_top + 12, x1 - 6, body_top + 12)), fill=(190, 76, 66, 70), width=s(1))
    box = (x0, y0, x1, bottom - 20)
    stains(im, box, 8, seed=seed, size=(10, 30), alpha=(6, 20))
    dust(im, box, 180, light=False, seed=seed + 1, alpha=(20, 70))
    scuffs(im, (x0, body_top, x1, bottom - 20), 8, light=False, seed=seed + 2, alpha=(10, 26))
    if tab_label:
        text(im, (x0 + tab_off + tab_w / 2, y0 + 15), tab_label, 10.5, INK, spacing=0.8)


def page_filters():
    im = Image.new("RGBA", (W * S, H * S), (20, 18, 17, 255))
    wall(im)
    deck(im)
    crate_back(im)
    offs = [0, 24, 12, 24, 0]
    for i, (num, name, value, v) in enumerate(FILTERS):
        x0 = 660 + i * 117
        x1 = x0 + 108
        card(im, x0, x1, 62 + (i % 2) * 4, offs[i], 84, f"{num} {name}", seed=80 + i * 5)
        cx = (x0 + x1) / 2
        text(im, (cx, 132), value, 16 if len(value) < 10 else 14.5, INK)
        text(im, (cx, 154), name, 7.5, (126, 104, 84), spacing=1)
        knob(im, cx, 250, 34, v)
        key(im, (x0 + 6, 330, x0 + 52, 370), "black", None, 11, arrow="l")
        key(im, (x0 + 56, 330, x0 + 102, 370), "black", None, 11, arrow="r")
    coffee_ring(im, (1010, 444), 30)
    crate_front(im, stamp=None, extra=filters_front, with_amp=False)
    return im


def filters_front(m):
    """FILTERS: a Dymo title and two stamped notes on the crate's front."""
    dymo(m, (664, CRATE_FRONT + 18, 844, CRATE_FRONT + 48), "DISCOGS FILTERS", 12, seed=43)
    worn_text(m, (1010, CRATE_FRONT + 38), "STYLE FOLLOWS GENRE", 8, (70, 34, 14, 200), anchor="lm", spacing=0.6, wear=0.3, seed=8)
    worn_text(m, (1010, CRATE_FRONT + 52), "COUNTRY FOLLOWS REGION", 8, (70, 34, 14, 200), anchor="lm", spacing=0.6, wear=0.3, seed=9)


FIND_TEXT, FIND_KB = (656, 432, 1248, 482), (1112, 428, 1248, 476)


def find_text(im, query="AMEN BREAK_"):
    """FIND: the typed text on an amber display across the bins, and the KEYBOARD key beside it."""
    vfd_panel(im, FIND_TEXT)
    x0, y0, x1, y1 = FIND_TEXT
    text(im, (x0 + 22, (y0 + y1) / 2), "TEXT", 8, AMBER_LOW, anchor="lm", spacing=1.2)
    if LIVE:
        glow_text(im, (x0 + 66, (y0 + y1) / 2), query, 18, AMBER, anchor="lm", blur=3)
        key(im, FIND_KB, "black", "KEYBOARD", 13)


def page_find():
    im = Image.new("RGBA", (W * S, H * S), (20, 18, 17, 255))
    wall(im)
    deck(im)
    crate_back(im)
    bins = [("DISCOGS", 660, 812, False), ("YOUTUBE", 822, 1080, True), ("CHANNEL", 1090, 1236, False)]
    for k, (name, x0, x1, on) in enumerate(bins):
        card(im, x0, x1, 118, 0, 0, "", body_top=118, dim=not on, seed=90 + k * 5)
        soft_shadow(im, (x0 - 2, 66, x1 + 2, 112), 5, off=(3, 5), blur=5, alpha=200)
        if on:
            L = layer()
            ImageDraw.Draw(L).rounded_rectangle(B((x0 - 2, 66, x1 + 2, 112)), s(6), fill=AMBER + (190,))
            im.alpha_composite(L.filter(ImageFilter.GaussianBlur(s(8))))
        grad(im, (x0 - 2, 66, x1 + 2, 112), (34, 31, 28), (15, 14, 13), r=4)
        ImageDraw.Draw(im, "RGBA").rounded_rectangle(B((x0 + 2, 70, x1 - 2, 108)), s(3), outline=(232, 222, 200, 110), width=s(1))
        dust(im, (x0, 66, x1, 112), 80, light=True, seed=95 + k, alpha=(20, 70))
        if on:
            glow_text(im, ((x0 + x1) / 2, 89), name, 18, AMBER, blur=4)
        else:
            worn_text(im, ((x0 + x1) / 2, 89), name, 18, (224, 214, 192), spacing=1.5, wear=0.25, seed=k)
    for i, (cap, val) in enumerate((("GENRE", "ELECTRONIC"), ("STYLE", "ACID HOUSE"), ("DECADE", "1990s"), ("COUNTRY", "GERMANY"))):
        text(im, (672, 146 + i * 42), cap, 7.5, (116, 96, 76), anchor="lm", spacing=1)
        text(im, (672, 164 + i * 42), val, 14, INK, anchor="lm")
    text(im, (736, 330), "SET ON THE FILTERS TAB", 7.5, (146, 58, 40), spacing=0.6)
    for cx, cap, val, v in ((886, "MIN LENGTH", "ANY", 0.0), (1016, "MAX LENGTH", "6:00", 0.55)):
        text(im, (cx, 142), cap, 8, (106, 86, 66), spacing=1)
        knob(im, cx, 198, 30, v)
        text(im, (cx, 252), val, 15, INK)
        key(im, (cx - 50, 272, cx - 4, 308), "black", None, 10, arrow="l")
        key(im, (cx + 4, 272, cx + 50, 308), "black", None, 10, arrow="r")
    key(im, (846, 330, 1056, 372), "cream", "MUSIC ONLY", 13, lamp=False)
    text(im, (1163, 142), "CHANNELS.TXT", 8, (106, 86, 66), spacing=1)
    text(im, (1163, 168), "NONE - SEE", 13, INK)
    text(im, (1163, 186), "CHANNELS.TXT", 13, INK)
    knob(im, 1163, 246, 30, 0.1)
    key(im, (1113, 300, 1159, 336), "black", None, 10, arrow="l")
    key(im, (1167, 300, 1213, 336), "black", None, 10, arrow="r")
    coffee_ring(im, (742, 476), 26, alpha=80)
    find_text(im)
    crate_front(im, with_amp=False)
    return im


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, fn in (("play", page_play), ("filters", page_filters), ("find", page_find)):
        im = finish(fn().resize((W, H), Image.Resampling.LANCZOS))
        im.save(os.path.join(OUT, name + ".png"))
        print(os.path.join(OUT, name + ".png"))


if __name__ == "__main__":
    main()
