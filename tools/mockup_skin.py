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
    """(none: the panels are silk-screened sections now)"""
    return


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


SILK = (198, 198, 192)   # a slightly darker grey than the faceplate: a printed (silk-screened) section, flat


def plate(c, box, title=None, color=None):
    """A silk-screened section of the faceplate: flat grey, a thin printed outline, the title printed in the top-left with a rule."""
    x0, y0, x1, y1 = box
    c.r(box, 3, fill=SILK, outline=(70, 70, 68), width=1)
    if title:
        c.t((x0 + 14, y0 + 15), title, 10, INK, "lm", "b")
        c.line([(x0 + 24 + len(title) * 7.4, y0 + 15), (x1 - 14, y0 + 15)], (70, 70, 68), 1)


def brushed(c, box):
    """A silk-screened key section (flat grey, printed outline); the title is printed by bracket()."""
    c.r(box, 3, fill=SILK, outline=(70, 70, 68), width=1)


def bracket(c, x0, x1, y, text):
    """A printed section title: left-aligned small caps and a rule to the right edge."""
    c.t((x0, y), text, 10, INK, "lm", "b")
    c.line([(x0 + 10 + len(text) * 7.6, y), (x1, y)], (70, 70, 68), 1)


KEYCOL = {"cream": ((250, 250, 245), (214, 214, 206), (88, 88, 82), INK), "dark": ((126, 130, 138), (84, 88, 96), (50, 52, 58), (245, 245, 240)),
          "green": ((92, 214, 120), (34, 150, 70), (14, 80, 34), (8, 40, 16)), "red": ((214, 62, 48), (150, 24, 20), (72, 12, 10), (255, 244, 240)),
          "amber": ((255, 214, 96), (232, 160, 30), (120, 78, 8), (50, 30, 0)), "blue": ((120, 170, 240), (58, 106, 190), (26, 54, 110), (255, 255, 255)),
          "white": ((255, 255, 255), (226, 226, 222), (96, 96, 92), INK)}


