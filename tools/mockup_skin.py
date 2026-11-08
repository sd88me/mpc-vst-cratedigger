#!/usr/bin/env python3
"""Art primitives and mock-ups of the Crate Digger skin. The look is now v5 "MPC60": putty body, slate cheeks, bright green LCD with dark ink, cream keys,
red accent keys, black knobs, centred silk-screen section titles (the older functions below still draw the v4 mock-up pages). Was v4 ("S-series rack sampler"): the proportions and materials of the late-80s rack samplers, studied from
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
PLATE, EAR, EDGE = (198, 196, 186), (84, 86, 92), (50, 52, 56)                   # putty faceplate, slate side cheeks
BLUEG, BLUEG2, BLUEG3 = (146, 160, 178), (112, 128, 148), (86, 100, 120)         # grey-blue plates
LCD_BG, LCD_BG2, LCD_FG, LCD_DIM = (96, 206, 92), (176, 248, 150), (8, 38, 14), (44, 112, 52)   # bright green glass, inverse text, ink, dim ink
KEYC, KEYD, INK, RED, BLACK = (238, 238, 232), (100, 104, 112), (30, 30, 32), (196, 40, 32), (22, 22, 24)


def font(size, kind="s"):
    return ImageFont.truetype({"s": SANS, "b": SANSB, "k": SERIFB, "m": MONO, "t": TIT, "tb": TITB}[kind], int(size * S))


def vgrad_raw(c, box, top, bot):
    x0, y0, x1, y1 = [int(v * S) for v in box]
    for k in range(y1 - y0):
        t = k / max(1, y1 - y0 - 1)
        c.d.line([(x0, y0 + k), (x1, y0 + k)], fill=tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3)))


class C:
    def __init__(self):
        self.im = Image.new("RGB", (W * S, H * S), PLATE)
        self.d = ImageDraw.Draw(self.im, "RGBA")
        random.seed(11)
        for _ in range(14000):   # fine paint grain
            x, y = random.randrange(W * S), random.randrange(H * S)
            v = random.randint(-6, 6)
            self.d.point((x, y), fill=(255 if v > 0 else 0,) * 3 + (abs(v) * 2,))
        for x0, x1 in ((0, 22), (W - 22, W)):   # slate side cheeks
            vgrad_raw(self, (x0, 0, x1, H), (98, 100, 106), (74, 76, 82))
        for x in (22, W - 22):
            self.d.line([(x * S, 0), (x * S, H * S)], fill=EDGE, width=2 * S)

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
    """The recessed dark slate bezel and the bright green dot-matrix glass: a pixel grid, a lighter top, an inner shadow, a faint glare."""
    x0, y0, x1, y1 = box
    c.shadow(box, 4, 5, 3, 150)
    vgrad(c, box, (74, 76, 82), (44, 46, 50), 5)
    c.r(box, 5, outline=(24, 24, 26), width=2)
    c.r((x0 + 2, y0 + 2, x1 - 2, y1 - 2), 4, outline=(255, 255, 255, 46), width=1)
    ix0, iy0, ix1, iy1 = x0 + 10, y0 + 10, x1 - 10, y1 - 10
    vgrad(c, (ix0, iy0, ix1, iy1), (112, 222, 104), (84, 196, 84))
    for x in range(int(ix0), int(ix1), 3):
        c.d.line([(x * S, iy0 * S), (x * S, iy1 * S)], fill=(10, 60, 20, 34), width=1)
    for y in range(int(iy0), int(iy1), 3):
        c.d.line([(ix0 * S, y * S), (ix1 * S, y * S)], fill=(10, 60, 20, 34), width=1)
    for k in range(10):
        c.d.line([(ix0 * S, (iy0 + k) * S), (ix1 * S, (iy0 + k) * S)], fill=(0, 30, 0, 80 - k * 8), width=S)
        c.d.line([((ix0 + k) * S, iy0 * S), ((ix0 + k) * S, iy1 * S)], fill=(0, 30, 0, 60 - k * 6), width=S)
    gl = Image.new("RGBA", c.im.size, (0, 0, 0, 0))
    ImageDraw.Draw(gl).polygon([(ix0 * S, iy0 * S), ((ix0 + (ix1 - ix0) * 0.38) * S, iy0 * S), (ix0 * S, (iy0 + (iy1 - iy0) * 0.5) * S)], fill=(255, 255, 255, 18))
    c.im.paste(gl, (0, 0), gl)
    c.d = ImageDraw.Draw(c.im, "RGBA")


def lcd_mini(c, box):
    """A small green read-out window (one value), same glass as the main LCD."""
    x0, y0, x1, y1 = box
    c.shadow(box, 3, 3, 2, 120)
    vgrad(c, box, (74, 76, 82), (44, 46, 50), 3)
    c.r(box, 3, outline=(24, 24, 26), width=1)
    vgrad(c, (x0 + 4, y0 + 4, x1 - 4, y1 - 4), (112, 222, 104), (88, 200, 88))


def lt(c, xy, text, size=15, inv=False, dim=False, anchor="lm"):
    """LCD text: dark ink on the green glass (a one-dot light edge), or bright text when inverse (on a dark bar)."""
    if not inv:
        c.t((xy[0] + 1, xy[1] + 1), text, size, (150, 236, 140) if not dim else (130, 220, 124), anchor, "t")
    c.t(xy, text, size, LCD_BG2 if inv else (LCD_DIM if dim else LCD_FG), anchor, "t")


def invbar(c, x0, y0, x1, y1):
    c.d.rectangle([x0 * S, y0 * S, x1 * S, y1 * S], fill=(16, 52, 22))


SILK = (188, 186, 176)


SILK = (146, 150, 146)   # the cool mid-grey of the MPC60 pad well: every printed section is this colour, flat, no outline


def title_rule(c, x0, x1, y, text, ink=INK, rule=(96, 94, 86)):
    """A silk-screened title in the MPC60 manner: -- TITLE -- centred, thin rules to both ends."""
    mid = (x0 + x1) / 2
    tw = c.d.textlength(text, font=font(12, "tb")) / S
    c.t((mid, y), text, 12, ink, "mm", "tb")
    c.line([(x0, y), (mid - tw / 2 - 8, y)], rule, 1)
    c.line([(mid + tw / 2 + 8, y), (x1, y)], rule, 1)


def plate(c, box, title=None, color=None, ink=INK):
    """A silk-screened section of the faceplate: flat putty (or a flat colour), the title printed centred with rules."""
    x0, y0, x1, y1 = box
    c.r(box, 4, fill=color or SILK)
    if title:
        title_rule(c, x0 + 14, x1 - 14, y0 + 15, title, ink, (96, 94, 86) if ink == INK else (230, 236, 244))


def brushed(c, box):
    """A silk-screened key section: flat grey, no outline; the title is printed by bracket()."""
    c.r(box, 4, fill=SILK)


def bracket(c, x0, x1, y, text):
    title_rule(c, x0, x1, y, text)


KEYCOL = {"cream": ((248, 242, 218), (226, 218, 184), (112, 106, 84), INK), "dark": ((104, 104, 108), (66, 66, 70), (34, 34, 36), (240, 238, 230)),
          "red": ((206, 56, 48), (150, 24, 22), (70, 12, 10), (255, 244, 238)), "blue": ((248, 242, 218), (226, 218, 184), (112, 106, 84), INK),
          "white": ((255, 252, 240), (232, 226, 200), (112, 106, 84), INK)}
LAMP = {"green": (70, 230, 120), "red": (255, 60, 40), "amber": (255, 176, 40)}


def key(c, cx, cy, w, h, label=None, color="cream", lit=False, size=13, sub=None, lamp="red"):
    """A plastic key in the MPC60 manner, with no drawn border: a soft contact shadow, a darker side wall visible under the cap, and a cap with
    a vertical gradient, a faint specular line along the top edge and a subtle shade near the bottom. Labelled by what it does; the small
    indicator lamp sits above it (glowing when lit)."""
    top, bot, edge, ink = KEYCOL[color]
    x0, y0, x1, y1 = cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2
    c.shadow((x0, y0 + 2, x1, y1), 4, 4, 3, 150)
    rad = 4 if h < 50 else 5
    wall = tuple(int(v * 0.58) for v in bot)
    vgrad(c, (x0, y0 + 3, x1, y1 + 1), wall, tuple(int(v * 0.45) for v in bot), rad)            # the side wall under the cap
    face = (x0, y0, x1, y1 - 3)
    vgrad(c, face, top, bot, rad)
    c.line([(x0 + rad + 2, y0 + 1.5), (x1 - rad - 2, y0 + 1.5)], (255, 255, 255, 150), 1.4)      # specular edge
    c.line([(x0 + rad + 2, y1 - 4.5), (x1 - rad - 2, y1 - 4.5)], (0, 0, 0, 38), 1.4)              # shade where the cap rolls under
    ly = cy - h / 2 - 4
    col = LAMP[lamp] if lamp else None
    if col and lit:
        glow(c, cx, ly, 10, col, 190)
        c.d.rectangle([(cx - 9) * S, (ly - 1.5) * S, (cx + 9) * S, (ly + 2) * S], fill=tuple(min(255, v + 30) for v in col))
    elif col:
        c.d.rectangle([(cx - 9) * S, (ly - 1.5) * S, (cx + 9) * S, (ly + 2) * S], fill=tuple(v // 4 for v in col) + (200,))
    if label:
        c.t((cx, cy - (7 if sub else 0) - 1), label, size, ink, "mm", "b")
    if sub:
        c.t((cx, cy + 10), sub, 8, ink, "mm")


def knob(c, cx, cy, r, value, name=None, big=False, pointer=(245, 245, 240), body=(36, 36, 40), numbers=True, ruler=True, only_ruler=False, ruler_ink=None):
    """Knurled knob: big = the grey-blue CURSOR/DATA style with machined rings, otherwise black with a white pointer. A printed dot ruler
    with 0 / 5 / 10 around it, a soft specular highlight, a drop shadow."""
    if ruler or only_ruler:
        for i in range(11):
            a = math.radians(135 + i * 27)
            c.ell(cx + math.cos(a) * (r + 10), cy + math.sin(a) * (r + 10), 1.7, 1.7, fill=ruler_ink or INK)
            if numbers and i in (0, 5, 10):
                c.t((cx + math.cos(a) * (r + 21), cy + math.sin(a) * (r + 21)), str(i), 8, ruler_ink or INK)
    if only_ruler:
        return
    c.shadow((cx - r, cy - r, cx + r, cy + r), r, 7, 7, 160)
    if big:
        c.ell(cx, cy, r, r, fill=(22, 22, 24), outline=(0, 0, 0), width=2)           # skirt
        c.ell(cx, cy + 1, r - 3, r - 3, fill=(40, 40, 44))
        cap = r - 6
        vgrad(c, (cx - cap, cy - cap, cx + cap, cy + cap), (86, 86, 92), (52, 52, 56), int(cap))   # matte cap, lit from above
        c.ell(cx, cy, cap, cap, outline=(110, 110, 116), width=1)
    else:
        c.ell(cx, cy, r, r, fill=BLACK, outline=(0, 0, 0), width=2)
        for i in range(44):
            a = math.radians(i * 8.2)
            c.line([(cx + math.cos(a) * (r - 5), cy + math.sin(a) * (r - 5)), (cx + math.cos(a) * (r - 1), cy + math.sin(a) * (r - 1))], (104, 104, 108), 1)
        c.ell(cx, cy, r - 8, r - 8, fill=body, outline=(10, 10, 12), width=1)
        c.ell(cx - 1, cy - 2, r - 14, r - 14, fill=(60, 60, 64))
        c.ell(cx - r * 0.2, cy - r * 0.3, r * 0.4, r * 0.25, fill=(255, 255, 255, 34))
    a = math.radians(135 + value * 270)
    c.line([(cx + math.cos(a) * (r * 0.30), cy + math.sin(a) * (r * 0.30)), (cx + math.cos(a) * (r - 6), cy + math.sin(a) * (r - 6))], (246, 246, 240), 4)
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
    """The wordmark in the MPC60 manner: a flat red serif, a small italic line under it, a model badge in outline letters."""
    c.t((44, 34), "CRATE DIGGER", 30, (190, 34, 40), "lm", "k")
    c.t((46, 62), "digital record sampler", 11, (110, 30, 34), "lm", "s")
    master(c)
