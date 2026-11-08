#!/usr/bin/env python3
"""Crate Digger's native MPC skin: skins/TUI.json + skins/Q-Links.json + the PNGs they use (the SDK method, docs/SDK-PORTING.md).
Three tabs (PLAY, FILTERS, FIND) in the "rack sampler" look of docs/skin-mockups: off-white faceplate, one main blue LCD per tab, silk-screened
sections, cream / dark grey / pale blue keys with indicator lamps, grey knobs, a horizontal main-volume fader and a stereo level meter.
The art is drawn with tools/mockup_skin.py's primitives; the live parts (LCD text, keys, knobs, results, keyboard) are TUI components bound to
the frozen parameter indices of vst/params.lock. The component shapes are the ones the 1.x skin proved on both devices.
    python3 tools/make_tui.py        # -> skins/   (build-sdk.sh copies it to Plugin Skins/)"""
import json, os, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from PIL import Image, ImageDraw
import mockup_skin as M
from tui_lib import *

ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "skins")
LOCK = [l.strip() for l in open(os.path.join(ROOT, "vst", "params.lock")) if l.strip()]
S = M.S


def P(key):
    return "Parameter %d" % LOCK.index(key)


def save(im, name):
    im.save(os.path.join(OUT, name))
    return name


# ---- sprites: small transparent canvases drawn with the mock-up primitives ---------------------------------------------------------------
class Sprite(M.C):
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.im = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.im, "RGBA")

    def image(self):
        return self.im.resize((self.w, self.h), Image.LANCZOS)


PAD_X, PAD_TOP, PAD_BOT = 14, 26, 14


def key_images(name, label, color, w, h, size=13, lamp=None, toggle=False):
    """off / on images of a key. A toggle's on image is the lit key (lamp glowing); a trigger's is the pressed key. Returns (on, off, sw, sh)."""
    sw, sh = w + 2 * PAD_X, h + PAD_TOP + PAD_BOT
    outs = []
    for on in (True, False):
        sp = Sprite(sw, sh)
        M.key(sp, sw / 2, PAD_TOP + h / 2, w, h, label, color, lit=(on and toggle), size=size, lamp=lamp)
        if on and not toggle:
            sp.r((sw / 2 - w / 2, PAD_TOP, sw / 2 + w / 2, PAD_TOP + h), 3, fill=(0, 0, 0, 46))
        outs.append(save(sp.image(), "key_%s_%s.png" % (name, "on" if on else "off")))
    return outs[0], outs[1], sw, sh


DEFS, DEFKEYS = [], set()


def add_def(key, value):
    if key not in DEFKEYS:
        DEFKEYS.add(key)
        DEFS.append({"key": key, "value": value})


def trig_def(key, on, off, sw, sh):
    """A key as the 1.x skin built it: Mouse Down selects the Q-Link, Enter toggles; a Button inside shows the state."""
    add_def(key, component([entry("Button", "Button", {"version": 1, "onImage": on, "offImage": off, "buttonId": 1, "numButtonsInGroup": 1, "handleName": "Data"},
                                  "0 0 %d %d" % (sw, sh))],
                           actions=[act("Mouse Down", "Q-Link"), act("Enter Pressed", "Toggle Switch")]))


def tap_def(key, img, w, h):
    add_def(key, component([entry("Button", "Button", {"version": 1, "onImage": img, "offImage": img, "buttonId": 1, "numButtonsInGroup": 1, "handleName": "Data"},
                                  "0 0 %d %d" % (w, h))], actions=[act("Enter Pressed", "Toggle Switch")]))