def key(c, cx, cy, w, h, label=None, color="cream", lit=False, size=13, sub=None):
    """A square plastic key labelled by what it does: gradient cap, bevel, finger dish, a small lamp above when lit (with a halo).
    color tells the key's job at a glance: green PLAY, red SEARCH, amber SYNC, blue SOURCE, cream the rest."""
    top, bot, edge, ink = KEYCOL[color]
    box = (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
    c.shadow(box, 3, 3, 3, 140)
    vgrad(c, box, top, bot, 3)
    c.r(box, 3, outline=edge, width=2)
    c.r((cx - w / 2 + 3, cy - h / 2 + 3, cx + w / 2 - 3, cy + h / 2 - 3), 2, outline=(255, 255, 255, 120), width=1)
    c.r((cx - w / 2 + 6, cy - h / 2 + 6, cx + w / 2 - 6, cy + h / 2 - 6), 2, outline=(0, 0, 0, 30), width=1)
    ly = cy - h / 2 - 4
    if lit:
        glow(c, cx, ly, 10, (255, 60, 40), 190)
        c.d.rectangle([(cx - 9) * S, (ly - 1.5) * S, (cx + 9) * S, (ly + 2) * S], fill=(255, 96, 70))
    else:
        c.d.rectangle([(cx - 9) * S, (ly - 1.5) * S, (cx + 9) * S, (ly + 2) * S], fill=(70, 70, 72, 140))
    if label:
        c.t((cx, cy - (7 if sub else 0) + 1), label, size, ink, "mm", "b")
    if sub:
        c.t((cx, cy + 12), sub, 8, ink, "mm")


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


def header(c, tabname):
    """The wordmark in the Dexed manner: bold letters with horizontal stripe cuts, a tagline and a model badge."""
    txt = "CRATE DIGGER"
    f = font(30, "k")
    mask = Image.new("L", (W * S, 70 * S), 0)
    ImageDraw.Draw(mask).text((44 * S, 36 * S), txt, font=f, fill=255, anchor="lm")
    for y in range(0, 70 * S, 6 * S):
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
    c.d.text((560 * S, 46 * S), "DIG 1", font=font(24, "b"), fill=(214, 214, 208), anchor="mm", stroke_width=S, stroke_fill=(120, 120, 116))


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


def volume_panel(c, gain=0.5, extra=None):
    """The right-hand plate: MAIN VOLUME (the plugin's gain) and the stereo level meter (two rows of lamps), then page extras."""
    plate(c, (1004, 14, 1250, 614), "MAIN VOLUME")
    knob(c, 1127, 118, 36, gain)
    c.t((1127, 182), "GAIN", 9, INK)
    c.t((1127, 214), "LEVEL", 10, INK, "mm", "b")
    for row, lit_n in enumerate((6, 5)):   # L and R
        c.t((1034, 236 + row * 22), "LR"[row], 9, INK)
        for i in range(10):
            col = (255, 60, 40) if i == 9 else ((255, 190, 40) if i >= 7 else (70, 230, 120))
            on = i < lit_n + (2 if i < 6 and row == 0 else 0)
            x, y = 1056 + i * 18, 236 + row * 22
            if on:
                glow(c, x, y, 8, col, 130)
            c.r((x - 6, y - 5, x + 6, y + 5), 2, fill=col if on else tuple(v // 4 for v in col), outline=(40, 40, 40), width=1)
    if extra:
        extra()


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
        x0, y0 = 66 + col * 450, 190 + row * 58
        playing = i == 1
        if playing:
            invbar(c, x0 - 6, y0 - 14, x0 + 436, y0 + 40)
        lt(c, (x0, y0 + 2), "%02d" % (i + 1), 18, inv=playing)
        lt(c, (x0 + 44, y0 + 2), t, 18, inv=playing)
        lt(c, (x0 + 430, y0 + 2), d, 15, inv=playing, anchor="rm")
        lt(c, (x0 + 44, y0 + 26), a, 12, inv=playing, dim=not playing)
    # two separate groups: TRANSPORT, and the results / search controls
    brushed(c, (40, 456, 540, 614))
    bracket(c, 60, 520, 474, "TRANSPORT")
    for i, (lab, col) in enumerate([("◄◄", "cream"), ("▶ ❚❚", "green"), ("■", "white"), ("►►", "cream")]):
        key(c, 110 + i * 118, 540, 98, 62, lab, col, size=20 if i != 1 else 18)
    for i, t in enumerate(["BACK 15 S", "PLAY / PAUSE", "STOP", "FORWARD 15 S"]):
        c.t((110 + i * 118, 584), t, 9, INK)
    brushed(c, (556, 456, 988, 614))
    bracket(c, 576, 968, 474, "RESULTS  /  SEARCH")
    for i, (lab, col, lit) in enumerate([("◄ PAGE", "cream", False), ("PAGE ►", "cream", False), ("SYNC", "amber", True), ("SEARCH", "red", False)]):
        key(c, 612 + i * 100, 540, 86, 62, lab, col, lit=lit, size=13)
    c.t((612 + 2 * 100, 584), "WAIT FOR MPC PLAY", 8, INK)
    volume_panel(c, 0.5)
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
        key(c, cx - 30, 556, 44, 28, "◄", size=12)
        key(c, cx + 30, 556, 44, 28, "►", size=12)
    def right():
        bracket(c, 1024, 1230, 356, "DISCOGS")
        key(c, 1127, 420, 190, 62, "SEARCH", "red", size=16)
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
    lt(c, (70, 270), "TEXT", 13, dim=True)
    invbar(c, 160, 254, 960, 288) if keys else None
    lt(c, (170, 271), "AMEN BREAK_" if keys else "TAP KEYS TO TYPE", 18, inv=keys, dim=not keys)
    # two groups: where to search, and the search itself
    brushed(c, (40, 350, 560, 470))
    bracket(c, 60, 540, 366, "SOURCE")
    for i, (n, lit) in enumerate([("DISCOGS", False), ("CHANNEL", False), ("YOUTUBE", True)]):
        key(c, 112 + i * 160, 424, 138, 54, n, "blue", lit=lit, size=14)
    brushed(c, (576, 350, 988, 470))
    bracket(c, 596, 968, 366, "SEARCH")
    for i, (n, col) in enumerate([("MUSIC ONLY", "cream"), ("KEYBOARD", "dark"), ("SEARCH", "red")]):
        key(c, 650 + i * 130, 424, 116, 54, n, col, size=12 if i < 2 else 14)
    plate(c, (40, 484, 988, 614), None)
    for i, (k, v) in enumerate([("CHANNEL", .0), ("MIN LENGTH", .0), ("MAX LENGTH", .0)]):
        cx = 190 + i * 300
        knob(c, cx, 560, 26, v, k, big=True)
        key(c, cx - 70, 560, 40, 26, "◄", size=11)
        key(c, cx + 70, 560, 40, 26, "►", size=11)
    volume_panel(c, 0.5)
    if keys:
        c.shadow((0, 340, W, H), 0, 8, -3, 170)
        c.d.rectangle([0, 340 * S, W * S, H * S], fill=SILK)
        c.line([(0, 340), (W, 340)], (70, 70, 68), 2)
        c.t((44, 356), "KEYBOARD", 10, INK, "lm", "b")
        c.line([(130, 356), (1236, 356)], (70, 70, 68), 1)
        rows = ["1234567890", "QWERTYUIOP", "ASDFGHJKL", "ZXCVBNM"]
        for ri, row in enumerate(rows):
            x0 = 118 + [0, 0, 58, 174][ri]
            for k, ch in enumerate(row):
                key(c, x0 + k * 116, 372 + ri * 52 + 22, 100, 42, ch, "cream", size=18)
        for (cx, cy, w, txt, col) in [(130, 590, 200, "HIDE", "dark"), (520, 590, 520, "SPACE", "cream"), (880, 590, 190, "CLEAR", "dark"), (1130, 590, 220, "SEARCH", "red"), (1180, 541, 150, "BACK", "dark")]:
            key(c, cx, cy, w, 40, txt, col, size=14)
    c.save("find_keys.png" if keys else "find.png")


if __name__ == "__main__":
    play(); filters(); find(False); find(True)
    print("wrote", os.path.normpath(OUT))
