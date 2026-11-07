#!/usr/bin/env python3
"""Mock-ups of a redrawn Crate Digger skin (sampler-front-panel look), 1280 x 628 content area. Pictures only, no TUI wiring:
    python3 tools/mockup_skin.py   ->  docs/skin-mockups/{dig,find,find_keys,play}.png"""
import math, os, random
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUT = os.path.join(ROOT, "docs", "skin-mockups")
FONT = next((f for f in (os.path.join(ROOT, "vst", "fonts", "Univers_53_Extended_Regular.otf"),
                         os.path.expanduser("~/mpc-vst-acid/vst/fonts/Univers_53_Extended_Regular.otf"),
                         "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf") if os.path.exists(f)))
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
S = 2                                  # supersampling
W, H = 1280, 628
BODY, BODY2, GRAPH, GRAPH2 = (207, 203, 192), (190, 186, 175), (42, 42, 44), (24, 24, 26)
AMBER, AMBER_D, INK, INK_D = (245, 166, 35), (120, 78, 14), (46, 44, 40), (112, 108, 98)
RED, BLUE, GREEN, ORANGE, WHITE = (216, 48, 36), (46, 134, 222), (60, 200, 110), (240, 120, 30), (238, 236, 228)


def font(size, kind="u"):
    p = {"u": FONT, "m": MONO, "s": SANS}[kind]
    return ImageFont.truetype(p, int(size * S))


class Canvas:
    def __init__(self):
        self.im = Image.new("RGB", (W * S, H * S), BODY)
        self.d = ImageDraw.Draw(self.im, "RGBA")
        random.seed(3)
        for _ in range(9000):   # fine grain, like the painted plastic
            x, y = random.randrange(W * S), random.randrange(H * S)
            v = random.randint(-7, 7)
            self.d.point((x, y), fill=(255 if v > 0 else 0,) * 3 + (abs(v) * 2,))

    def r(self, box, rad=8, fill=None, outline=None, width=1):
        self.d.rounded_rectangle([c * S for c in box], radius=rad * S, fill=fill, outline=outline, width=width * S)

    def t(self, xy, text, size=14, fill=INK, anchor="mm", kind="u"):
        if any(ord(ch) > 127 for ch in text): kind = "s"   # arrows and transport symbols
        self.d.text((xy[0] * S, xy[1] * S), text, font=font(size, kind), fill=fill, anchor=anchor)

    def line(self, pts, fill, width=1):
        self.d.line([(x * S, y * S) for x, y in pts], fill=fill, width=int(width * S))

    def ell(self, cx, cy, rx, ry, fill=None, outline=None, width=1):
        self.d.ellipse([(cx - rx) * S, (cy - ry) * S, (cx + rx) * S, (cy + ry) * S], fill=fill, outline=outline, width=int(width * S))

    def shadow(self, box, rad=8, blur=6, off=3, alpha=90):
        lay = Image.new("RGBA", self.im.size, (0, 0, 0, 0))
        ImageDraw.Draw(lay).rounded_rectangle([box[0] * S, (box[1] + off) * S, box[2] * S, (box[3] + off) * S], radius=rad * S, fill=(0, 0, 0, alpha))
        lay = lay.filter(ImageFilter.GaussianBlur(blur * S))
        self.im.paste(lay, (0, 0), lay)
        self.d = ImageDraw.Draw(self.im, "RGBA")

    def save(self, name):
        os.makedirs(OUT, exist_ok=True)
        self.im.resize((W, H), Image.LANCZOS).save(os.path.join(OUT, name))


