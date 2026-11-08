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
# the MPC draws live text in Titillium Web, so the art and the previews use it too (the family is on the OFL; only rendered here, not shipped)
TIT = next((f for f in (os.path.expanduser("~/mpc-vst-dx7/fonts/TitilliumWeb-SemiBold.ttf"), os.path.expanduser("~/mpc-vst-plugins-v1/tools/html_art/fonts/TitilliumWeb-SemiBold.ttf"), MONO) if os.path.exists(f)))
TITB = next((f for f in (os.path.expanduser("~/mpc-vst-airwin2rack/tools/art/fonts/TitilliumWeb-Bold.ttf"), os.path.expanduser("~/mpc-vst-plugins-v1/tools/html_art/fonts/TitilliumWeb-Bold.ttf"), SANSB) if os.path.exists(f)))
S = 2
W, H = 1280, 628
PLATE, EAR, EDGE = (214, 214, 208), (196, 196, 190), (150, 150, 146)           # off-white faceplate, rack ears
BLUEG, BLUEG2, BLUEG3 = (146, 160, 178), (112, 128, 148), (86, 100, 120)         # grey-blue plates
LCD_BG, LCD_BG2, LCD_FG, LCD_DIM = (24, 52, 170), (14, 34, 124), (236, 240, 255), (130, 156, 235)
KEYC, KEYD, INK, RED, BLACK = (238, 238, 232), (100, 104, 112), (30, 30, 32), (196, 40, 32), (22, 22, 24)


def font(size, kind="s"):
    return ImageFont.truetype({"s": SANS, "b": SANSB, "k": SERIFB, "m": MONO, "t": TIT, "tb": TITB}[kind], int(size * S))


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
        if any(ord(ch) > 127 for ch in text) and kind not in ("m", "t", "tb"): kind = "b"
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
        c.t((xy[0] + 1, xy[1] + 1), text, size, (6, 14, 70), anchor, "t")
    c.t(xy, text, size, LCD_BG2 if inv else (LCD_DIM if dim else LCD_FG), anchor, "t")


def invbar(c, x0, y0, x1, y1):
    c.d.rectangle([x0 * S, y0 * S, x1 * S, y1 * S], fill=LCD_FG)


SILK = (198, 198, 192)   # a slightly darker grey than the faceplate: a printed (silk-screened) section, flat


SILK = (197, 197, 191)   # a slightly darker grey than the faceplate: a printed (silk-screened) section, flat, no outline


def plate(c, box, title=None, color=None):
    """A silk-screened section of the faceplate: flat grey, the title printed top-left with a thin rule."""
    x0, y0, x1, y1 = box
    c.r(box, 4, fill=SILK)
    if title:
        c.t((x0 + 50, y0 + 15), title, 10, INK, "lm", "b")
        c.line([(x0 + 60 + len(title) * 7.4, y0 + 15), (x1 - 14, y0 + 15)], (120, 120, 116), 1)


def brushed(c, box):
    """A silk-screened key section: flat grey, no outline; the title is printed by bracket()."""
    c.r(box, 4, fill=SILK)


def bracket(c, x0, x1, y, text):
    """A printed section title: left-aligned small caps and a rule to the right edge."""
    x0 += 36   # leave the corner free for the MPC's Q-Link tag
    c.t((x0, y), text, 10, INK, "lm", "b")
    c.line([(x0 + 10 + len(text) * 7.6, y), (x1, y)], (120, 120, 116), 1)


KEYCOL = {"cream": ((250, 250, 245), (214, 214, 206), (88, 88, 82), INK), "dark": ((124, 128, 136), (82, 86, 94), (46, 48, 54), (245, 245, 240)),
          "blue": ((196, 218, 242), (150, 182, 218), (70, 96, 130), (24, 36, 56))}
LAMP = {"green": (70, 230, 120), "red": (255, 60, 40), "amber": (255, 176, 40)}