class Page:
    def __init__(self, name, fn):
        self.name, self.fn = name, fn
        self.kids, self.groups, self.qrows = [], [], []

    def key(self, param, label, color, cx, cy, w, h, size=13, lamp=None, toggle=False, ind=None, nm=None):
        nm = nm or "%s_%s" % (param, label.replace(" ", "").replace("◄", "L").replace("►", "R").replace("▶", "P").replace("❚", "").replace("■", "S"))
        nm = "".join(ch if ch.isalnum() or ch == "_" else "" for ch in nm) + "_%dx%d" % (w, h)
        on, off, sw, sh = key_images(nm, label, color, w, h, size=size, lamp=lamp, toggle=toggle)
        trig_def("cd_" + nm, on, off, sw, sh)
        self.kids.append(entry(label or param, "cd_" + nm, {"version": 1, "handleName": "Data"}, "%d %d %d %d" % (cx - sw / 2, cy - PAD_TOP - h / 2, sw, sh),
                               remap=P(param), focus="Yes", ind=ind))

    def lcd_text(self, key, x, y, w, size=16, h=26, just="left verticallyCentred", handle="Data"):
        e = label("Value", "%d %d %d %d" % (x, y - h / 2, w, h), remap=[("Data", P(key)), ("Text", P(key))] if handle == "Text" else P(key),
                  just=just, colour="ffecf0ff", style="SemiBold", case="Original", h=float(size) + 4)
        if handle == "Text":
            e["componentData"]["data"]["handleName"] = "Text"
        self.kids.append(e)

    def qgroup(self, rect, keys):
        self.groups.append("%d %d %d %d" % (rect[0], rect[1], rect[2] - rect[0], rect[3] - rect[1]))
        self.qrows.append(keys)

    def tab(self, bgfile):
        kids = [entry("bg", "Image", {"version": 2, "imageType": "Regular", "colour": "0", "image": bgfile}, "0 0 1280 628")] + self.kids
        return {"version": 1, "tabName": self.name, "fnKeyIndex": self.fn, "fnKeySubIndex": 0,
                "componentDefinition": component(kids, background=bg("ff1a1a1a")), "qlinkBoundsData": self.groups}


# ---- the master section: main volume (a horizontal fader) and the stereo level meter, on every tab ---------------------------------------
GAIN_X, GAIN_Y, GAIN_W, GAIN_H = 760, 22, 240, 44
LEV_X, LEV_Y, LEV_W, LEV_H = 1068, 24, 160, 16


def master_bg(c):
    c.r((700, 6, 1240, 78), 4, fill=M.SILK)
    c.t((718, 42), "GAIN", 10, M.INK, "lm", "b")
    c.t((1016, 42), "LEVEL", 9, M.INK, "lm", "b")
    c.t((1062, 30), "L", 9, M.INK)
    c.t((1062, 52), "R", 9, M.INK)


def gain_strip(frames=64):
    strip = Image.new("RGBA", (GAIN_W, GAIN_H * frames), (0, 0, 0, 0))
    for f in range(frames):
        sp = Sprite(GAIN_W, GAIN_H)
        g = f / (frames - 1)
        sp.r((20, 16, 220, 24), 3, fill=(20, 20, 22), outline=(60, 60, 62), width=1)
        for i in range(21):
            sp.line([(22 + i * 9.5, 30), (22 + i * 9.5, 35 if i % 5 == 0 else 32)], M.INK, 1)
        cx = 20 + g * 200
        sp.shadow((cx - 8, 6, cx + 8, 34), 2, 2, 2, 140)
        M.vgrad(sp, (cx - 8, 6, cx + 8, 34), (236, 236, 232), (170, 170, 166), 2)
        sp.r((cx - 8, 6, cx + 8, 34), 2, outline=(60, 60, 58), width=1)
        sp.line([(cx, 8), (cx, 32)], (40, 40, 40), 2)
        strip.paste(sp.image(), (0, f * GAIN_H))
    return save(strip, "gain_strip.png"), frames