def header(c, page, now="OPEN SESAME - TREVOR NOVA", status="STREAMING", time="0:42", search="DONE - 12 RESULTS IN 3.1S"):
    """The black top panel, the same on every page: wordmark, the amber screen, the gain LEDs."""
    c.r((0, 0, W, 150), 0, fill=GRAPH)
    c.d.rectangle([0, 150 * S, W * S, 154 * S], fill=GRAPH2)
    c.t((40, 52), "CRATE", 40, RED, "lm")
    c.t((40, 98), "DIGGER", 40, RED, "lm")
    c.t((42, 130), "RECORD  DIG  SAMPLER", 11, (150, 146, 138), "lm")
    c.shadow((350, 14, 1030, 138), 10, 4, 2, 120)
    c.r((350, 14, 1030, 138), 10, fill=(14, 12, 8), outline=(70, 66, 58), width=2)
    c.r((358, 22, 1022, 130), 6, fill=(26, 18, 6))
    for i, (lab, val) in enumerate([("NOW", now), ("STATUS", status), ("TIME", time), ("SEARCH", search)]):
        y = 44 + i * 26
        c.t((374, y), lab, 12, AMBER_D, "lm", "m")
        c.t((470, y), val, 17, AMBER, "lm", "m")
    c.t((1000, 44), page, 13, AMBER_D, "rm", "m")
    c.t((1000, 70 + 26), "", 12)
    # gain LEDs and label
    for i in range(6):
        col = [RED, ORANGE, GREEN, GREEN, GREEN, GREEN][i]
        on = i >= 2
        for k, x in enumerate((1150, 1180)):
            y = 30 + i * 18
            c.r((x, y, x + 20, y + 11), 3, fill=col if on else tuple(v // 4 for v in col))
    c.t((1215, 90), "GAIN", 11, (150, 146, 138), "lm")
    c.t((1215, 110), "1.00", 14, AMBER, "lm", "m")


def knob(c, cx, cy, r, value, label, win, legend=None):
    """A ringed selector knob with a tick arc, the name above, the amber value window and the arrows below."""
    c.shadow((cx - r, cy - r, cx + r, cy + r), r, 7, 6, 110)
    for i in range(41):
        a = math.radians(135 + i * 270 / 40)
        x0, y0 = cx + math.cos(a) * (r + 7), cy + math.sin(a) * (r + 7)
        x1, y1 = cx + math.cos(a) * (r + (14 if i % 5 == 0 else 10)), cy + math.sin(a) * (r + (14 if i % 5 == 0 else 10))
        c.line([(x0, y0), (x1, y1)], INK_D if i / 40 > value else RED, 2)
    c.ell(cx, cy, r, r, fill=(52, 52, 54), outline=(20, 20, 22), width=2)
    c.ell(cx, cy, r - 7, r - 7, fill=(204, 202, 196))
    c.ell(cx - 3, cy - 4, r - 14, r - 14, fill=(224, 222, 216))
    a = math.radians(135 + value * 270)
    c.line([(cx + math.cos(a) * 8, cy + math.sin(a) * 8), (cx + math.cos(a) * (r - 11), cy + math.sin(a) * (r - 11))], INK, 4)
    c.t((cx, cy - r - 28), label, 15, INK)
    wx = 78
    c.r((cx - wx, cy + r + 20, cx + wx, cy + r + 54), 5, fill=(26, 18, 6), outline=(70, 66, 58), width=2)
    c.t((cx, cy + r + 37), win, 15, AMBER, "mm", "m")
    for sgn in (-1, 1):
        x = cx + sgn * (wx + 22)
        c.d.polygon([((x + 7 * sgn) * S, (cy + r + 37) * S), ((x - 7 * sgn) * S, (cy + r + 26) * S), ((x - 7 * sgn) * S, (cy + r + 48) * S)], fill=INK)


def button(c, cx, cy, w, h, text, col, legend=None, lit=False, textcol=WHITE):
    c.shadow((cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), 7, 4, 3, 100)
    c.r((cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), 7, fill=col, outline=tuple(max(0, v - 60) for v in col), width=2)
    c.r((cx - w / 2 + 3, cy - h / 2 + 3, cx + w / 2 - 3, cy - 2), 5, fill=tuple(min(255, v + 28) for v in col) + (110,))
    c.t((cx, cy + 1), text, 15, textcol)
    if lit:
        c.ell(cx + w / 2 - 12, cy - h / 2 + 12, 5, 5, fill=GREEN)
    if legend:
        c.t((cx, cy + h / 2 + 15), legend, 11, INK_D)


def window(c, cx, cy, w, label, value, h=34):
    c.t((cx, cy - h / 2 - 15), label, 12, INK_D)
    c.r((cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), 5, fill=(26, 18, 6), outline=(70, 66, 58), width=2)
    c.t((cx, cy), value, 14, AMBER, "mm", "m")
    for sgn in (-1, 1):
        x = cx + sgn * (w / 2 + 18)
        c.d.polygon([((x + 6 * sgn) * S, cy * S), ((x - 6 * sgn) * S, (cy - 10) * S), ((x - 6 * sgn) * S, (cy + 10) * S)], fill=INK)


def qlink(c, box, tag):
    c.r(box, 10, outline=ORANGE + (200,), width=2)
    c.t((box[0] + 30, box[1] + 11), tag, 11, ORANGE, "mm")


def panel_label(c, x, y, text, w):
    c.t((x, y), text, 12, INK_D, "lm")
    c.line([(x + 8 + len(text) * 9.4, y), (x + w, y)], INK_D + (140,), 1)


def page_dig():
    c = Canvas()
    header(c, "DIG")
    panel_label(c, 40, 178, "DISCOGS FILTERS", 1240)
    qlink(c, (40, 190, 1240, 424), "Q 1-4")
    for i, (lab, val, v) in enumerate([("GENRE", "ELECTRONIC", .35), ("STYLE", "ACID HOUSE", .5), ("DECADE", "1990s", .62), ("REGION", "EUROPE", .3)]):
        knob(c, 190 + i * 300, 285, 48, v, lab, val)
    qlink(c, (40, 436, 1240, 598), "Q 5-8")
    for i, (lab, val) in enumerate([("COUNTRY", "GERMANY"), ("SOURCE", "DISCOGS"), ("CHANNEL", "NONE"), ("LENGTH", "ANY - ANY")]):
        window(c, 190 + i * 300, 500, 150, lab, val, 36)
    button(c, 1100, 548, 230, 46, "SEARCH", ORANGE, "DISCOGS DIG")
    button(c, 130, 548, 130, 40, "KEYS", (120, 116, 108), "TYPE A SEARCH")
    c.save("dig.png")


def page_find(keys=False):
    c = Canvas()
    header(c, "FIND")
    panel_label(c, 40, 178, "SOURCE", 1240)
    for i, (name, on) in enumerate([("DISCOGS", False), ("CHANNEL", False), ("YOUTUBE", True)]):
        button(c, 150 + i * 210, 232, 180, 54, name, BLUE if on else (110, 108, 102), "ONLINE DIG" if i == 0 else ("channels.txt" if i == 1 else "ANY VIDEO"), lit=on)
    window(c, 880, 232, 380, "CHANNEL", "NONE - SEE CHANNELS.TXT", 40)
    button(c, 1190, 232, 110, 54, "MUSIC", (110, 108, 102), "ONLY")
    window(c, 250, 330, 230, "MIN LENGTH", "ANY")
    window(c, 640, 330, 230, "MAX LENGTH", "ANY")
    c.t((640, 395), "", 10)
    panel_label(c, 40, 402, "SEARCH TEXT", 1240)
    c.r((40, 416, 1240, 470), 6, fill=(26, 18, 6), outline=(70, 66, 58), width=2)
    c.t((60, 443), "AMEN BREAK_" if keys else "TAP KEYS TO TYPE", 22, AMBER if keys else AMBER_D, "lm", "m")
    button(c, 110, 540, 150, 52, "KEYS", (120, 116, 108), "OPEN KEYBOARD")
    button(c, 290, 540, 170, 52, "SEARCH", ORANGE, "GO")
    c.t((860, 540), "SEARCH   DONE - 12 RESULTS IN 3.1S", 17, INK_D, "mm", "m")
    if keys:   # the popup keyboard
        c.shadow((0, 290, W, H), 0, 10, -4, 140)
        c.r((0, 290, W, H), 0, fill=GRAPH)
        rows = ["1234567890", "QWERTYUIOP", "ASDFGHJKL", "ZXCVBNM"]
        for ri, row in enumerate(rows):
            x0 = 118 + [0, 0, 58, 174][ri]
            for k, ch in enumerate(row):
                kx = x0 + k * 116
                c.r((kx - 52, 306 + ri * 58, kx + 52, 306 + ri * 58 + 50), 6, fill=(64, 64, 68), outline=(20, 20, 22))
                c.t((kx, 331 + ri * 58), ch, 20, WHITE)
        for (cx, cy, w, txt, col) in [(130, 563, 200, "HIDE", (96, 96, 100)), (520, 563, 520, "SPACE", (64, 64, 68)), (880, 563, 190, "CLEAR", (96, 96, 100)),
                                      (1130, 563, 220, "SEND", ORANGE), (1180, 505, 150, "BACK", (96, 96, 100))]:
            c.r((cx - w / 2, cy - 25, cx + w / 2, cy + 25), 6, fill=col, outline=(20, 20, 22))
            c.t((cx, cy), txt, 18, WHITE)
    c.save("find_keys.png" if keys else "find.png")


def page_play():
    c = Canvas()
    header(c, "PLAY")
    panel_label(c, 40, 178, "TRANSPORT", 760)
    qlink(c, (40, 190, 800, 300), "Q 1-4")
    for i, (txt, col, leg) in enumerate([("◄◄", (120, 116, 108), "BACK 15 S"), ("▶", GREEN, "PLAY / PAUSE"), ("■", WHITE, "STOP"), ("►►", (120, 116, 108), "FORWARD 15 S")]):
        button(c, 120 + i * 180, 246, 140, 56, txt, col, leg, textcol=INK if col == WHITE else WHITE)
    button(c, 900, 246, 150, 56, "SYNC", AMBER, "WAIT FOR MPC PLAY", textcol=INK, lit=True)
    c.t((1130, 246), "", 10)
    # gain fader on the right, like a sampler's slider
    c.r((1128, 196, 1152, 296), 6, fill=(20, 20, 22))
    c.r((1112, 220, 1168, 244), 5, fill=(214, 212, 206), outline=(70, 70, 70), width=2)
    c.t((1140, 312), "GAIN", 11, INK_D)
    panel_label(c, 40, 336, "RESULTS", 1240)
    titles = ["01  OPEN SESAME - TREVOR NOVA  1996  4:12", "02  AMEN BREAK - THE WINSTONS  1969  2:05", "03  ACID TRACKS - PHUTURE  1987  6:55", "04  DEEP SPACE - NOVA  1994  5:40",
              "05  MOVE YOUR BODY - MARSHALL  1986  3:30", "06  STRINGS OF LIFE - RHYTHIM  1987  5:12", "07  NO WAY BACK - ADONIS  1986  4:49", "08  (UNTITLED)  1991  7:03"]
    for i, t in enumerate(titles):
        col, row = i % 4, i // 4
        x0, y0 = 40 + col * 306, 352 + row * 112
        playing = i == 1
        c.shadow((x0, y0, x0 + 292, y0 + 100), 8, 4, 3, 90)
        c.r((x0, y0, x0 + 292, y0 + 100), 8, fill=(122, 122, 126), outline=BLUE if playing else (60, 60, 64), width=4 if playing else 2)
        c.r((x0 + 4, y0 + 4, x0 + 288, y0 + 40), 6, fill=(140, 140, 144, 130))
        num, rest = t[:2], t[4:]
        parts = rest.split("  ")
        c.t((x0 + 16, y0 + 24), num, 20, WHITE if not playing else (150, 200, 255), "lm")
        c.t((x0 + 56, y0 + 24), parts[0].split(" - ")[0][:20], 14, WHITE, "lm")
        c.t((x0 + 16, y0 + 56), (parts[0].split(" - ")[1] if " - " in parts[0] else "")[:26], 13, (225, 225, 230), "lm")
        c.t((x0 + 16, y0 + 80), "  ".join(parts[1:]), 12, (200, 200, 206), "lm")
    button(c, 640, 608, 160, 30, "◄ PAGE", (120, 116, 108))
    c.t((760, 608), "1 / 2", 15, INK_D)
    button(c, 880, 608, 160, 30, "PAGE ►", (120, 116, 108))
    c.save("play.png")


if __name__ == "__main__":
    page_dig(); page_find(False); page_find(True); page_play()
    print("wrote", os.path.normpath(OUT))
