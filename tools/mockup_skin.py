#!/usr/bin/env python3
"""Mock-ups of a redrawn Crate Digger skin, v4 ("S-series rack sampler"): the proportions and materials of the late-80s rack samplers, studied from
photos: off-white faceplate with rack ears, deep blue LCD with F1..F8 tabs along its lower edge, a brushed SCREEN FUNCTION panel with the keys under
it, grey-blue plates, knurled knobs, printed legends and a printed key guide. One main LCD per tab carries the readouts, so no duplicate status
strips. No maker's name or logo. Pictures only, no TUI wiring:   python3 tools/mockup_skin.py   ->  docs/skin-mockups/{play,filters,find,find_keys}.png"""
import math, os, random
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUT = os.path.join(ROOT, "docs", "skin-mockups")
SANSB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
SERIFB = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
S = 2
W, H = 1280, 628
PLATE, EAR, EDGE = (214, 214, 208), (196, 196, 190), (150, 150, 146)           # off-white faceplate, rack ears
BLUEG, BLUEG2, BLUEG3 = (146, 160, 178), (112, 128, 148), (86, 100, 120)         # grey-blue plates
LCD_BG, LCD_BG2, LCD_FG, LCD_DIM = (24, 52, 170), (14, 34, 124), (236, 240, 255), (130, 156, 235)
KEYC, KEYD, INK, RED, BLACK = (238, 238, 232), (100, 104, 112), (30, 30, 32), (196, 40, 32), (22, 22, 24)


def font(size, kind="s"):
    return ImageFont.truetype({"s": SANS, "b": SANSB, "k": SERIFB, "m": MONO}[kind], int(size * S))


class C:
    def __init__(self):
        self.im = Image.new("RGB", (W * S, H * S), PLATE)
        self.d = ImageDraw.Draw(self.im, "RGBA")
        random.seed(11)
        for _ in range(14000):   # fine paint grain
            x, y = random.randrange(W * S), random.randrange(H * S)
            v = random.randint(-6, 6)
            self.d.point((x, y), fill=(255 if v > 0 else 0,) * 3 + (abs(v) * 2,))
        for x0, x1 in ((0, 22), (W - 22, W)):   # rack ears with their oval holes
            self.d.rectangle([x0 * S, 0, x1 * S, H * S], fill=EAR)
        for x in (22, W - 22):
            self.d.line([(x * S, 0), (x * S, H * S)], fill=EDGE, width=2 * S)
        for x in (11, W - 11):
            for y in (60, H - 60):
                self.d.rounded_rectangle([(x - 5) * S, (y - 9) * S, (x + 5) * S, (y + 9) * S], radius=5 * S, fill=(120, 120, 118), outline=(90, 90, 88), width=S)

    def r(self, box, rad=8, fill=None, outline=None, width=1):
        self.d.rounded_rectangle([c * S for c in box], radius=rad * S, fill=fill, outline=outline, width=int(width * S))

    def t(self, xy, text, size=12, fill=INK, anchor="mm", kind="s"):
        if any(ord(ch) > 127 for ch in text) and kind != "m": kind = "b"
        self.d.text((xy[0] * S, xy[1] * S), text, font=font(size, kind), fill=fill, anchor=anchor)

    def ell(self, cx, cy, rx, ry, fill=None, outline=None, width=1):
        self.d.ellipse([(cx - rx) * S, (cy - ry) * S, (cx + rx) * S, (cy + ry) * S], fill=fill, outline=outline, width=int(width * S))

    def line(self, pts, fill, width=1):
        self.d.line([(x * S, y * S) for x, y in pts], fill=fill, width=int(width * S))

    def shadow(self, box, rad=6, blur=4, off=3, alpha=110):
        lay = Image.new("RGBA", self.im.size, (0, 0, 0, 0))
        ImageDraw.Draw(lay).rounded_rectangle([box[0] * S, (box[1] + off) * S, box[2] * S, (box[3] + off) * S], radius=rad * S, fill=(0, 0, 0, alpha))
        lay = lay.filter(ImageFilter.GaussianBlur(blur * S))
        self.im.paste(lay, (0, 0), lay)
        self.d = ImageDraw.Draw(self.im, "RGBA")

    def save(self, name):
        os.makedirs(OUT, exist_ok=True)
        self.im.resize((W, H), Image.LANCZOS).save(os.path.join(OUT, name))