def key(c, cx, cy, w, h, label=None, color="cream", lit=False, size=13, sub=None, lamp="red"):
    """A square plastic key in the period colours (cream, dark grey, pale blue) labelled by what it does, with the small indicator lamp above
    it (red, green or amber; glowing when lit), as on the sampler's function keys."""
    top, bot, edge, ink = KEYCOL[color]
    box = (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
    c.shadow(box, 3, 3, 3, 140)
    vgrad(c, box, top, bot, 3)
    c.r(box, 3, outline=edge, width=2)
    c.r((cx - w / 2 + 3, cy - h / 2 + 3, cx + w / 2 - 3, cy + h / 2 - 3), 2, outline=(255, 255, 255, 120), width=1)
    c.r((cx - w / 2 + 6, cy - h / 2 + 6, cx + w / 2 - 6, cy + h / 2 - 6), 2, outline=(0, 0, 0, 30), width=1)
    ly = cy - h / 2 - 4
    col = LAMP[lamp] if lamp else None
    if col and lit:
        glow(c, cx, ly, 10, col, 190)
        c.d.rectangle([(cx - 9) * S, (ly - 1.5) * S, (cx + 9) * S, (ly + 2) * S], fill=tuple(min(255, v + 30) for v in col))
    elif col:
        c.d.rectangle([(cx - 9) * S, (ly - 1.5) * S, (cx + 9) * S, (ly + 2) * S], fill=tuple(v // 4 for v in col) + (200,))
    if label:
        c.t((cx, cy - (7 if sub else 0) + 1), label, size, ink, "mm", "b")
    if sub:
        c.t((cx, cy + 12), sub, 8, ink, "mm")


def knob(c, cx, cy, r, value, name=None, big=False, pointer=(245, 245, 240), body=(36, 36, 40), numbers=True, ruler=True, only_ruler=False):
    """Knurled knob: big = the grey-blue CURSOR/DATA style with machined rings, otherwise black with a white pointer. A printed dot ruler
    with 0 / 5 / 10 around it, a soft specular highlight, a drop shadow."""
    if ruler or only_ruler:
        for i in range(11):
            a = math.radians(135 + i * 27)
            c.ell(cx + math.cos(a) * (r + 10), cy + math.sin(a) * (r + 10), 1.7, 1.7, fill=INK)
            if numbers and i in (0, 5, 10):
                c.t((cx + math.cos(a) * (r + 21), cy + math.sin(a) * (r + 21)), str(i), 8, INK)
    if only_ruler:
        return
    c.shadow((cx - r, cy - r, cx + r, cy + r), r, 7, 7, 160)
    if big:
        c.ell(cx, cy, r, r, fill=(66, 70, 80), outline=(34, 36, 42), width=2)
        for i in range(64):   # knurled skirt
            a = math.radians(i * 5.625)
            c.line([(cx + math.cos(a) * (r - 4), cy + math.sin(a) * (r - 4)), (cx + math.cos(a) * (r - 1), cy + math.sin(a) * (r - 1))], (110, 114, 126), 1)
        cap = r - 7
        vgrad(c, (cx - cap, cy - cap, cx + cap, cy + cap), (186, 194, 208), (146, 154, 170), int(cap))   # a flat cap, lit from the top
        c.ell(cx, cy, cap, cap, outline=(70, 76, 90), width=1)
    else:
        c.ell(cx, cy, r, r, fill=BLACK, outline=(0, 0, 0), width=2)
        for i in range(44):
            a = math.radians(i * 8.2)
            c.line([(cx + math.cos(a) * (r - 5), cy + math.sin(a) * (r - 5)), (cx + math.cos(a) * (r - 1), cy + math.sin(a) * (r - 1))], (104, 104, 108), 1)
        c.ell(cx, cy, r - 8, r - 8, fill=body, outline=(10, 10, 12), width=1)
        c.ell(cx - 1, cy - 2, r - 14, r - 14, fill=(60, 60, 64))
        c.ell(cx - r * 0.2, cy - r * 0.3, r * 0.4, r * 0.25, fill=(255, 255, 255, 34))
    a = math.radians(135 + value * 270)
    c.line([(cx + math.cos(a) * (r * 0.30), cy + math.sin(a) * (r * 0.30)), (cx + math.cos(a) * (r - 6), cy + math.sin(a) * (r - 6))], pointer if not big else (28, 32, 44), 4)
    if name:
        c.t((cx, cy - r - 32), name, 10, INK)


def master(c, gain=0.5):
    """GAIN (a wide horizontal fader) and the stereo level meter: a compact printed section at the top right of every tab."""
    c.r((700, 6, 1240, 78), 4, fill=SILK)
    c.t((718, 42), "GAIN", 10, INK, "lm", "b")
    c.r((780, 38, 980, 46), 3, fill=(20, 20, 22), outline=(60, 60, 62), width=1)   # fader slot, ticks, cap
    for i in range(21):
        c.line([(782 + i * 9.5, 52), (782 + i * 9.5, 57 if i % 5 == 0 else 54)], INK, 1)
    cx = 780 + gain * 200
    c.shadow((cx - 8, 28, cx + 8, 56), 2, 2, 2, 140)
    vgrad(c, (cx - 8, 28, cx + 8, 56), (236, 236, 232), (170, 170, 166), 2)
    c.r((cx - 8, 28, cx + 8, 56), 2, outline=(60, 60, 58), width=1)
    c.line([(cx, 30), (cx, 54)], (40, 40, 40), 2)
    c.t((1016, 42), "LEVEL", 9, INK, "lm", "b")
    for row, lit_n in enumerate((6, 5)):
        c.t((1062, 30 + row * 22), "LR"[row], 9, INK)
        for i in range(10):
            col = (255, 60, 40) if i == 9 else ((255, 190, 40) if i >= 7 else (70, 230, 120))
            on = i < lit_n + (2 if i < 6 and row == 0 else 0)
            x, y = 1076 + i * 15, 30 + row * 22
            if on:
                glow(c, x, y, 7, col, 130)
            c.r((x - 6, y - 5, x + 6, y + 5), 2, fill=col if on else tuple(v // 4 for v in col), outline=(40, 40, 40), width=1)


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
    master(c)


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


def play():
    c = C()
    header(c, "PLAY")
    lcd(c, (40, 82, 1240, 440))
    lcd_head(c, 66, 112, 1212)
    c.d.rectangle([66 * S, 170 * S, 1214 * S, 172 * S], fill=LCD_DIM)
    rows = [("OPEN SESAME", "TREVOR NOVA", "4:12"), ("AMEN BREAK", "THE WINSTONS", "2:05"), ("ACID TRACKS", "PHUTURE", "6:55"), ("DEEP SPACE", "NOVA", "5:40"),
            ("MOVE YOUR BODY", "MARSHALL JEFFERSON", "3:30"), ("STRINGS OF LIFE", "RHYTHIM IS RHYTHIM", "5:12"), ("NO WAY BACK", "ADONIS", "4:49"), ("(UNTITLED)", "", "7:03")]
    for i, (t, a, d) in enumerate(rows):
        col, row = i // 4, i % 4
        x0, y0 = 66 + col * 590, 198 + row * 58
        playing = i == 1
        if playing:
            invbar(c, x0 - 6, y0 - 14, x0 + 566, y0 + 40)
        lt(c, (x0, y0 + 2), "%02d" % (i + 1), 18, inv=playing)
        lt(c, (x0 + 44, y0 + 2), t, 18, inv=playing)
        lt(c, (x0 + 556, y0 + 2), d, 15, inv=playing, anchor="rm")
        lt(c, (x0 + 44, y0 + 26), a, 12, inv=playing, dim=not playing)
    brushed(c, (40, 456, 640, 614))
    bracket(c, 60, 620, 474, "TRANSPORT")
    for i, (lab, lamp, lit) in enumerate([("◄◄", "red", False), ("▶ ❚❚", "green", True), ("■", "red", False), ("►►", "red", False)]):
        key(c, 120 + i * 140, 540, 110, 62, lab, "cream", lit=lit, lamp=lamp, size=20 if i != 1 else 18)
    for i, t in enumerate(["BACK 15 S", "PLAY / PAUSE", "STOP", "FORWARD 15 S"]):
        c.t((120 + i * 140, 584), t, 9, INK)
    brushed(c, (656, 456, 1240, 614))
    bracket(c, 676, 1220, 474, "RESULTS  /  SEARCH")
    for i, (lab, col, lit, lamp) in enumerate([("◄ PAGE", "cream", False, "red"), ("PAGE ►", "cream", False, "red"), ("SYNC", "cream", True, "amber"), ("SEARCH", "dark", False, "red")]):
        key(c, 730 + i * 135, 540, 108, 62, lab, col, lit=lit, lamp=lamp, size=14)
    c.t((730 + 2 * 135, 584), "WAIT FOR MPC PLAY", 8, INK)
    c.save("play.png")


def filters():
    c = C()
    header(c, "FILTERS")
    lcd(c, (40, 82, 1240, 400))
    lcd_head(c, 66, 112, 1212)
    c.d.rectangle([66 * S, 170 * S, 1214 * S, 172 * S], fill=LCD_DIM)
    vals = [("GENRE", "ELECTRONIC"), ("STYLE", "ACID HOUSE"), ("DECADE", "1990s"), ("REGION", "EUROPE"), ("COUNTRY", "GERMANY")]
    # like the results page: two columns of big entries, the selected one in inverse video, the label on the small line
    for i, (k, v) in enumerate(vals):
        col, row = i // 3, i % 3
        x0, y0 = 66 + col * 590, 198 + row * 62
        sel = i == 1
        if sel:
            invbar(c, x0 - 6, y0 - 15, x0 + 566, y0 + 44)
        lt(c, (x0, y0 + 4), "%02d" % (i + 1), 20, inv=sel)
        lt(c, (x0 + 52, y0 + 4), v, 26, inv=sel)
        lt(c, (x0 + 52, y0 + 32), k, 12, inv=sel, dim=not sel)
    lt(c, (66 + 590 + 52, 198 + 2 * 62 + 4), "STYLE FOLLOWS GENRE", 13, dim=True)
    lt(c, (66 + 590 + 52, 198 + 2 * 62 + 30), "COUNTRY FOLLOWS REGION", 13, dim=True)
    plate(c, (40, 414, 1240, 614), "DISCOGS FILTERS")
    for i, (k, v) in enumerate(vals):
        cx = 142 + i * 188
        knob(c, cx, 502, 36, [0.35, 0.5, 0.62, 0.3, 0.45][i], None, big=True, numbers=False)
        key(c, cx - 70, 502, 36, 28, "◄", size=12)
        key(c, cx + 70, 502, 36, 28, "►", size=12)
        c.t((cx, 502 + 56), k, 10, INK, "mm", "b")
    key(c, 1110, 520, 190, 62, "SEARCH", "dark", size=16)
    c.t((1110, 566), "SEARCH DISCOGS", 9, INK)
    c.save("filters.png")


def selector(c, cx, cy, name, value=0.0, r=22, gap=56):
    """A small selector: knob with its name under it and a ◄ ► key either side."""
    knob(c, cx, cy, r, value, None, big=True, numbers=False)
    key(c, cx - gap, cy, 36, 26, "◄", "cream", size=11)
    key(c, cx + gap, cy, 36, 26, "►", "cream", size=11)
    c.t((cx, cy + r + 20), name, 9, INK)


def find(keys=False):
    c = C()
    header(c, "FIND")
    lcd(c, (40, 82, 1240, 340))
    lcd_head(c, 66, 112, 1212, search="SEARCH YOUTUBE ..." if keys else "DONE - 12 RESULTS IN 3.1S")
    c.d.rectangle([66 * S, 170 * S, 1214 * S, 172 * S], fill=LCD_DIM)
    lt(c, (70, 198), "SOURCE", 13, dim=True); lt(c, (170, 198), "YOUTUBE", 15)
    lt(c, (520, 198), "CHANNEL", 13, dim=True); lt(c, (620, 198), "NONE - SEE CHANNELS.TXT", 15)
    lt(c, (70, 224), "LENGTH", 13, dim=True); lt(c, (170, 224), "ANY - ANY", 15)
    lt(c, (520, 224), "MUSIC ONLY", 13, dim=True); lt(c, (660, 224), "OFF", 15)
    lt(c, (70, 276), "TEXT", 13, dim=True)
    invbar(c, 160, 260, 1214, 294) if keys else None
    lt(c, (170, 277), "AMEN BREAK_" if keys else "TAP KEYS TO TYPE", 18, inv=keys, dim=not keys)
    brushed(c, (40, 354, 300, 540))
    bracket(c, 56, 284, 370, "DISCOGS")
    key(c, 170, 416, 160, 56, "DISCOGS", "blue", size=15)
    c.t((170, 472), "USES THE FILTERS TAB", 8, INK)
    brushed(c, (316, 354, 760, 540))
    bracket(c, 332, 744, 370, "CHANNEL")
    key(c, 538, 416, 160, 56, "CHANNEL", "blue", size=15)
    selector(c, 538, 494, "CHANNEL  (CHANNELS.TXT)", gap=76)
    brushed(c, (776, 354, 1240, 540))
    bracket(c, 792, 1224, 370, "YOUTUBE")
    key(c, 880, 416, 140, 56, "YOUTUBE", "blue", lit=True, size=15)
    key(c, 1060, 416, 140, 56, "MUSIC ONLY", "cream", size=13)
    selector(c, 870, 494, "MIN LENGTH", gap=52)
    selector(c, 1070, 494, "MAX LENGTH", gap=52)
    brushed(c, (40, 550, 1240, 616))
    bracket(c, 56, 1224, 566, "SEARCH")
    key(c, 150, 596, 160, 38, "KEYBOARD", "dark", size=13)
    key(c, 340, 596, 160, 38, "SEARCH", "dark", size=14)
    if keys:
        c.shadow((0, 346, W, H), 0, 8, -3, 170)
        c.d.rectangle([0, 346 * S, W * S, H * S], fill=SILK)
        c.t((44, 362), "KEYBOARD", 10, INK, "lm", "b")
        c.line([(130, 362), (1236, 362)], (120, 120, 116), 1)
        rows = ["1234567890", "QWERTYUIOP", "ASDFGHJKL", "ZXCVBNM"]
        for ri, row in enumerate(rows):
            x0 = 118 + [0, 0, 58, 174][ri]
            for k, ch in enumerate(row):
                key(c, x0 + k * 116, 378 + ri * 52 + 22, 100, 42, ch, "blue" if ri == 0 else "cream", size=18)
        for (cx, cy, w, txt, col) in [(130, 592, 200, "HIDE", "dark"), (520, 592, 520, "SPACE", "cream"), (880, 592, 190, "CLEAR", "dark"), (1130, 592, 220, "SEARCH", "dark"), (1180, 547, 150, "BACK", "dark")]:
            key(c, cx, cy, w, 40, txt, col, size=14)
    c.save("find_keys.png" if keys else "find.png")


if __name__ == "__main__":
    play(); filters(); find(False); find(True)
    print("wrote", os.path.normpath(OUT))
