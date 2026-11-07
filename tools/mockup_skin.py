#!/usr/bin/env python3
"""Mock-ups of a redrawn Crate Digger skin, v3 ("rack sampler"): a silver faceplate, a pale blue-green dot-matrix LCD, a row of function keys under
the screen, black knurled knobs and printed bracket labels, in the spirit of late-80s rack samplers (no maker's name or logo). The three tabs keep
the 1.x idea (PLAY, FILTERS, FIND) but the layout is loose. Pictures only, no TUI wiring:
    python3 tools/mockup_skin.py   ->  docs/skin-mockups/{play,filters,find,find_keys}.png"""
import math, os, random
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUT = os.path.join(ROOT, "docs", "skin-mockups")
FONT = next(f for f in (os.path.join(ROOT, "vst", "fonts", "Univers_53_Extended_Regular.otf"),
                        os.path.expanduser("~/mpc-vst-acid/vst/fonts/Univers_53_Extended_Regular.otf"),
                        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf") if os.path.exists(f))
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
S = 2
W, H = 1280, 628
SILVER, SILVER2, SILVER3 = (201, 201, 195), (186, 186, 180), (160, 160, 154)
BLACK, GRAPH, KEY, KEY_D = (24, 24, 26), (52, 52, 56), (226, 226, 220), (84, 84, 88)
LCD, LCD_INK, LCD_DIM, LCD_GRID = (178, 204, 192), (24, 42, 38), (112, 146, 132), (150, 178, 166)
INK, RED = (36, 36, 38), (190, 36, 30)


def font(size, kind="u"):
    return ImageFont.truetype({"u": FONT, "m": MONO, "s": SANS}[kind], int(size * S))


class C:
    def __init__(self):
        self.im = Image.new("RGB", (W * S, H * S), SILVER)
        self.d = ImageDraw.Draw(self.im, "RGBA")
        random.seed(7)
        for y in range(0, H * S, 3):   # brushed metal
            v = random.randint(-9, 9)
            self.d.line([(0, y), (W * S, y)], fill=(255 if v > 0 else 0,) * 3 + (abs(v),), width=1)

    def r(self, box, rad=8, fill=None, outline=None, width=1):
        self.d.rounded_rectangle([c * S for c in box], radius=rad * S, fill=fill, outline=outline, width=int(width * S))

    def t(self, xy, text, size=14, fill=INK, anchor="mm", kind="u"):
        if any(ord(ch) > 127 for ch in text): kind = "s"
        self.d.text((xy[0] * S, xy[1] * S), text, font=font(size, kind), fill=fill, anchor=anchor)

    def ell(self, cx, cy, rx, ry, fill=None, outline=None, width=1):
        self.d.ellipse([(cx - rx) * S, (cy - ry) * S, (cx + rx) * S, (cy + ry) * S], fill=fill, outline=outline, width=int(width * S))

    def line(self, pts, fill, width=1):
        self.d.line([(x * S, y * S) for x, y in pts], fill=fill, width=int(width * S))

    def shadow(self, box, rad=8, blur=5, off=3, alpha=100):
        lay = Image.new("RGBA", self.im.size, (0, 0, 0, 0))
        ImageDraw.Draw(lay).rounded_rectangle([box[0] * S, (box[1] + off) * S, box[2] * S, (box[3] + off) * S], radius=rad * S, fill=(0, 0, 0, alpha))
        lay = lay.filter(ImageFilter.GaussianBlur(blur * S))
        self.im.paste(lay, (0, 0), lay)
        self.d = ImageDraw.Draw(self.im, "RGBA")

    def save(self, name):
        os.makedirs(OUT, exist_ok=True)
        self.im.resize((W, H), Image.LANCZOS).save(os.path.join(OUT, name))


def lcd(c, box, grid=True):
    """A recessed black bezel around a pale blue-green dot-matrix screen."""
    x0, y0, x1, y1 = box
    c.shadow(box, 8, 4, 2, 120)
    c.r(box, 8, fill=BLACK, outline=(70, 70, 72), width=2)
    c.r((x0 + 8, y0 + 8, x1 - 8, y1 - 8), 3, fill=LCD)
    if grid:
        for x in range(int(x0 + 8), int(x1 - 8), 3):
            c.d.line([(x * S, (y0 + 8) * S), (x * S, (y1 - 8) * S)], fill=LCD_GRID + (50,), width=1)
        for y in range(int(y0 + 8), int(y1 - 8), 3):
            c.d.line([((x0 + 8) * S, y * S), ((x1 - 8) * S, y * S)], fill=LCD_GRID + (50,), width=1)


def lt(c, xy, text, size=16, inv=False, anchor="lm", dim=False):
    c.t(xy, text, size, LCD if inv else (LCD_DIM if dim else LCD_INK), anchor, "m")


def bar(c, x0, y0, x1, y1):
    c.d.rectangle([x0 * S, y0 * S, x1 * S, y1 * S], fill=LCD_INK)


def label(c, x0, x1, y, text):
    """A printed bracket label: ruler line, centred text, short end ticks (the 'SCREEN FUNCTION' idiom)."""
    mid = (x0 + x1) / 2
    tw = len(text) * 9.5 + 18
    c.line([(x0, y), (mid - tw / 2, y)], INK + (200,), 1)
    c.line([(mid + tw / 2, y), (x1, y)], INK + (200,), 1)
    c.line([(x0, y), (x0, y + 7)], INK + (200,), 1)
    c.line([(x1, y), (x1, y + 7)], INK + (200,), 1)
    c.t((mid, y), text, 12, INK)


def fkey(c, cx, cy, w, h, text, fnum=None, lit=False, red=False, dark=False, size=14):
    """A flat plastic key with its legend printed on it; an F-number above, an LED when lit."""
    c.shadow((cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), 5, 3, 3, 110)
    base = (150, 34, 28) if red else (KEY_D if dark else KEY)
    c.r((cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), 5, fill=base, outline=(70, 70, 66), width=2)
    c.r((cx - w / 2 + 3, cy - h / 2 + 3, cx + w / 2 - 3, cy - h / 2 + h * 0.4), 3, fill=(255, 255, 255, 70))
    c.t((cx, cy + 1), text, size, (240, 236, 230) if (red or dark) else INK)
    if fnum:
        c.t((cx, cy - h / 2 - 11), "F%d" % fnum, 10, INK)
    if lit:
        c.ell(cx + w / 2 - 11, cy - h / 2 + 10, 4, 4, fill=RED, outline=(90, 10, 8))


def knob(c, cx, cy, r, value, name, cap=False):
    """A black knurled knob with a white pointer, a printed ruler of ticks and its name above."""
    for i in range(21):
        a = math.radians(135 + i * 270 / 20)
        l = 11 if i % 5 == 0 else 7
        c.line([(cx + math.cos(a) * (r + 8), cy + math.sin(a) * (r + 8)), (cx + math.cos(a) * (r + 8 + l), cy + math.sin(a) * (r + 8 + l))], INK, 2 if i % 5 == 0 else 1)
    c.shadow((cx - r, cy - r, cx + r, cy + r), r, 7, 7, 140)
    c.ell(cx, cy, r, r, fill=BLACK, outline=(8, 8, 8), width=2)
    for i in range(48):   # knurled edge
        a = math.radians(i * 7.5)
        c.line([(cx + math.cos(a) * (r - 6), cy + math.sin(a) * (r - 6)), (cx + math.cos(a) * (r - 1), cy + math.sin(a) * (r - 1))], (90, 90, 94), 1)
    c.ell(cx, cy, r - 9, r - 9, fill=(40, 40, 44), outline=(14, 14, 16), width=1)
    c.ell(cx - 2, cy - 3, r - 17, r - 17, fill=(52, 52, 56))
    a = math.radians(135 + value * 270)
    c.line([(cx + math.cos(a) * 6, cy + math.sin(a) * 6), (cx + math.cos(a) * (r - 9), cy + math.sin(a) * (r - 9))], (240, 240, 236), 4)
    c.t((cx, cy - r - 32), name, 15, INK)


def window(c, cx, cy, w, h, value, size=16, caption=None, arrows=True):
    """A small LCD window; ◄ ► keys either side."""
    if caption:
        c.t((cx, cy - h / 2 - 14), caption, 12, INK)
    lcd(c, (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), grid=False)
    lt(c, (cx, cy), value, size, anchor="mm")
    if arrows:
        for sgn, ch in ((-1, "◄"), (1, "►")):
            fkey(c, cx + sgn * (w / 2 + 28), cy, 40, h - 4, ch, size=13)


def top(c, now="OPEN SESAME - TREVOR NOVA", status="STREAMING", time="0:42", search="DONE - 12 RESULTS IN 3.1S", gain=0.5):
    """The same on every page: the wordmark, the LCD with the readouts, the gain knob."""
    c.t((40, 44), "CRATE DIGGER", 27, INK, "lm")
    c.line([(40, 66), (300, 66)], INK, 2)
    c.t((40, 84), "STEREO DIGITAL RECORD SAMPLER", 10, INK, "lm")
    c.t((40, 102), "S H A R E D   R O O M   M O D E L", 9, INK, "lm") if False else None
    lcd(c, (330, 10, 1010, 130))
    for i, (k, v) in enumerate([("NOW", now), ("STATUS", status), ("TIME", time), ("SEARCH", search)]):
        lt(c, (354, 34 + i * 25), k, 12, dim=True)
        lt(c, (440, 34 + i * 25), v, 17)
    knob(c, 1150, 82, 36, gain, "", cap=True)
    c.t((1150, 22), "GAIN", 13, INK)
    c.line([(1090, 130), (1210, 130)], INK + (0,), 1)


def play():
    c = C()
    top(c)
    label(c, 40, 1240, 160, "SCREEN FUNCTION")
    keys = [("◄◄ 15", False, False), ("▶ ❚❚", False, False), ("■", False, False), ("15 ►►", False, False), ("SYNC", True, False), ("◄ PAGE", False, False), ("PAGE ►", False, False), ("SEARCH", False, True)]
    for i, (t, lit, red) in enumerate(keys):
        fkey(c, 108 + i * 152, 215, 128, 52, t, i + 1, lit=lit, red=red)
    # the big LCD: header line + results as an LCD list, the playing row in inverse video
    lcd(c, (40, 262, 1240, 616))
    bar(c, 58, 276, 1222, 304)
    lt(c, (70, 290), "RESULTS", 17, inv=True)
    lt(c, (700, 290), "PAGE 1 / 2     12 FOUND     SYNC ON", 15, inv=True, anchor="mm")
    rows = [("OPEN SESAME", "TREVOR NOVA", "1996", "4:12"), ("AMEN BREAK", "THE WINSTONS", "1969", "2:05"), ("ACID TRACKS", "PHUTURE", "1987", "6:55"), ("DEEP SPACE", "NOVA", "1994", "5:40"),
            ("MOVE YOUR BODY", "MARSHALL JEFFERSON", "1986", "3:30"), ("STRINGS OF LIFE", "RHYTHIM IS RHYTHIM", "1987", "5:12"), ("NO WAY BACK", "ADONIS", "1986", "4:49"), ("(UNTITLED)", "", "1991", "7:03")]
    for i, (t, a, y, d) in enumerate(rows):
        col, row = i // 4, i % 4
        x0, y0 = 62 + col * 590, 316 + row * 72
        playing = i == 1
        if playing:
            bar(c, x0 - 4, y0 - 2, x0 + 566, y0 + 62)
        lt(c, (x0 + 6, y0 + 16), "%02d" % (i + 1), 20, inv=playing)
        lt(c, (x0 + 52, y0 + 16), t, 20, inv=playing)
        lt(c, (x0 + 52, y0 + 44), a, 14, inv=playing, dim=not playing)
        lt(c, (x0 + 556, y0 + 16), d, 16, inv=playing, anchor="rm")
        lt(c, (x0 + 556, y0 + 44), y, 14, inv=playing, anchor="rm", dim=not playing)
    c.save("play.png")


def filters():
    c = C()
    top(c)
    label(c, 40, 1240, 160, "DISCOGS FILTERS")
    names = [("GENRE", "ELECTRONIC", .35), ("STYLE", "ACID HOUSE", .5), ("DECADE", "1990s", .62), ("REGION", "EUROPE", .3), ("COUNTRY", "GERMANY", .45)]
    for i, (n, v, val) in enumerate(names):
        cx = 140 + i * 250
        knob(c, cx, 290, 44, val, n)
        window(c, cx, 392, 124, 40, v, 15)
    c.t((640, 452), "STYLE FOLLOWS GENRE  -  COUNTRY FOLLOWS REGION", 11, INK)
    label(c, 40, 1240, 490, "SCREEN FUNCTION")
    fkey(c, 150, 556, 220, 56, "SEARCH DISCOGS", 1, red=True)
    lcd(c, (330, 526, 1240, 590))
    lt(c, (354, 548), "STATUS", 12, dim=True)
    lt(c, (354, 570), "DONE - 12 RESULTS IN 3.1S", 18)
    c.save("filters.png")


def find(keys=False):
    c = C()
    top(c, search="SEARCH YOUTUBE ..." if keys else "DONE - 12 RESULTS IN 3.1S")
    label(c, 40, 1240, 160, "SOURCE")
    for i, n in enumerate(["DISCOGS", "CHANNEL", "YOUTUBE"]):
        fkey(c, 112 + i * 168, 212, 144, 52, n, i + 1, lit=(i == 2))
    window(c, 810, 212, 380, 44, "NONE - SEE CHANNELS.TXT", 15, caption="CHANNEL")
    fkey(c, 1180, 212, 150, 52, "MUSIC ONLY", 5)
    window(c, 250, 308, 220, 40, "ANY", 16, caption="MIN LENGTH")
    window(c, 640, 308, 220, 40, "ANY", 16, caption="MAX LENGTH")
    label(c, 40, 1240, 366, "SEARCH TEXT")
    lcd(c, (40, 380, 1240, 438))
    lt(c, (66, 409), "AMEN BREAK_" if keys else "TAP KEYS TO TYPE", 24, dim=not keys)
    fkey(c, 112, 520, 144, 52, "KEYS", 6)
    fkey(c, 280, 520, 144, 52, "SEARCH", 7, red=True)
    lcd(c, (400, 492, 1240, 548))
    lt(c, (424, 520), "DONE - 12 RESULTS IN 3.1S", 17)
    if keys:   # the keypad, drawn over the lower half
        c.shadow((0, 330, W, H), 0, 8, -3, 170)
        c.r((0, 330, W, H), 0, fill=(44, 44, 48))
        c.line([(0, 330), (W, 330)], (120, 120, 124), 2)
        rows = ["1234567890", "QWERTYUIOP", "ASDFGHJKL", "ZXCVBNM"]
        for ri, row in enumerate(rows):
            x0 = 118 + [0, 0, 58, 174][ri]
            for k, ch in enumerate(row):
                kx, ky = x0 + k * 116, 344 + ri * 54
                c.shadow((kx - 52, ky, kx + 52, ky + 46), 5, 3, 2, 120)
                c.r((kx - 52, ky, kx + 52, ky + 46), 5, fill=KEY, outline=(70, 70, 66), width=2)
                c.t((kx, ky + 24), ch, 20, INK)
        for (cx, cy, w, txt, red) in [(130, 586, 200, "HIDE", False), (520, 586, 520, "SPACE", False), (880, 586, 190, "CLEAR", False), (1130, 586, 220, "SEND", True), (1180, 529, 150, "BACK", False)]:
            c.shadow((cx - w / 2, cy - 24, cx + w / 2, cy + 24), 5, 3, 2, 120)
            c.r((cx - w / 2, cy - 24, cx + w / 2, cy + 24), 5, fill=(150, 34, 28) if red else KEY, outline=(70, 70, 66), width=2)
            c.t((cx, cy), txt, 18, (240, 236, 230) if red else INK)
    c.save("find_keys.png" if keys else "find.png")


if __name__ == "__main__":
    play(); filters(); find(False); find(True)
    print("wrote", os.path.normpath(OUT))