def vgrad(c, box, top, bot, rad=0):
    """A vertical gradient fill (plastic and metal caps are never flat)."""
    x0, y0, x1, y1 = [int(v * S) for v in box]
    g = Image.new("RGB", (x1 - x0, y1 - y0))
    gd = ImageDraw.Draw(g)
    for k in range(y1 - y0):
        t = k / max(1, y1 - y0 - 1)
        gd.line([(0, k), (x1 - x0, k)], fill=tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3)))
    mask = Image.new("L", g.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, g.size[0] - 1, g.size[1] - 1], radius=int(rad * S), fill=255)
    c.im.paste(g, (x0, y0), mask)
    c.d = ImageDraw.Draw(c.im, "RGBA")


def glow(c, cx, cy, r, color, alpha=170):
    """A soft halo, for lit lamps and LED segments."""
    lay = Image.new("RGBA", c.im.size, (0, 0, 0, 0))
    ImageDraw.Draw(lay).ellipse([(cx - r) * S, (cy - r) * S, (cx + r) * S, (cy + r) * S], fill=color + (alpha,))
    lay = lay.filter(ImageFilter.GaussianBlur(r * S * 0.55))
    c.im.paste(lay, (0, 0), lay)
    c.d = ImageDraw.Draw(c.im, "RGBA")


def screws(c, box, inset=9):
    x0, y0, x1, y1 = box
    for i, (x, y) in enumerate(((x0 + inset, y0 + inset), (x1 - inset, y0 + inset), (x0 + inset, y1 - inset), (x1 - inset, y1 - inset))):
        c.ell(x, y, 5, 5, fill=(176, 178, 180), outline=(96, 98, 100), width=1)
        c.ell(x - 1, y - 1, 3, 3, fill=(206, 208, 210))
        a = math.radians(20 + i * 37)
        c.line([(x - math.cos(a) * 4, y - math.sin(a) * 4), (x + math.cos(a) * 4, y + math.sin(a) * 4)], (70, 72, 74), 1.4)
        c.line([(x - math.sin(a) * 4, y + math.cos(a) * 4), (x + math.sin(a) * 4, y - math.cos(a) * 4)], (70, 72, 74), 1.4)


SEG = {"0": "abcdef", "1": "bc", "2": "abdeg", "3": "abcdg", "4": "bcfg", "5": "acdfg", "6": "acdefg", "7": "abc", "8": "abcdefg", "9": "abcdfg", " ": "", "-": "g"}


def led7(c, box, text):
    """A red seven-segment LED window (the Dexed preset-number idea): black glass, dim ghost segments, glowing lit ones."""
    x0, y0, x1, y1 = box
    c.shadow(box, 3, 3, 2, 120)
    c.r(box, 3, fill=(14, 6, 6), outline=(70, 66, 66), width=2)
    n = len(text)
    dw = (x1 - x0 - 10) / n
    for i, ch in enumerate(text):
        cx0, cy0 = x0 + 5 + i * dw + 4, y0 + 6
        w, h, t = dw - 10, y1 - y0 - 12, 4.5
        segs = {"a": (cx0, cy0, w, t), "d": (cx0, cy0 + h - t, w, t), "g": (cx0, cy0 + h / 2 - t / 2, w, t),
                "f": (cx0 - 0, cy0, t, h / 2), "e": (cx0, cy0 + h / 2, t, h / 2), "b": (cx0 + w - t, cy0, t, h / 2), "c": (cx0 + w - t, cy0 + h / 2, t, h / 2)}
        on = SEG.get(ch, "")
        for k, (sx, sy, sw, sh) in segs.items():
            if k in on:
                glow(c, sx + sw / 2, sy + sh / 2, max(sw, sh) * 0.6, (255, 40, 30), 120)
        for k, (sx, sy, sw, sh) in segs.items():
            c.d.rectangle([sx * S, sy * S, (sx + sw) * S, (sy + sh) * S], fill=(255, 70, 52) if k in on else (60, 20, 20))


