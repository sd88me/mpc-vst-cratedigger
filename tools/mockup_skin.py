#!/usr/bin/env python3
"""Mock-ups of a redrawn Crate Digger skin, v2 ("record shop"): the SAME three tabs and positions as the 1.x skin (PLAY, FILTERS, FIND; vst/layout.conf
y minus 86), only the look changes. Cream paper-label plates, vinyl-disc arrows, sleeve-card results with a record peeking out of the playing one.
Pictures only, no TUI wiring:   python3 tools/mockup_skin.py   ->  docs/skin-mockups/{play,filters,find,find_keys}.png"""
import math, os, random
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUT = os.path.join(ROOT, "docs", "skin-mockups")
FONT = next(f for f in (os.path.join(ROOT, "vst", "fonts", "Univers_53_Extended_Regular.otf"),
                        os.path.expanduser("~/mpc-vst-acid/vst/fonts/Univers_53_Extended_Regular.otf"),
                        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf") if os.path.exists(f))
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
S = 2
W, H = 1280, 628
BG, BG2, PANEL, PANEL_LINE = (38, 33, 28), (30, 26, 22), (47, 41, 35), (86, 76, 64)
CREAM, CREAM2, INK, INK2 = (238, 228, 204), (220, 208, 180), (44, 38, 32), (110, 98, 82)
AMBER, AMBER_D, DIM = (240, 160, 40), (110, 72, 16), (150, 140, 120)
VINYL, VINYL2 = (22, 22, 24), (40, 40, 44)


def font(size, kind="u"):
    return ImageFont.truetype({"u": FONT, "m": MONO, "s": SANS, "k": SERIF}[kind], int(size * S))


class C:
    def __init__(self):
        self.im = Image.new("RGB", (W * S, H * S), BG)
        self.d = ImageDraw.Draw(self.im, "RGBA")
        random.seed(5)
        for y in range(0, H * S, 6):   # faint wood grain
            v = random.randint(-5, 5)
            self.d.line([(0, y), (W * S, y + random.randint(-3, 3))], fill=(255 if v > 0 else 0,) * 3 + (abs(v) + 2,), width=2)

    def r(self, box, rad=8, fill=None, outline=None, width=1):
        self.d.rounded_rectangle([c * S for c in box], radius=rad * S, fill=fill, outline=outline, width=int(width * S))

    def t(self, xy, text, size=14, fill=CREAM, anchor="mm", kind="u"):
        if any(ord(ch) > 127 for ch in text): kind = "s"
        self.d.text((xy[0] * S, xy[1] * S), text, font=font(size, kind), fill=fill, anchor=anchor)

    def ell(self, cx, cy, rx, ry, fill=None, outline=None, width=1):
        self.d.ellipse([(cx - rx) * S, (cy - ry) * S, (cx + rx) * S, (cy + ry) * S], fill=fill, outline=outline, width=int(width * S))

    def line(self, pts, fill, width=1):
        self.d.line([(x * S, y * S) for x, y in pts], fill=fill, width=int(width * S))

    def shadow(self, box, rad=8, blur=5, off=3, alpha=110):
        lay = Image.new("RGBA", self.im.size, (0, 0, 0, 0))
        ImageDraw.Draw(lay).rounded_rectangle([box[0] * S, (box[1] + off) * S, box[2] * S, (box[3] + off) * S], radius=rad * S, fill=(0, 0, 0, alpha))
        lay = lay.filter(ImageFilter.GaussianBlur(blur * S))
        self.im.paste(lay, (0, 0), lay)
        self.d = ImageDraw.Draw(self.im, "RGBA")

    def save(self, name):
        os.makedirs(OUT, exist_ok=True)
        self.im.resize((W, H), Image.LANCZOS).save(os.path.join(OUT, name))


def frame(c, x0, y0, x1, y1, title):
    c.r((x0, y0, x1, y1), 12, fill=PANEL, outline=PANEL_LINE, width=2)
    c.t((x0 + 20, y0 + 16), title, 13, AMBER, "lm")
    c.line([(x0 + 24 + len(title) * 10.5, y0 + 16), (x1 - 20, y0 + 16)], PANEL_LINE, 1)


def disc(c, cx, cy, r, spin=0.0, label=AMBER):
    """A little vinyl record: black disc, groove rings, a coloured label, the spindle hole."""
    c.ell(cx, cy, r, r, fill=VINYL, outline=(70, 70, 74), width=1)
    for k in range(3, 6):
        c.ell(cx, cy, r * (0.5 + k * 0.1), r * (0.5 + k * 0.1), outline=VINYL2, width=1)
    c.ell(cx, cy, r * 0.36, r * 0.36, fill=label)
    c.ell(cx, cy, r * 0.07, r * 0.07, fill=VINYL)
    a = math.radians(-50 + spin)
    c.line([(cx + math.cos(a) * r * 0.38, cy + math.sin(a) * r * 0.38), (cx + math.cos(a) * r * 0.9, cy + math.sin(a) * r * 0.9)], (200, 200, 205, 90), 2)


def plate(c, cx, cy, w, h, text, label=None, size=17, dim=False):
    """A paper-label value plate: dark ink on cream, with the small caption above it."""
    if label:
        c.t((cx, cy - h / 2 - 13), label, 12, DIM)
    c.shadow((cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), 5, 3, 2, 120)
    c.r((cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), 5, fill=CREAM2 if dim else CREAM, outline=(150, 140, 118), width=1)
    c.line([(cx - w / 2 + 8, cy + h / 2 - 5), (cx + w / 2 - 8, cy + h / 2 - 5)], (190, 178, 150), 1)
    c.t((cx, cy - 1), text, size, INK2 if dim else INK, "mm", "k")


def stepper(c, cx, cy, w, h, label, value, size=20):
    """Two vinyl-disc arrows either side of a label plate."""
    plate(c, cx, cy, w - 2 * (h + 14), h, value, None, size)
    c.t((cx - w / 2 + 6, cy - h / 2 - 14), label, 12, DIM, "lm")
    for sgn in (-1, 1):
        x = cx + sgn * (w / 2 - h / 2)
        disc(c, x, cy, h / 2)
        c.d.polygon([((x + 7 * sgn) * S, cy * S), ((x - 5 * sgn) * S, (cy - 10) * S), ((x - 5 * sgn) * S, (cy + 10) * S)], fill=CREAM)


def key(c, cx, cy, w, h, text, lit=False, accent=False, legend=None, textsize=15):
    """A flat deck key: ivory, rounded, an amber lamp when lit; the accent one is amber."""
    c.shadow((cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), 8, 4, 3, 130)
    base = AMBER if accent else (CREAM if not lit else (255, 214, 130))
    c.r((cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), 8, fill=base, outline=(120, 100, 60), width=2)
    c.r((cx - w / 2 + 3, cy - h / 2 + 3, cx + w / 2 - 3, cy - 1), 6, fill=(255, 255, 255, 60))
    c.t((cx, cy + 1), text, textsize, INK, "mm")
    if lit:
        c.ell(cx + w / 2 - 12, cy - h / 2 + 11, 4, 4, fill=(255, 120, 40))
    if legend:
        c.t((cx, cy + h / 2 + 14), legend, 11, DIM)


def screen(c, cx, cy, w, h, label, value, size=17):
    """A small amber read-out window."""
    c.t((cx - w / 2 + 4, cy - h / 2 - 12), label, 12, DIM, "lm")
    c.r((cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), 6, fill=(18, 12, 4), outline=(90, 78, 56), width=2)
    c.t((cx - w / 2 + 14, cy), value, size, AMBER, "lm", "m")


def play():
    c = C()
    frame(c, 40, 4, 1240, 222, "TRANSPORT")
    for i, (txt, leg) in enumerate([("◄◄", "BACK 15 S"), ("▶", "PLAY / PAUSE"), ("►►", "FORWARD 15 S"), ("■", "STOP")]):
        key(c, 150 + i * 130, 83, 90, 56, txt, accent=(i == 1), legend=leg)
    key(c, 700, 83, 150, 56, "SYNC", lit=True, legend="WAIT FOR MPC PLAY")
    screen(c, 1000, 83, 170, 40, "STATUS", "STREAMING")
    screen(c, 471, 170, 822, 40, "NOW PLAYING", "OPEN SESAME - TREVOR NOVA", 18)
    screen(c, 994, 170, 130, 40, "TIME", "0:42", 18)
    c.r((1150, 28, 1176, 168), 8, fill=(14, 12, 10), outline=PANEL_LINE, width=2)   # gain fader
    c.r((1134, 78, 1192, 104), 6, fill=CREAM, outline=(120, 100, 60), width=2)
    c.t((1163, 186), "GAIN", 12, DIM)
    frame(c, 40, 232, 1240, 376, "RESULTS")
    stepper(c, 322, 325, 520, 52, "RESULTS PAGE", "PAGE 1 / 2", 19)
    screen(c, 817, 325, 410, 40, "SEARCH", "DONE - 12 RESULTS IN 3.1S", 15)
    key(c, 1120, 325, 190, 52, "SEARCH", accent=True)
    frame(c, 40, 386, 1240, 624, "")
    titles = ["OPEN SESAME - TREVOR NOVA  1996  4:12", "AMEN BREAK - THE WINSTONS  1969  2:05", "ACID TRACKS - PHUTURE  1987  6:55", "DEEP SPACE - NOVA  1994  5:40",
              "MOVE YOUR BODY - MARSHALL  1986  3:30", "STRINGS OF LIFE - RHYTHIM  1987  5:12", "NO WAY BACK - ADONIS  1986  4:49", "(UNTITLED)  1991  7:03"]
    for i, t in enumerate(titles):
        col, row = i // 4, i % 4
        x0, y0 = 64 + col * 580, 408 + row * 52
        playing = i == 1
        if playing:
            disc(c, x0 + 618, y0 + 22, 21, 30)   # the record sliding out of its sleeve
        c.shadow((x0, y0, x0 + 560, y0 + 44), 5, 3, 2, 110)
        c.r((x0, y0, x0 + 560, y0 + 44), 5, fill=CREAM if not playing else (255, 232, 170), outline=(150, 140, 118), width=1)
        c.r((x0, y0, x0 + 12, y0 + 44), 4, fill=[(190, 80, 50), (60, 120, 130), (200, 160, 50), (110, 90, 150)][i % 4])   # the spine
        name, *rest = t.split("  ")
        c.t((x0 + 26, y0 + 22), "%02d" % (i + 1), 18, INK2, "lm", "k")
        c.t((x0 + 66, y0 + 22), name[:34], 15, INK, "lm", "k")
        c.t((x0 + (420 if not playing else 400), y0 + 22), "  ".join(rest), 13, INK2, "lm", "k")
    c.save("play.png")


def filters():
    c = C()
    frame(c, 40, 4, 1242, 540, "DISCOGS FILTERS")
    for i, (lab, val) in enumerate([("GENRE", "ELECTRONIC"), ("STYLE (DEPENDS ON GENRE)", "ACID HOUSE"), ("DECADE", "1990s"), ("REGION", "EUROPE"), ("COUNTRY (DEPENDS ON REGION)", "GERMANY")]):
        stepper(c, 640, 97 + i * 100, 1000, 64, lab, val, 24)
    key(c, 282, 590, 290, 52, "SEARCH DISCOGS", accent=True)
    screen(c, 820, 590, 748, 40, "STATUS", "DONE - 12 RESULTS IN 3.1S", 16)
    c.save("filters.png")


def find(keys=False):
    c = C()
    frame(c, 40, 4, 1240, 334, "FIND")
    for i, (name, leg) in enumerate([("DISCOGS", "ONLINE DIG"), ("CHANNEL", "FROM CHANNELS.TXT"), ("YOUTUBE", "ANY VIDEO")]):
        key(c, 152 + i * 196, 90, 170, 54, name, lit=(i == 2))
    stepper(c, 936, 90, 560, 56, "CHANNEL (FROM CHANNELS.TXT)", "NONE - SEE CHANNELS.TXT", 17)
    stepper(c, 244, 166, 360, 48, "MIN LENGTH (YOUTUBE)", "ANY", 18)
    stepper(c, 640, 166, 360, 48, "MAX LENGTH (YOUTUBE)", "ANY", 18)
    key(c, 1126, 166, 150, 48, "MUSIC ONLY")
    screen(c, 640, 240, 1152, 44, "SEARCH TEXT", "AMEN BREAK_" if keys else "TAP KEYS TO TYPE", 22)
    key(c, 112, 305, 130, 46, "KEYS")
    key(c, 262, 305, 130, 46, "SEARCH", accent=True)
    screen(c, 786, 308, 860, 34, "STATUS", "DONE - 12 RESULTS IN 3.1S", 15)
    if keys:
        c.shadow((0, 338, W, H), 0, 8, -3, 160)
        c.r((0, 338, W, H), 0, fill=BG2)
        rows = ["1234567890", "QWERTYUIOP", "ASDFGHJKL", "ZXCVBNM"]
        for ri, row in enumerate(rows):
            x0 = 118 + [0, 0, 58, 174][ri]
            for k, ch in enumerate(row):
                kx, ky = x0 + k * 116, 346 + ri * 54
                c.shadow((kx - 52, ky, kx + 52, ky + 46), 6, 3, 2, 110)
                c.r((kx - 52, ky, kx + 52, ky + 46), 6, fill=CREAM, outline=(150, 140, 118), width=1)
                c.t((kx, ky + 24), ch, 20, INK, "mm", "k")
        for (cx, cy, w, txt, acc) in [(130, 586, 200, "HIDE", False), (520, 586, 520, "SPACE", False), (880, 586, 190, "CLEAR", False), (1130, 586, 220, "SEND", True), (1180, 531, 150, "BACK", False)]:
            c.shadow((cx - w / 2, cy - 24, cx + w / 2, cy + 24), 6, 3, 2, 110)
            c.r((cx - w / 2, cy - 24, cx + w / 2, cy + 24), 6, fill=AMBER if acc else CREAM2, outline=(150, 140, 118), width=1)
            c.t((cx, cy), txt, 18, INK)
    c.save("find_keys.png" if keys else "find.png")


if __name__ == "__main__":
    play(); filters(); find(False); find(True)
    print("wrote", os.path.normpath(OUT))