def level_strip():
    frames = 11
    strip = Image.new("RGBA", (LEV_W, LEV_H * frames), (0, 0, 0, 0))
    for f in range(frames):
        sp = Sprite(LEV_W, LEV_H)
        for i in range(10):
            col = (255, 60, 40) if i == 9 else ((255, 190, 40) if i >= 7 else (70, 230, 120))
            x, y = 8 + i * 15, 8
            if i < f:
                M.glow(sp, x, y, 7, col, 130)
            sp.r((x - 6, y - 5, x + 6, y + 5), 2, fill=col if i < f else tuple(v // 4 for v in col), outline=(40, 40, 40), width=1)
        strip.paste(sp.image(), (0, f * LEV_H))
    return save(strip, "level_strip.png"), frames


def add_master(p):
    gname, gframes = gain_strip()
    add_def("cd_gain", component([entry("Slider", "Knob", {"version": 3, "knobType": "FilmStrip", "filmStrip": gname, "numFrames": gframes, "invert": False,
                                                          "dragOrientation": "Horizontal", "handleName": "Data"}, "0 0 %d %d" % (GAIN_W, GAIN_H))],
                                 actions=[act("Mouse Down", "Q-Link"), act("Double Click", "Show Overlay", "knob overlay"), act("Enter Pressed", "Show Overlay", "knob overlay")],
                                 background=bg("00000000")))
    p.kids.append(entry("gain", "cd_gain", {"version": 1, "handleName": "Data"}, "%d %d %d %d" % (GAIN_X, GAIN_Y, GAIN_W, GAIN_H), remap=P("gain"), focus="Yes"))
    lname, lframes = level_strip()
    for key, y in (("level_l", LEV_Y + 0), ("level_r", LEV_Y + 22)):
        p.kids.append(entry(key, "Image", {"version": 2, "imageType": "FilmStrip", "colour": "0", "image": lname, "numFrames": lframes, "handleName": "Data"},
                            "%d %d %d %d" % (LEV_X, y, LEV_W, LEV_H), remap=P(key)))


# ---- knobs -------------------------------------------------------------------------------------------------------------------------------------
KNOBS = {}


def knob_def(r, big=True):
    size = int(round((r + 8) * 2))
    name = "cdk%d" % r
    if name not in KNOBS:
        strip = Image.new("RGBA", (size, size * 64), (0, 0, 0, 0))
        for f in range(64):
            sp = Sprite(size, size)
            M.knob(sp, size / 2, size / 2, r, f / 63.0, None, big=big, ruler=False)
            strip.paste(sp.image(), (0, f * size))
        save(strip, name + ".png")
        KNOBS[name] = size
        add_def(name, component([entry("knob", "Knob", {"version": 3, "knobType": "FilmStrip", "filmStrip": name + ".png", "numFrames": 64, "invert": False,
                                                       "dragOrientation": "Vertical", "handleName": "Data"}, "0 0 %d %d" % (size, size))],
                                actions=[act("Mouse Down", "Q-Link"), act("Double Click", "Show Overlay", "knob overlay"), act("Enter Pressed", "Show Overlay", "knob overlay")],
                                background=bg("00000000")))
    return name, KNOBS[name]


def add_knob(p, param, cx, cy, r):
    name, size = knob_def(r)
    p.kids.append(entry(param, name, {"version": 1, "handleName": "Data"}, "%d %d %d %d" % (cx - size // 2, cy - size // 2, size, size), remap=P(param), focus="Yes"))


def arrow(p, param, ch, cx, cy, w=36, h=28, size=12):
    nm = "arrow_%s" % param
    sp = Sprite(w + 2 * PAD_X, h + PAD_TOP + PAD_BOT)
    M.key(sp, sp.w / 2, PAD_TOP + h / 2, w, h, ch, "cream", size=size, lamp=None)
    img = save(sp.image(), nm + ".png")
    tap_def("cd_" + nm, img, sp.w, sp.h)
    p.kids.append(entry(nm, "cd_" + nm, {"version": 1, "handleName": "Data"}, "%d %d %d %d" % (cx - sp.w / 2, cy - PAD_TOP - h / 2, sp.w, sp.h), remap=P(param)))


# ---- shared page art ---------------------------------------------------------------------------------------------------------------------------
def base_canvas(tabname):
    c = M.C()
    M.header(c, tabname)   # draws the wordmark, badge and (static) master; the master is repainted below without its moving parts
    c.r((700, 6, 1240, 78), 4, fill=M.PLATE)   # clear the mock-up's master, then draw the empty one
    master_bg(c)
    return c


def lcd_frame(c, box):
    M.lcd(c, box)


def lcd_header_static(c, x0, y0, x1):
    M.lt(c, (x0, y0), "NOW", 12, dim=True)
    M.lt(c, (x0, y0 + 22), "STATUS", 12, dim=True)
    M.lt(c, (x1 - 150, y0 + 22), "TIME", 12, dim=True)
    M.lt(c, (x0, y0 + 44), "SEARCH", 12, dim=True)
    c.d.rectangle([x0 * S, (y0 + 58) * S, (x1 + 2) * S, (y0 + 60) * S], fill=M.LCD_DIM)


def lcd_header_live(p, x0, y0, x1):
    p.lcd_text("now_playing", x0 + 68, y0, x1 - x0 - 80, size=16)
    p.lcd_text("status", x0 + 68, y0 + 22, 440, size=16)
    p.lcd_text("time", x1 - 100, y0 + 22, 100, size=16)
    p.lcd_text("search_status", x0 + 68, y0 + 44, x1 - x0 - 80, size=16)


def row_def(w, h):
    """A result row: a touch area with the LCD text; the playing row (value 1) gets a lighter bar."""
    key = "cd_row%dx%d" % (w, h)
    if key not in DEFKEYS:
        on = Sprite(w, h)
        on.r((0, 0, w - 1, h - 1), 4, fill=(66, 104, 230))
        on.r((0, 0, w - 1, h - 1), 4, outline=(150, 176, 255), width=1)
        offs = Sprite(w, h)
        add_def(key, component([
            entry("Button", "Button", {"version": 1, "onImage": save(on.image(), "row_on.png"), "offImage": save(offs.image(), "row_off.png"),
                                       "buttonId": 1, "numButtonsInGroup": 1, "handleName": "Data"}, "0 0 %d %d" % (w, h)),
            entry("Value", "Label", {"version": 1, "textStyle": text_style(h=20.0, colour="ffecf0ff", just="left verticallyCentred", case="Original"),
                                     "type": "Value", "handleName": "Data"}, "10 0 %d %d" % (w - 14, h)),
        ], actions=[act("Mouse Down", "Toggle Switch"), act("Enter Pressed", "Toggle Switch")]))
    return key


# ---- PLAY ----------------------------------------------------------------------------------------------------------------------------------------
def build_play():
    c = base_canvas("PLAY")
    p = Page("PLAY", 0)
    M.lcd(c, (40, 82, 1240, 440))
    lcd_header_static(c, 66, 112, 1212)
    lcd_header_live(p, 66, 112, 1212)
    w, h = 570, 54
    rk = row_def(w, h)
    for i in range(8):
        col, row = i // 4, i % 4
        x0, y0 = 66 + col * 590, 198 + row * 58
        p.kids.append(entry("result %d" % (i + 1), rk, {"version": 1, "handleName": "Data"}, "%d %d %d %d" % (x0 - 6, y0 - 14, w, h), remap=P("result_%d" % (i + 1)),
                            focus="Yes" if i == 0 else "No"))
    M.brushed(c, (40, 456, 640, 614))
    M.bracket(c, 60, 620, 474, "TRANSPORT")
    for i, (param, lab, cap, size) in enumerate([("rewind_15", "◄◄", "BACK 15 S", 20), ("play_pause", "▶ ❚❚", "PLAY / PAUSE", 18), ("stop", "■", "STOP", 20), ("forward_15", "►►", "FORWARD 15 S", 20)]):
        cx = 120 + i * 140
        p.key(param, lab, "cream", cx, 540, 110, 62, size=size, lamp=None)
        c.t((cx, 584), cap, 9, M.INK)
    M.brushed(c, (656, 456, 1240, 614))
    M.bracket(c, 676, 1220, 474, "RESULTS  /  SEARCH")
    p.key("page_prev", "◄ PAGE", "cream", 730, 540, 108, 62, size=14)
    p.key("page_next", "PAGE ►", "cream", 865, 540, 108, 62, size=14)
    p.key("transport_sync", "SYNC", "cream", 1000, 540, 108, 62, size=14, lamp="amber", toggle=True)
    p.key("search", "SEARCH", "dark", 1135, 540, 108, 62, size=14)
    c.t((1000, 584), "WAIT FOR MPC PLAY", 8, M.INK)
    add_master(p)
    p.qgroup((40, 456, 640, 614), ["rewind_15", "play_pause", "stop", "forward_15"])
    p.qgroup((656, 456, 1240, 614), ["transport_sync", "search", "page", "gain"])
    return p, c


# ---- FILTERS ---------------------------------------------------------------------------------------------------------------------------------
FILTERS = [("genre", "GENRE"), ("style", "STYLE"), ("decade", "DECADE"), ("region", "REGION"), ("country", "COUNTRY")]


def build_filters():
    c = base_canvas("FILTERS")
    p = Page("FILTERS", 1)
    M.lcd(c, (40, 82, 1240, 400))
    lcd_header_static(c, 66, 112, 1212)
    lcd_header_live(p, 66, 112, 1212)
    for i, (key, cap) in enumerate(FILTERS):
        col, row = i // 3, i % 3
        x0, y0 = 66 + col * 590, 198 + row * 62
        M.lt(c, (x0, y0 + 4), "%02d" % (i + 1), 20)
        M.lt(c, (x0 + 52, y0 + 32), cap, 12, dim=True)
        p.lcd_text(key, x0 + 46, y0 + 4, 520, size=26, h=40, handle="Text")
    M.lt(c, (66 + 590 + 52, 198 + 2 * 62 + 4), "STYLE FOLLOWS GENRE", 13, dim=True)
    M.lt(c, (66 + 590 + 52, 198 + 2 * 62 + 30), "COUNTRY FOLLOWS REGION", 13, dim=True)
    M.plate(c, (40, 414, 1240, 614), "DISCOGS FILTERS")
    for i, (key, cap) in enumerate(FILTERS):
        cx = 142 + i * 188
        M.knob(c, cx, 502, 36, 0.0, None, big=True, numbers=False, only_ruler=True)
        c.t((cx, 558), cap, 10, M.INK, "mm", "b")
        add_knob(p, key, cx, 502, 36)
        arrow(p, key + "_prev", "◄", cx - 70, 502)
        arrow(p, key + "_next", "►", cx + 70, 502)
    p.key("search", "SEARCH", "dark", 1110, 520, 190, 62, size=16)
    c.t((1110, 566), "SEARCH DISCOGS", 9, M.INK)
    add_master(p)
    p.qgroup((40, 420, 830, 610), ["genre", "style", "decade", "region"])
    p.qgroup((830, 420, 1240, 610), ["country", "search"])
    return p, c


# ---- FIND --------------------------------------------------------------------------------------------------------------------------------------
def selector(c, p, cx, cy, key, name, gap, r=22):
    M.knob(c, cx, cy, r, 0.0, None, big=True, numbers=False, only_ruler=True)
    c.t((cx, cy + r + 20), name, 9, M.INK)
    add_knob(p, key, cx, cy, r)
    arrow(p, key + "_prev", "◄", cx - gap, cy, w=36, h=26, size=11)
    arrow(p, key + "_next", "►", cx + gap, cy, w=36, h=26, size=11)


def build_find():
    c = base_canvas("FIND")
    p = Page("FIND", 2)
    M.lcd(c, (40, 82, 1240, 340))
    lcd_header_static(c, 66, 112, 1212)
    lcd_header_live(p, 66, 112, 1212)
    M.lt(c, (70, 198), "SOURCE", 13, dim=True)
    p.lcd_text("source", 170, 198, 300, size=15, handle="Text")
    M.lt(c, (520, 198), "CHANNEL", 13, dim=True)
    p.lcd_text("channel", 620, 198, 560, size=15, handle="Text")
    M.lt(c, (70, 224), "LENGTH", 13, dim=True)
    p.lcd_text("min_len", 170, 224, 90, size=15, handle="Text")
    M.lt(c, (268, 224), "-", 15)
    p.lcd_text("max_len", 290, 224, 90, size=15, handle="Text")
    M.lt(c, (520, 224), "MUSIC ONLY", 13, dim=True)
    p.lcd_text("music", 660, 224, 120, size=15, handle="Text")
    M.lt(c, (70, 276), "TEXT", 13, dim=True)
    p.lcd_text("query", 170, 277, 1030, size=18)
    M.brushed(c, (40, 354, 300, 540))
    M.bracket(c, 56, 284, 370, "DISCOGS")
    p.key("source_discogs", "DISCOGS", "blue", 170, 416, 160, 56, size=15, toggle=True, lamp="red")
    c.t((170, 472), "USES THE FILTERS TAB", 8, M.INK)
    M.brushed(c, (316, 354, 760, 540))
    M.bracket(c, 332, 744, 370, "CHANNEL")
    p.key("source_channel", "CHANNEL", "blue", 538, 416, 160, 56, size=15, toggle=True, lamp="red")
    selector(c, p, 538, 494, "channel", "CHANNEL  (CHANNELS.TXT)", 76)
    M.brushed(c, (776, 354, 1240, 540))
    M.bracket(c, 792, 1224, 370, "YOUTUBE")
    p.key("source_youtube", "YOUTUBE", "blue", 880, 416, 140, 56, size=15, toggle=True, lamp="red")
    p.key("music_btn", "MUSIC ONLY", "cream", 1060, 416, 140, 56, size=13, toggle=True, lamp="red")
    selector(c, p, 870, 494, "min_len", "MIN LENGTH", 52)
    selector(c, p, 1070, 494, "max_len", "MAX LENGTH", 52)
    M.brushed(c, (40, 550, 1240, 616))
    M.bracket(c, 56, 1224, 566, "SEARCH")
    p.key("keys", "KEYBOARD", "dark", 150, 596, 160, 38, size=13)
    p.key("find_search", "SEARCH", "dark", 340, 596, 160, 38, size=14)
    add_master(p)
    p.qgroup((316, 354, 1240, 540), ["source", "channel", "min_len", "max_len"])
    p.qgroup((40, 550, 1240, 616), ["music", "keys", "find_search", "gain"])
    # the popup keyboard, shown while `kb` is on: a plate that swallows touches, and the keys over it
    ind = ["IndexedEnabling/1/2/%s" % P("kb")]
    plate_img = Sprite(1280, 282)
    plate_img.d.rectangle([0, 0, 1280 * S, 282 * S], fill=M.SILK)
    plate_img.line([(0, 0), (1280, 0)], (60, 60, 58), 2)
    plate_img.t((44, 16), "KEYBOARD", 10, M.INK, "lm", "b")
    plate_img.line([(130, 16), (1236, 16)], (120, 120, 116), 1)
    pimg = save(plate_img.image(), "kb_plate.png")
    add_def("cd_kbplate", component([entry("Button", "Button", {"version": 1, "onImage": pimg, "offImage": pimg, "buttonId": 1, "numButtonsInGroup": 1, "handleName": "Data"}, "0 0 1280 282")],
                                    actions=[act("Mouse Down", "Q-Link")]))
    p.kids.append(entry("noop", "cd_kbplate", {"version": 1, "handleName": "Data"}, "0 346 1280 282", remap=P("noop"), focus="Yes", ind=ind))
    rows = ["1234567890", "QWERTYUIOP", "ASDFGHJKL", "ZXCVBNM"]
    for ri, row in enumerate(rows):
        x0 = 118 + [0, 0, 58, 174][ri]
        for k, ch in enumerate(row):
            p.key("k_" + ch, ch, "blue" if ri == 0 else "cream", x0 + k * 116, 378 + ri * 52 + 22, 100, 42, size=18, ind=ind, nm="kb_" + ch)
    for param, lab, cx, cy, w, col in [("k_hide", "HIDE", 130, 592, 200, "dark"), ("k_space", "SPACE", 520, 592, 520, "cream"), ("k_clear", "CLEAR", 880, 592, 190, "dark"),
                                       ("k_send", "SEARCH", 1130, 592, 220, "dark"), ("k_back", "BACK", 1180, 547, 150, "dark")]:
        p.key(param, lab, col, cx, cy, w, 40, size=14, ind=ind, nm="kb_" + param)
    return p, c


# ---- Q-Links -----------------------------------------------------------------------------------------------------------------------------------
def qlinks_for(pages):
    maps = []
    for p in pages:
        q = {"Q-Link %d" % n: -1 for n in range(1, 17)}
        for gi, keys in enumerate(p.qrows[:4]):
            first = 13 - 4 * gi
            for i, key in enumerate(keys):
                q["Q-Link %d" % (first + i)] = LOCK.index(key)
        maps.append({"Tab": p.fn + 1, "SubTab": 1, "Bank Direction": "RowTopDown", "Q-Links": q})
    prog = {"Q-Link %d" % n: -1 for n in range(1, 17)}
    return {"version": 4, "info": {"version": 1, "type": "CompleteDescription"},
            "Screen Mode Q-Links": {"version": 4, "map": maps}, "Program Mode Q-Links": prog}


def overlay_defs():
    knob_overlay = component([entry("overlay", "KnobOverlay", Obj(
        ("version", 2), ("version", 1),
        ("actions", [{"version": 1, "onAction": "Focus Lost", "handler": "Focus Lost", "handleName": "Focus Lost", "additionalData": ""}]),
        ("overlayType", "Knob With Header"), ("scaleType", "Linear"), ("polarityType", "Unipolar"),
        ("showMinusSign", True), ("handleName", "Data")), "0 0 1280 800", focus="Yes")], ignore=True)
    return [{"key": "knob overlay", "value": knob_overlay}]


SAMPLE = {"now_playing": "OPEN SESAME - TREVOR NOVA", "status": "STREAMING", "time": "0:42", "search_status": "DONE - 12 RESULTS IN 3.1S", "query": "AMEN BREAK_",
          "genre": "ELECTRONIC", "style": "ACID HOUSE", "decade": "1990s", "region": "EUROPE", "country": "GERMANY", "source": "YOUTUBE", "channel": "NONE - SEE CHANNELS.TXT",
          "min_len": "ANY", "max_len": "ANY", "music": "OFF"}
ROWS = ["01  OPEN SESAME - TREVOR NOVA  1996  4:12", "02  AMEN BREAK - THE WINSTONS  1969  2:05", "03  ACID TRACKS - PHUTURE  1987  6:55", "04  DEEP SPACE - NOVA  1994  5:40",
        "05  MOVE YOUR BODY - MARSHALL  1986  3:30", "06  STRINGS OF LIFE - RHYTHIM  1987  5:12", "07  NO WAY BACK - ADONIS  1986  4:49", "08  (UNTITLED)  1991  7:03"]


def preview(pages, tabs):
    """Compose each tab offline the way the MPC would (art, then the components' images, sample text) to check positions. build/preview/*.png"""
    defs = {d["key"]: d["value"] for d in DEFS}
    for p, tab in zip(pages, tabs):
        im = Image.open(os.path.join(OUT, tab["componentDefinition"]["componentsData"][0]["componentData"]["data"]["image"])).convert("RGBA")
        d = ImageDraw.Draw(im)
        for e in p.kids:
            cd = e["componentData"]
            x, y, w, h = [float(v) for v in e["bounds"]["bounds"].split()]
            if e["bounds"].get("additionalInvalidatingHandles") and "noop" not in cd["name"] and not cd["name"].startswith("kb_"):
                pass
            if cd["type"] == "Image" and cd["data"].get("imageType") == "FilmStrip":
                st = Image.open(os.path.join(OUT, cd["data"]["image"])).convert("RGBA")
                n = cd["data"]["numFrames"]
                fr = st.crop((0, st.height // n * 6, st.width, st.height // n * 7))
                im.alpha_composite(fr, (int(x), int(y)))
            elif cd["type"] == "Label":
                rp = e["handle remapping"]["map"][0]["value"] if e["handle remapping"]["map"] else None
                key = LOCK[int(rp.split()[1])] if rp else ""
                txt = SAMPLE.get(key, ROWS[int(key.split("_")[1]) - 1] if key.startswith("result_") else key)
                d.text((x + 4, y + h / 2), txt, font=M.ImageFont.truetype(M.MONO, int(float(cd["data"]["textStyle"]["font"]["height"]) * 0.8)), fill=(236, 240, 255), anchor="lm")
            elif cd["type"] in defs:
                comp = defs[cd["type"]]
                for sub in comp["componentsData"]:
                    sd = sub["componentData"]
                    sx, sy, sw, sh = [float(v) for v in sub["bounds"]["bounds"].split()]
                    if sd["type"] == "Button":
                        img = sd["data"]["offImage"]
                        if "key_" in img or "arrow" in img or "kb_" in img or "row_" in img:
                            im.alpha_composite(Image.open(os.path.join(OUT, img)).convert("RGBA"), (int(x + sx), int(y + sy)))
                        elif "kb_plate" in img:
                            im.alpha_composite(Image.open(os.path.join(OUT, img)).convert("RGBA"), (int(x), int(y)))
                    elif sd["type"] == "Knob":
                        st = Image.open(os.path.join(OUT, sd["data"]["filmStrip"])).convert("RGBA")
                        n = sd["data"]["numFrames"]
                        fh = st.height // n
                        k = 30 if "gain" in sd["data"]["filmStrip"] else 20
                        im.alpha_composite(st.crop((0, fh * k, st.width, fh * (k + 1))), (int(x + sx), int(y + sy)))
                    elif sd["type"] == "Label":
                        d.text((x + sx + 6, y + sy + sh / 2), ROWS[1] if "row" in cd["type"] else "", font=M.ImageFont.truetype(M.MONO, 16), fill=(236, 240, 255), anchor="lm")
        os.makedirs(os.path.join(ROOT, "build", "preview"), exist_ok=True)
        im.convert("RGB").save(os.path.join(ROOT, "build", "preview", "%s.png" % p.name.lower()))


def main():
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    pages, tabs = [], []
    for fn, build in enumerate((build_play, build_filters, build_find)):
        p, c = build()
        pages.append(p)
        tabs.append(p.tab(save(c.im.resize((1280, 628), Image.LANCZOS).convert("RGB"), "bg_%s.png" % p.name.lower())))
    tui = {"pageData": {"version": 1, "componentDefinitions": {"version": 2, "importFiles": [], "localComponentDefinitions": overlay_defs() + DEFS},
                        "replacementStrings": [], "info": {"version": 1, "type": "CompleteDescription"}, "tabs": tabs}}
    open(os.path.join(OUT, "TUI.json"), "w").write(dump(tui) + "\n")
    open(os.path.join(OUT, "Q-Links.json"), "w").write(dump(qlinks_for(pages)) + "\n")
    if "--preview" in sys.argv:
        preview(pages, tabs)
    print("wrote", OUT, "-", len(tabs), "tabs,", len(os.listdir(OUT)), "files,", len(DEFS), "components")


if __name__ == "__main__":
    main()