def lcd(c, box):
    """The recessed black bezel and the deep blue dot-matrix screen: pixel grid, lighter top, inner shadow, a diagonal glass glare."""
    x0, y0, x1, y1 = box
    c.shadow(box, 4, 5, 3, 140)
    c.r(box, 5, fill=BLACK, outline=(70, 70, 74), width=2)
    c.r((x0 + 2, y0 + 2, x1 - 2, y1 - 2), 4, outline=(255, 255, 255, 38), width=1)   # bevel catch-light
    ix0, iy0, ix1, iy1 = x0 + 10, y0 + 10, x1 - 10, y1 - 10
    vgrad(c, (ix0, iy0, ix1, iy1), (34, 66, 186), (18, 42, 140))
    for x in range(int(ix0), int(ix1), 3):
        c.d.line([(x * S, iy0 * S), (x * S, iy1 * S)], fill=(0, 0, 40, 55), width=1)
    for y in range(int(iy0), int(iy1), 3):
        c.d.line([(ix0 * S, y * S), (ix1 * S, y * S)], fill=(0, 0, 40, 55), width=1)
    for k in range(10):   # inner shadow along the top and left edges
        c.d.line([(ix0 * S, (iy0 + k) * S), (ix1 * S, (iy0 + k) * S)], fill=(0, 0, 20, 90 - k * 9), width=S)
        c.d.line([((ix0 + k) * S, iy0 * S), ((ix0 + k) * S, iy1 * S)], fill=(0, 0, 20, 70 - k * 7), width=S)
    gl = Image.new("RGBA", c.im.size, (0, 0, 0, 0))   # glass glare: a pale wedge across the upper left
    ImageDraw.Draw(gl).polygon([(ix0 * S, iy0 * S), ((ix0 + (ix1 - ix0) * 0.42) * S, iy0 * S), (ix0 * S, (iy0 + (iy1 - iy0) * 0.55) * S)], fill=(255, 255, 255, 20))
    c.im.paste(gl, (0, 0), gl)
    c.d = ImageDraw.Draw(c.im, "RGBA")


def lt(c, xy, text, size=15, inv=False, dim=False, anchor="lm"):
    """LCD text: a faint dark shadow one dot down-right, like lit pixels on a dot-matrix panel."""
    if not inv:
        c.t((xy[0] + 1, xy[1] + 1), text, size, (6, 14, 70), anchor, "m")
    c.t(xy, text, size, LCD_BG2 if inv else (LCD_DIM if dim else LCD_FG), anchor, "m")


def invbar(c, x0, y0, x1, y1):
    c.d.rectangle([x0 * S, y0 * S, x1 * S, y1 * S], fill=LCD_FG)


def plate(c, box, title=None, color=BLUEG):
    """A grey-blue printed plate: bevelled edge, a white title strip, screws in the corners."""
    c.shadow(box, 3, 4, 3, 90)
    vgrad(c, box, tuple(min(255, v + 14) for v in color), tuple(max(0, v - 10) for v in color), 3)
    c.r(box, 3, outline=BLUEG3, width=2)
    c.r((box[0] + 2, box[1] + 2, box[2] - 2, box[3] - 2), 2, outline=(255, 255, 255, 60), width=1)
    if title:
        c.t(((box[0] + box[2]) / 2, box[1] + 15), title, 11, (255, 255, 255), "mm", "b")
        c.line([(box[0] + 40, box[1] + 26), (box[2] - 40, box[1] + 26)], (255, 255, 255, 90), 1)
    screws(c, box)


def brushed(c, box):
    """The SCREEN FUNCTION panel: brushed steel in a frame, a step below the faceplate, with screws."""
    x0, y0, x1, y1 = box
    c.shadow(box, 2, 5, 4, 130)
    vgrad(c, box, (208, 210, 212), (180, 182, 184))
    c.d.rectangle([x0 * S, y0 * S, x1 * S, y1 * S], outline=(110, 112, 114), width=2 * S)
    c.d.line([((x0 + 2) * S, (y0 + 2) * S), ((x1 - 2) * S, (y0 + 2) * S)], fill=(255, 255, 255, 140), width=S)
    random.seed(2)
    for y in range(int(y0 + 3), int(y1 - 3)):
        v = random.randint(-16, 16)
        c.d.line([((x0 + 3) * S, y * S), ((x1 - 3) * S, y * S)], fill=(255 if v > 0 else 0,) * 3 + (abs(v) + 4,), width=S)
    screws(c, box, 8)


def bracket(c, x0, x1, y, text):
    mid = (x0 + x1) / 2
    tw = len(text) * 7.6 + 16
    c.line([(x0, y), (mid - tw / 2, y)], INK, 1)
    c.line([(mid + tw / 2, y), (x1, y)], INK, 1)
    c.t((mid, y), text, 10, INK)


def key(c, cx, cy, w, h, legend=None, tab=None, lit=False, red=False, dark=False, legend_below=True, size=10):
    """A square plastic key: gradient cap, bevel and a finger dish. tab = the blue-grey F-number tab above it, legend printed under it;
    lit keys get a glowing LED dash and a halo."""
    box = (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
    c.shadow(box, 3, 3, 3, 140)
    if red:
        top, bot, edge = (206, 58, 46), (140, 22, 18), (70, 12, 10)
    elif dark:
        top, bot, edge = (126, 130, 138), (84, 88, 96), (50, 52, 58)
    else:
        top, bot, edge = (250, 250, 245), (214, 214, 206), (88, 88, 82)
    vgrad(c, box, top, bot, 3)
    c.r(box, 3, outline=edge, width=2)
    c.r((cx - w / 2 + 3, cy - h / 2 + 3, cx + w / 2 - 3, cy + h / 2 - 3), 2, outline=(255, 255, 255, 120 if not red else 70), width=1)
    c.r((cx - w / 2 + 6, cy - h / 2 + 6, cx + w / 2 - 6, cy + h / 2 - 6), 2, outline=(0, 0, 0, 30), width=1)   # the finger dish
    if tab:
        c.r((cx - 16, cy - h / 2 - 17, cx + 16, cy - h / 2 - 5), 2, fill=BLUEG2, outline=BLUEG3)
        c.t((cx, cy - h / 2 - 11), tab, 8, (255, 255, 255), "mm", "b")
    ly = cy - h / 2 - 3 if not tab else cy + h / 2 + 4
    if lit:
        glow(c, cx, ly + 1, 11, (255, 60, 40), 190)
        c.d.rectangle([(cx - 9) * S, (ly - 1.5) * S, (cx + 9) * S, (ly + 2) * S], fill=(255, 96, 70))
    elif tab:
        c.d.rectangle([(cx - 9) * S, (ly - 1.5) * S, (cx + 9) * S, (ly + 2) * S], fill=(70, 70, 72, 150))
    if legend:
        c.t((cx, cy + h / 2 + (20 if tab else 13)), legend, size, INK)


def knob(c, cx, cy, r, value, name=None, big=False, pointer=(245, 245, 240), body=(36, 36, 40)):
    """Knurled knob: big = the grey-blue CURSOR/DATA style with machined rings, otherwise black with a white pointer. A printed dot ruler
    with 0 / 5 / 10 around it, a soft specular highlight, a drop shadow."""
    for i in range(11):
        a = math.radians(135 + i * 27)
        c.ell(cx + math.cos(a) * (r + 10), cy + math.sin(a) * (r + 10), 1.7, 1.7, fill=INK)
        if i in (0, 5, 10):
            c.t((cx + math.cos(a) * (r + 21), cy + math.sin(a) * (r + 21)), str(i), 8, INK)
    c.shadow((cx - r, cy - r, cx + r, cy + r), r, 7, 7, 160)
    if big:
        c.ell(cx, cy, r, r, fill=(104, 114, 134), outline=(46, 52, 66), width=2)
        for i in range(60):   # knurling
            a = math.radians(i * 6)
            c.line([(cx + math.cos(a) * (r - 4), cy + math.sin(a) * (r - 4)), (cx + math.cos(a) * (r - 1), cy + math.sin(a) * (r - 1))], (70, 78, 96), 1)
        c.ell(cx, cy, r - 5, r - 5, fill=(150, 160, 178))
        for k in range(1, 6):   # machined concentric rings
            c.ell(cx, cy, (r - 6) * k / 6, (r - 6) * k / 6, outline=(255, 255, 255, 36) if k % 2 else (0, 0, 0, 24), width=1)
        c.ell(cx - r * 0.18, cy - r * 0.25, r * 0.45, r * 0.3, fill=(255, 255, 255, 40))
    else:
        c.ell(cx, cy, r, r, fill=BLACK, outline=(0, 0, 0), width=2)
        for i in range(44):
            a = math.radians(i * 8.2)
            c.line([(cx + math.cos(a) * (r - 5), cy + math.sin(a) * (r - 5)), (cx + math.cos(a) * (r - 1), cy + math.sin(a) * (r - 1))], (104, 104, 108), 1)
        c.ell(cx, cy, r - 8, r - 8, fill=body, outline=(10, 10, 12), width=1)
        c.ell(cx - 1, cy - 2, r - 14, r - 14, fill=(60, 60, 64))
        c.ell(cx - r * 0.2, cy - r * 0.3, r * 0.4, r * 0.25, fill=(255, 255, 255, 34))
    a = math.radians(135 + value * 270)
    c.line([(cx + math.cos(a) * (r * 0.22), cy + math.sin(a) * (r * 0.22)), (cx + math.cos(a) * (r - 7), cy + math.sin(a) * (r - 7))], pointer if not big else (24, 28, 40), 4)
    if name:
        c.t((cx, cy - r - 32), name, 10, INK)


def header(c, tabname, led="1"):
    """The wordmark in the Dexed manner: bold letters with horizontal stripe cuts and a highlight, a tagline, a model badge, a red LED window."""
    txt = "CRATE DIGGER"
    f = font(30, "k")
    mask = Image.new("L", (W * S, 70 * S), 0)
    ImageDraw.Draw(mask).text((44 * S, 36 * S), txt, font=f, fill=255, anchor="lm")
    for y in range(0, 70 * S, 6 * S):   # stripe cuts
        ImageDraw.Draw(mask).line([(0, y + 3 * S), (W * S, y + 3 * S)], fill=0, width=S)
    grad = Image.new("RGB", (W * S, 70 * S))
    gd = ImageDraw.Draw(grad)
    for y in range(70 * S):
        t = y / (70 * S)
        gd.line([(0, y), (W * S, y)], fill=(int(214 - 56 * t), int(52 - 22 * t), int(40 - 18 * t)))
    c.im.paste(grad, (0, 0), mask)
    c.d = ImageDraw.Draw(c.im, "RGBA")
    c.t((44, 62), "STEREO DIGITAL RECORD SAMPLER", 8, INK, "lm")
    c.line([(44, 71), (330, 71)], (60, 60, 60, 160), 1)
    c.t((560, 46), "DIG 1", 24, (120, 120, 120), "mm", "b")
    c.t((560, 46), "DIG 1", 24, (200, 200, 196), "mm", "b")
    c.d.text((560 * S, 46 * S), "DIG 1", font=font(24, "b"), fill=(214, 214, 208), anchor="mm", stroke_width=S, stroke_fill=(120, 120, 116))
    c.t((650, 36), "PAGE", 8, INK, "mm")
    led7(c, (606, 42, 694, 72), led.rjust(2))


def lcd_head(c, x0, y0, x1, now="OPEN SESAME - TREVOR NOVA", status="STREAMING", time="0:42", search="DONE - 12 RESULTS IN 3.1S"):
    """The readouts every tab shows on its main LCD (three lines)."""
    lt(c, (x0, y0), "NOW", 12, dim=True)
    lt(c, (x0 + 70, y0), now, 16)
    lt(c, (x0, y0 + 22), "STATUS", 12, dim=True)
    lt(c, (x0 + 70, y0 + 22), status, 16)
    lt(c, (x1 - 150, y0 + 22), "TIME", 12, dim=True)
    lt(c, (x1 - 100, y0 + 22), time, 16)
    lt(c, (x0, y0 + 44), "SEARCH", 12, dim=True)
    lt(c, (x0 + 70, y0 + 44), search, 16)


def ftabs(c, x0, x1, y, n=8, labels=None):
    """'< F1 >< F2 >...' along the LCD's lower edge, aligned with the keys under it."""
    step = (x1 - x0) / n
    for i in range(n):
        cx = x0 + step * (i + 0.5)
        lt(c, (cx, y), "< F%d >" % (i + 1) if not labels else labels[i], 12, anchor="mm")


def volume_panel(c, gain=0.5, extra=None):
    """The right-hand plate: MAIN VOLUME (the plugin's gain) and a row of level lamps like the sampler's input section, then page extras."""
    plate(c, (1004, 14, 1250, 614), None)
    c.t((1127, 36), "MAIN VOLUME", 10, (255, 255, 255), "mm", "b")
    c.line([(1030, 47), (1224, 47)], (255, 255, 255, 90), 1)
    knob(c, 1127, 118, 36, gain)
    c.t((1127, 182), "GAIN", 9, INK)
    for i in range(8):   # level lamps
        col = (255, 60, 40) if i == 7 else ((255, 190, 40) if i == 6 else (70, 230, 120))
        on = i < 5
        x = 1052 + i * 21
        if on:
            glow(c, x, 206, 9, col, 130)
        c.ell(x, 206, 5, 5, fill=col if on else tuple(v // 4 for v in col), outline=(40, 40, 40), width=1)
    if extra:
        extra()


def guide(c, x0, y0, w, title, rows):
    """A printed key guide in the S900 manner: a titled grid with a number column."""
    c.d.rectangle([x0 * S, y0 * S, (x0 + w) * S, (y0 + 18) * S], fill=BLUEG3)
    c.t((x0 + w / 2, y0 + 9), title, 9, (255, 255, 255), "mm", "b")
    for i, (a, b) in enumerate(rows):
        y = y0 + 18 + i * 17
        c.d.rectangle([x0 * S, y * S, (x0 + w) * S, (y + 17) * S], fill=(228, 230, 232) if i % 2 == 0 else (214, 217, 221), outline=(120, 124, 130), width=1)
        c.t((x0 + 8, y + 9), a, 8, INK, "lm")
        c.t((x0 + w - 8, y + 9), b, 8, INK, "rm")


def play():
    c = C()
    header(c, "PLAY")
    lcd(c, (40, 76, 988, 436))
    lcd_head(c, 66, 106, 960)
    c.d.rectangle([66 * S, 164 * S, 962 * S, 166 * S], fill=LCD_DIM)
    rows = [("OPEN SESAME", "TREVOR NOVA", "4:12"), ("AMEN BREAK", "THE WINSTONS", "2:05"), ("ACID TRACKS", "PHUTURE", "6:55"), ("DEEP SPACE", "NOVA", "5:40"),
            ("MOVE YOUR BODY", "MARSHALL JEFFERSON", "3:30"), ("STRINGS OF LIFE", "RHYTHIM IS RHYTHIM", "5:12"), ("NO WAY BACK", "ADONIS", "4:49"), ("(UNTITLED)", "", "7:03")]
    for i, (t, a, d) in enumerate(rows):
        col, row = i // 4, i % 4
        x0, y0 = 66 + col * 450, 186 + row * 52
        playing = i == 1
        if playing:
            invbar(c, x0 - 6, y0 - 12, x0 + 436, y0 + 36)
        lt(c, (x0, y0 + 2), "%02d" % (i + 1), 18, inv=playing)
        lt(c, (x0 + 44, y0 + 2), t, 18, inv=playing)
        lt(c, (x0 + 430, y0 + 2), d, 15, inv=playing, anchor="rm")
        lt(c, (x0 + 44, y0 + 26), a, 12, inv=playing, dim=not playing)
    c.d.rectangle([66 * S, 400 * S, 962 * S, 402 * S], fill=LCD_DIM)
    ftabs(c, 66, 962, 418)
    # the SCREEN FUNCTION panel
    brushed(c, (40, 452, 988, 614))
    bracket(c, 60, 968, 470, "SCREEN FUNCTION")
    names = ["BACK 15 S", "PLAY / PAUSE", "STOP", "FORWARD 15 S", "TRANSPORT SYNC", "PAGE ◄", "PAGE ►", "SEARCH"]
    step = (962 - 66) / 8
    for i, n in enumerate(names):
        key(c, 66 + step * (i + 0.5), 530, 88, 44, n, "F%d" % (i + 1), lit=(i == 4), red=(i == 7))
    volume_panel(c, 0.5, extra=lambda: guide(c, 1020, 270, 214, "KEY GUIDE", [("F1  BACK 15 S", "01"), ("F2  PLAY / PAUSE", "02"), ("F3  STOP", "03"), ("F4  FORWARD 15 S", "04"), ("F5  TRANSPORT SYNC", "05"),
                                                                           ("F6  RESULTS PAGE -", "06"), ("F7  RESULTS PAGE +", "07"), ("F8  SEARCH", "08")]))
    c.save("play.png")


def filters():
    c = C()
    header(c, "FILTERS")
    lcd(c, (40, 76, 988, 336))
    lcd_head(c, 66, 106, 960)
    c.d.rectangle([66 * S, 164 * S, 962 * S, 166 * S], fill=LCD_DIM)
    vals = [("GENRE", "ELECTRONIC"), ("STYLE", "ACID HOUSE"), ("DECADE", "1990s"), ("REGION", "EUROPE"), ("COUNTRY", "GERMANY")]
    for i, (k, v) in enumerate(vals):
        y = 188 + i * 25
        sel = i == 1
        if sel:
            invbar(c, 62, y - 11, 520, y + 11)
        lt(c, (70, y), k, 14, inv=sel)
        lt(c, (210, y), v, 15, inv=sel)
    lt(c, (700, 188), "STYLE FOLLOWS GENRE", 11, dim=True)
    lt(c, (700, 213), "COUNTRY FOLLOWS REGION", 11, dim=True)
    plate(c, (40, 350, 988, 614), "DISCOGS FILTERS")
    for i, (k, v) in enumerate(vals):
        cx = 130 + i * 183
        knob(c, cx, 460, 40, [0.35, 0.5, 0.62, 0.3, 0.45][i], k, big=True)
        key(c, cx - 28, 556, 40, 26, "◄", size=9, legend_below=False)
        key(c, cx + 28, 556, 40, 26, "►", size=9, legend_below=False)
    def right():
        key(c, 1127, 380, 190, 56, None, None, red=True, legend_below=False)
        c.t((1127, 380), "SEARCH", 14, (245, 240, 236), "mm", "b")
        c.t((1127, 422), "SEARCH DISCOGS", 9, INK)
    volume_panel(c, 0.5, extra=right)
    c.save("filters.png")


def find(keys=False):
    c = C()
    header(c, "FIND")
    lcd(c, (40, 76, 988, 336))
    lcd_head(c, 66, 106, 960, search="SEARCH YOUTUBE ..." if keys else "DONE - 12 RESULTS IN 3.1S")
    c.d.rectangle([66 * S, 164 * S, 962 * S, 166 * S], fill=LCD_DIM)
    lt(c, (70, 192), "SOURCE", 13, dim=True); lt(c, (170, 192), "YOUTUBE", 15)
    lt(c, (400, 192), "CHANNEL", 13, dim=True); lt(c, (500, 192), "NONE - SEE CHANNELS.TXT", 15)
    lt(c, (70, 218), "LENGTH", 13, dim=True); lt(c, (170, 218), "ANY - ANY", 15)
    lt(c, (400, 218), "MUSIC ONLY", 13, dim=True); lt(c, (540, 218), "OFF", 15)
    lt(c, (70, 258), "TEXT", 13, dim=True)
    invbar(c, 160, 244, 960, 272) if keys else None
    lt(c, (170, 258), "AMEN BREAK_" if keys else "TAP KEYS TO TYPE", 18, inv=keys, dim=not keys)
    ftabs(c, 66, 962, 316)
    brushed(c, (40, 350, 988, 470))
    bracket(c, 60, 968, 366, "SCREEN FUNCTION")
    names = ["DISCOGS", "CHANNEL", "YOUTUBE", "MUSIC ONLY", "KEYBOARD", "", "", "SEARCH"]
    step = (962 - 66) / 8
    for i, n in enumerate(names):
        if n:
            key(c, 66 + step * (i + 0.5), 422, 88, 44, n, "F%d" % (i + 1), lit=(i == 2), red=(i == 7))
    plate(c, (40, 484, 988, 614), "CHANNEL  -  LENGTH")
    for i, (k, v) in enumerate([("CHANNEL", .0), ("MIN LENGTH", .0), ("MAX LENGTH", .0)]):
        cx = 190 + i * 300
        knob(c, cx, 556, 28, v, k, big=True)
        key(c, cx - 66, 556, 34, 26, "◄", size=9, legend_below=False)
        key(c, cx + 66, 556, 34, 26, "►", size=9, legend_below=False)
    volume_panel(c, 0.5)
    if keys:   # the keyboard: grey-blue plate, cream keys, over the lower half
        c.shadow((0, 340, W, H), 0, 8, -3, 170)
        c.d.rectangle([0, 340 * S, W * S, H * S], fill=BLUEG2)
        c.line([(0, 340), (W, 340)], (60, 70, 90), 2)
        c.t((640, 354), "KEYBOARD", 10, (255, 255, 255), "mm", "b")
        rows = ["1234567890", "QWERTYUIOP", "ASDFGHJKL", "ZXCVBNM"]
        for ri, row in enumerate(rows):
            x0 = 118 + [0, 0, 58, 174][ri]
            for k, ch in enumerate(row):
                kx, ky = x0 + k * 116, 372 + ri * 52
                key(c, kx, ky + 22, 100, 42, None)
                c.t((kx, ky + 23), ch, 18, INK, "mm", "b")
        for (cx, cy, w, txt, red) in [(130, 590, 200, "HIDE", False), (520, 590, 520, "SPACE", False), (880, 590, 190, "CLEAR", False), (1130, 590, 220, "SEND", True), (1180, 541, 150, "BACK", False)]:
            key(c, cx, cy, w, 40, None, red=red)
            c.t((cx, cy + 1), txt, 14, (245, 240, 236) if red else INK, "mm", "b")
    c.save("find_keys.png" if keys else "find.png")


if __name__ == "__main__":
    play(); filters(); find(False); find(True)
    print("wrote", os.path.normpath(OUT))
