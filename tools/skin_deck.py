#!/usr/bin/env python3
"""Crate Digger's second skin, "Deck": the pages of docs/skin-mockups/v6-deck as TUI pages, for tools/make_tui.py (which merges them with the
sampler skin into one TUI.json, each set shown by the `skin` parameter, as Xenia does).
The art is tools/mockup_skin_deck.py's, drawn twice: the page without its moving parts (LIVE off) is the background, and every moving part is
drawn on its own small canvas with the same primitives: keys (on / off), knobs and the gain (film strips), the pitch fader's cap (a slider
thumb), the VU needles and the strobe light (film strips on level_l / level_r / play_state), the tone arm (a film strip on `arm`, the stylus
walking from the lead-in to the run-out), the label's paper (a film strip on `label_tint`, the cover's colour) and its print (a rotating
image on `platter`: the record turns while it plays). The text is the TUI's own (Titillium), coloured to sit on the art.
    build(T) -> [(page, background file)] for PLAY, FILTERS, FIND        T: the make_tui module (Page, entry, add_def, ...)"""
import math, os, sys
from contextlib import contextmanager
from PIL import Image, ImageDraw, ImageChops, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mockup_skin_deck as D
sys.path.insert(0, os.path.join(HERE, "..", "src", "sdk"))

AMBER, AMBER_DIM = "ffffb042", "ffc87428"
INK, CREAM = "ff2c221a", "ffeae8e0"
CEN = "horizontallyCentred verticallyCentred"
ARM_FRAMES = 32
CLEAR = "dk_clear.png"
TOUCH = "dk_touch.png"      # all but clear: a picture needs some alpha (>= 3) to take touches


@contextmanager
def canvas(w, h):
    """The mock-up primitives draw on a page-sized layer; for a small canvas they get a small page."""
    ow, oh = D.W, D.H
    D.W, D.H = w, h
    try:
        yield Image.new("RGBA", (w * D.S, h * D.S), (0, 0, 0, 0))
    finally:
        D.W, D.H = ow, oh


def warm(im):
    """The page's warm grade on a sprite (the background gets it with its vignette and grain in D.finish)."""
    rgb = ImageChops.multiply(im.convert("RGB"), Image.new("RGB", im.size, (255, 247, 234)))
    rgb.putalpha(im.getchannel("A"))
    return rgb


def sprite(box, pad, draw):
    """draw(im, shifted box) on a canvas round box (page coordinates) with pad; returns (1x image, x, y, w, h)."""
    x, y = int(box[0] - pad), int(box[1] - pad)
    w, h = int(math.ceil(box[2] + pad)) - x, int(math.ceil(box[3] + pad)) - y
    with canvas(w, h) as im:
        draw(im, (box[0] - x, box[1] - y, box[2] - x, box[3] - y))
    return warm(im.resize((w, h), Image.LANCZOS)), x, y, w, h


def strip(frames):
    w, h = frames[0].size
    st = Image.new("RGBA", (w, h * len(frames)), (0, 0, 0, 0))
    for i, f in enumerate(frames):
        st.paste(f, (0, i * h))
    return st


def full_frames(draws, scale=1.0):
    """Frames drawn at page coordinates on full-page layers, cropped to the union of what they draw. Returns (frames, x, y, w, h)."""
    ims = []
    for dr in draws:
        im = Image.new("RGBA", (D.W * D.S, D.H * D.S), (0, 0, 0, 0))
        dr(im)
        ims.append(im)
    box = None
    for im in ims:
        b = im.getchannel("A").getbbox()
        if b:
            box = b if box is None else (min(box[0], b[0]), min(box[1], b[1]), max(box[2], b[2]), max(box[3], b[3]))
    box = box or (0, 0, 2 * D.S, 2 * D.S)
    x0, y0 = box[0] // D.S, box[1] // D.S
    x1, y1 = -(-box[2] // D.S), -(-box[3] // D.S)
    w, h = x1 - x0, y1 - y0
    out = [warm(im.crop((x0 * D.S, y0 * D.S, x1 * D.S, y1 * D.S)).resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.LANCZOS))
           for im in ims]
    return out, x0, y0, w, h


class Deck:
    def __init__(self, T):
        self.T = T
        self.made = {}

    def save(self, im, name):
        return self.T.save(im, "dk_" + name)

    # ---- keys -----------------------------------------------------------------------------------------------------------------------------------
    def key(self, p, param, box, draw, pad=8, toggle=False, name=None):
        """A key bound to param: draw(im, box, on) draws it; a trigger's on image is pressed, a toggle's is lit."""
        nm = name or param
        if nm not in self.made:
            on, x, y, w, h = sprite(box, pad, lambda im, b: draw(im, b, True))
            off = sprite(box, pad, lambda im, b: draw(im, b, False))[0]
            self.made[nm] = (self.save(on, "key_%s_on.png" % nm), self.save(off, "key_%s_off.png" % nm), w, h)
            self.T.trig_def("dk_" + nm, self.made[nm][0], self.made[nm][1], w, h)
        on, off, w, h = self.made[nm]
        x, y = int(box[0] - pad), int(box[1] - pad)
        p.kids.append(self.T.entry(param, "dk_" + nm, {"version": 1, "handleName": "Data"}, "%d %d %d %d" % (x, y, w, h), remap=self.T.P(param), focus="Yes"))

    def tap(self, p, param, box, draw=None, pad=6, name=None):
        """A tap area (an arrow, a divider tab): one image, or none."""
        nm = name or param
        x, y = int(box[0] - pad), int(box[1] - pad)
        w, h = int(math.ceil(box[2] + pad)) - x, int(math.ceil(box[3] + pad)) - y
        if nm not in self.made:
            img = self.save(sprite(box, pad, draw)[0], "tap_%s.png" % nm) if draw else TOUCH
            self.T.tap_def("dk_" + nm, img, w, h)
            self.made[nm] = img
        # it takes focus: the MPC then honours the deck's "no Q-Link frame" (a tap that leaves focus elsewhere let the frame show)
        p.kids.append(self.T.entry(param, "dk_" + nm, {"version": 1, "handleName": "Data"}, "%d %d %d %d" % (x, y, w, h), remap=self.T.P(param),
                                   focus="Yes"))

    def deck_key(self, p, k):
        toggle = k in ("speed_33", "speed_45", "transport_sync", "skin", "pitch_x2")
        self.key(p, k, D.DECK_KEYS[k], lambda im, b, on: D.deck_key(im, k, lit=on and toggle, pressed=on and not toggle, box=b), toggle=toggle)

    def black_arrow(self, p, param, box, direction):
        self.tap(p, param, box, lambda im, b: D.key(im, b, "black", None, 11, arrow=direction), name="arrow_%s_%dx%d" % (direction, box[2] - box[0], box[3] - box[1]))

    # ---- knobs and the fader --------------------------------------------------------------------------------------------------------------------
    def knob(self, p, param, cx, cy, r, ink=(70, 56, 42)):
        nm = "knob%d" % r
        pad = 12
        size = 2 * (r + pad)
        if nm not in self.made:
            frames = [sprite((size / 2 - r, size / 2 - r, size / 2 + r, size / 2 + r), pad,
                             lambda im, b, f=f: D.knob(im, (b[0] + b[2]) / 2, (b[1] + b[3]) / 2, r, f / 63.0, dots=False, ink=ink))[0] for f in range(64)]
            img = self.save(strip(frames), nm + ".png")
            T = self.T
            T.add_def("dk_" + nm, T.component([T.entry("knob", "Knob", {"version": 3, "knobType": "FilmStrip", "filmStrip": img, "numFrames": 64, "invert": False,
                                                                       "dragOrientation": "Vertical", "handleName": "Data"}, "0 0 %d %d" % (size, size))],
                                              actions=[T.act("Mouse Down", "Q-Link"), T.act("Double Click", "Show Overlay", "knob overlay"),
                                                       T.act("Enter Pressed", "Show Overlay", "knob overlay")], background=T.bg("00000000")))
            self.made[nm] = size
        p.kids.append(self.T.entry(param, "dk_" + nm, {"version": 1, "handleName": "Data"}, "%d %d %d %d" % (cx - size / 2, cy - size / 2, size, size),
                                   remap=self.T.P(param), focus="Yes"))

    def pitch_fader(self, p):
        T = self.T
        if "pitch" not in self.made:
            cap = sprite((588 - 21, 400 - 12, 588 + 21, 400 + 12), 8, lambda im, b: D.fader_cap(im, (b[0] + b[2]) / 2, (b[1] + b[3]) / 2))[0]
            self.made["pitch"] = self.save(cap, "pitch_cap.png")
            T.add_def("dk_pitch", T.component([T.entry("fader", "Slider", {"version": 4, "sliderType": "TrackAndThumb", "direction": "Vertical",
                                                                         "thumbImage": self.made["pitch"], "thumbTrackVisible": False, "revealedImage": "",
                                                                         "revealType": "Normal", "handleName": "Data"}, "0 0 58 252")],
                                              actions=[T.act("Mouse Down", "Q-Link"), T.act("Double Click", "Show Overlay", "knob overlay"),
                                                       T.act("Enter Pressed", "Show Overlay", "knob overlay")], background=T.bg("00000000")))
        # the cap's centre runs from 302 (+8 %) to 514 (-8 %): the thumb travels the bounds less its own height (40)
        p.kids.append(T.entry("pitch", "dk_pitch", {"version": 1, "handleName": "Data"}, "559 282 58 252", remap=T.P("pitch"), focus="Yes"))

    def fader(self, p, param, cx, y0, y1):
        """A long vertical fader on a list (a stepper): the pitch fader's cap in a slot of the console (D.fader_slot)."""
        T = self.T
        h = int(y1 - y0 + 20)    # the cap (40 tall with its shadow) travels the bounds less its height: centre y0 + 10 .. y1 - 10
        nm = "dk_fader%d" % h
        if nm not in self.made:
            cap = sprite((588 - 21, 400 - 12, 588 + 21, 400 + 12), 8, lambda im, b: D.fader_cap(im, (b[0] + b[2]) / 2, (b[1] + b[3]) / 2))[0]
            img = self.made.get("pitch") or self.save(cap, "pitch_cap.png")
            self.made["pitch"] = img
            T.add_def(nm, T.component([T.entry("fader", "Slider", {"version": 4, "sliderType": "TrackAndThumb", "direction": "Vertical",
                                                                   "thumbImage": img, "thumbTrackVisible": False, "revealedImage": "",
                                                                   "revealType": "Normal", "handleName": "Data"}, "0 0 58 %d" % h)],
                                      actions=[T.act("Mouse Down", "Q-Link"), T.act("Double Click", "Show Overlay", "knob overlay"),
                                               T.act("Enter Pressed", "Show Overlay", "knob overlay")], background=T.bg("00000000")))
            self.made[nm] = True
        p.kids.append(T.entry(param, nm, {"version": 1, "handleName": "Data"}, "%d %d 58 %d" % (cx - 29, y0 - 10, h), remap=T.P(param), focus="Yes"))

    # ---- film strips: arm, strobe, VU, label ----------------------------------------------------------------------------------------------------
    def film(self, p, param, name, frames, x, y, w, h):
        img = self.save(strip(frames), name + ".png")
        p.kids.append(self.T.entry(name, "Image", {"version": 2, "imageType": "FilmStrip", "colour": "0", "image": img, "numFrames": len(frames),
                                                   "handleName": "Data"}, "%d %d %d %d" % (x, y, w, h), remap=self.T.P(param)))

    def arm(self, p):
        if "arm" not in self.made:
            def rot_for(radius):
                lo, hi = -0.7, 0.7
                f = lambda rot: math.hypot(*(a - b for a, b in zip(D.stylus_tip(rot), (D.CX, D.CY)))) - radius
                flo = f(lo)
                for _ in range(40):
                    mid = (lo + hi) / 2
                    if (f(mid) > 0) == (flo > 0):
                        lo, flo = mid, f(mid)
                    else:
                        hi = mid
                return (lo + hi) / 2
            radii = [D.R_VINYL - 9 - (D.R_VINYL - 9 - (D.R_LABEL + 18)) * i / (ARM_FRAMES - 1) for i in range(ARM_FRAMES)]
            rots = [rot_for(r) for r in radii]
            self.made["arm"] = full_frames([lambda im, r=r: D.arm_parts(im, r) for r in rots])
        frames, x, y, w, h = self.made["arm"]
        # a knob, not a picture: drag it (up: towards the label) and the needle drops there (CrateDiggerPlugin.cpp, armMoved)
        img = self.save(strip(frames), "arm.png")
        T = self.T
        if "dk_tonearm" not in T.DEFKEYS:   # wrapped in a component of the deck's own, so a drag leaves no Q-Link frame (build)
            T.add_def("dk_tonearm", T.component([T.entry("tonearm", "Knob", {"version": 3, "knobType": "FilmStrip", "filmStrip": img,
                                                                             "numFrames": len(frames), "invert": False, "dragOrientation": "Vertical",
                                                                             "handleName": "Data"}, "0 0 %d %d" % (w, h))],
                                                actions=[T.act("Mouse Down", "Q-Link")], background=T.bg("00000000")))
        p.kids.append(T.entry("tonearm", "dk_tonearm", {"version": 1, "handleName": "Data"}, "%d %d %d %d" % (x, y, w, h), remap=T.P("arm"),
                              focus="Yes"))

    def strobe(self, p):
        if "strobe" not in self.made:
            # play_state 0..10: 1 = streaming lights the strobe; the other states leave it dark
            lit = full_frames([lambda im: D.strobe_glow(im)])
            frames, x, y, w, h = lit
            dark = Image.new("RGBA", frames[0].size, (0, 0, 0, 0))
            self.made["strobe"] = ([dark, frames[0]] + [dark] * 9, x, y, w, h)
        frames, x, y, w, h = self.made["strobe"]
        self.film(p, "play_state", "strobe", frames, x, y, w, h)

    def pitch_led(self, p):
        """The fader's zero LED: a film strip on `pitch` (201 frames over -1..1), lit only in the middle frame: with the pitch at 0 (the plugin
        snaps the fader to 0 within +-0.012 of it, a centre click, so it can get back there)."""
        if "pitch_led" not in self.made:
            cx, cy = D.PITCH_LED
            lit = sprite((cx - 4, cy - 4, cx + 4, cy + 4), 6, lambda im, b: D.pitch_led(im, True, ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)))
            dark = Image.new("RGBA", lit[0].size, (0, 0, 0, 0))
            self.made["pitch_led"] = ([dark] * 100 + [lit[0]] + [dark] * 100,) + lit[1:]
        frames, x, y, w, h = self.made["pitch_led"]
        self.film(p, "pitch", "pitch_led", frames, x, y, w, h)

    def vu(self, p):
        for param, box in (("level_l", D.VU_L), ("level_r", D.VU_R)):
            nm = "vu_" + param
            if nm not in self.made:
                fr = [sprite(box, 2, lambda im, b, f=f: D.vu_needle(im, b, f / 10.0)) for f in range(11)]
                self.made[nm] = ([f[0] for f in fr],) + fr[0][1:]
            frames, x, y, w, h = self.made[nm]
            self.film(p, param, nm, frames, x, y, w, h)

    ART_SIDE, ART_CELL = 16, 19          # the cover: 16 x 16 dots of 19 px on the label's display (CrateDiggerPlugin.cpp, ART_SIDE)
    MASK = "dk_label_mask.png"           # the vinyl round the label, cut from the finished background (build)

    @classmethod
    def art_box(cls):
        side = cls.ART_SIDE * cls.ART_CELL
        return int(D.CX - side / 2), int(D.CY - side / 2), side

    @classmethod
    def dot(cls, col):
        """One cell of the cover as a lit dot on the display's dark glass: the brighter the colour, the bigger the dot (black: none)."""
        k = 8
        n = cls.ART_CELL * k
        v = max(col) / 255.0
        im = Image.new("RGBA", (n, n), (0, 0, 0, 0))
        if v > 0:
            r = n / 2 * (0.42 + 0.54 * v)
            ImageDraw.Draw(im).ellipse((n / 2 - r, n / 2 - r, n / 2 + r, n / 2 + r), fill=tuple(col) + (255,))
            hl = Image.new("RGBA", (n, n), (0, 0, 0, 0))   # a soft highlight to the upper left: a lens, not a flat print
            ImageDraw.Draw(hl).ellipse((n / 2 - r * 0.7, n / 2 - r * 0.75, n / 2 + r * 0.1, n / 2 + r * 0.05), fill=(255, 255, 255, 60))
            im.alpha_composite(hl.filter(ImageFilter.GaussianBlur(n / 14)))
            m = Image.new("L", (n, n), 0)
            ImageDraw.Draw(m).ellipse((n / 2 - r, n / 2 - r, n / 2 + r, n / 2 + r), fill=255)
            im.putalpha(ImageChops.multiply(im.getchannel("A"), m))
        return im.resize((cls.ART_CELL, cls.ART_CELL), Image.LANCZOS)

    def label(self, p):
        """The centre label: the record's cover as 16 x 16 halftone dots (each a film strip of 512 colours on art_N) on the paper, cut round
        by the vinyl round it; the print turning with the record; the display's smoked glass over the middle (the cover shows through)."""
        T = self.T
        x0, y0, side = self.art_box()
        if "label" not in self.made:
            sw = []
            for i in range(512):
                col = (((i >> 6) & 7) * 255 // 7, ((i >> 3) & 7) * 255 // 7, (i & 7) * 255 // 7)
                sw.append(self.dot(col))
            R = D.R_LABEL + 2
            size = 2 * R
            with canvas(size, size) as im:
                D.label_band(im, c=(R, R))   # the paper ring, opaque: the dots show only inside it, on the display
                D.label_print(im, c=(R, R))
            printed = self.save(warm(im.resize((size, size), Image.LANCZOS)), "label_print.png")
            gs = 2 * (D.R_DISP + 6)
            with canvas(gs, gs) as im:
                D.display_glass(im, c=(gs / 2, gs / 2), alpha=125)
            glass = self.save(warm(im.resize((gs, gs), Image.LANCZOS)), "display_glass.png")
            self.made["label"] = (self.save(strip(sw), "art_swatches.png"), printed, glass, size, gs)
        swatches, printed, glass, size, gs = self.made["label"]
        for i in range(self.ART_SIDE * self.ART_SIDE):
            r, c = divmod(i, self.ART_SIDE)
            p.kids.append(T.entry("art %d" % i, "Image", {"version": 2, "imageType": "FilmStrip", "colour": "0", "image": swatches, "numFrames": 512,
                                                         "handleName": "Data"}, "%d %d %d %d" % (x0 + c * self.ART_CELL, y0 + r * self.ART_CELL,
                                                                                                 self.ART_CELL, self.ART_CELL), remap=T.P("art_%d" % i)))
        p.kids.append(T.entry("label mask", "Image", {"version": 2, "imageType": "Regular", "colour": "0", "image": self.MASK},
                              "%d %d %d %d" % (x0, y0, side, side)))
        R = size // 2
        if "dk_platter" not in T.DEFKEYS:   # only turned by the plugin: it ignores touches
            T.add_def("dk_platter", T.component([T.entry("label print", "Knob", {"version": 4, "knobType": "RotatingImage", "foregroundImage": printed,
                                                                                 "backgroundImage": CLEAR, "imageScale": 1.0, "dragOrientation": "Vertical",
                                                                                 "handleName": "Data"}, "0 0 %d %d" % (size, size))],
                                                ignore=True, background=T.bg("00000000")))
        p.kids.append(T.entry("label print", "dk_platter", {"version": 1, "handleName": "Data"}, "%d %d %d %d" % (D.CX - R, D.CY - R, size, size),
                              remap=T.P("platter")))
        p.kids.append(T.entry("display glass", "Image", {"version": 2, "imageType": "Regular", "colour": "0", "image": glass},
                              "%d %d %d %d" % (D.CX - gs / 2, D.CY - gs / 2, gs, gs)))
        cx, cy, rd = D.CX, D.CY, D.R_DISP
        wide = lambda dy: 2 * math.sqrt(rd * rd - dy * dy) - 12
        p.lcd_text("status", cx - wide(86) / 2, cy - 86, wide(86), size=16, h=26, just=CEN, colour=AMBER)
        p.lcd_text("now_playing", cx - wide(46) / 2, cy - 46, wide(46), size=20, h=30, just=CEN, colour=AMBER)
        p.lcd_text("time", cx - 100, cy + 54, 200, size=50, h=64, just=CEN, colour=AMBER)

    def label_mask(self, bg):
        """The vinyl round the label (from the finished background), clear inside the label's circle, with the label's edge."""
        x0, y0, side = self.art_box()
        sq = bg.convert("RGBA").crop((x0, y0, x0 + side, y0 + side)).resize((side * 4, side * 4), Image.LANCZOS)
        m = Image.new("L", sq.size, 255)
        c, r = side * 2, (D.R_DISP + 3) * 4
        ImageDraw.Draw(m).ellipse((c - r, c - r, c + r, c + r), fill=0)
        sq.putalpha(m)
        d = ImageDraw.Draw(sq, "RGBA")
        d.ellipse((c - r, c - r, c + r, c + r), outline=(0, 0, 0, 150), width=4)
        d.ellipse((c - r + 4, c - r + 4, c + r - 4, c + r - 4), outline=(255, 255, 255, 40), width=3)
        self.T.save(sq.resize((side, side), Image.LANCZOS), self.MASK)

    # ---- the pages ----------------------------------------------------------------------------------------------------------------------------
    def deck_parts(self, p):
        self.no_qlink_frame(p)
        self.label(p)
        self.strobe(p)
        self.arm(p)
        self.pitch_led(p)      # under the fader, so a touch there still moves the fader
        self.pitch_fader(p)
        self.key(p, "pitch_reset", (528, 528, 546, 546), lambda im, b, on: D.reset_button(im, (b[0] + b[2]) / 2, (b[1] + b[3]) / 2, pressed=on), pad=6)
        for k in D.DECK_KEYS:
            self.deck_key(p, k)

    def no_qlink_frame(self, p):
        """The deck look draws no Q-Link frame (the frames are the tab's, placed for the sampler look): an empty component that hides them
        while it is shown, and it is shown only in the deck look."""
        T = self.T
        if "noq" not in self.made:
            T.add_def("dk_noq", {"version": 4, "actions": [], "backgroundData": T.bg("00000000"), "ignoreMousePresses": True,
                                 "disableCoarseDataWheel": False, "hideQLinkBounds": True, "componentsData": []})
            self.made["noq"] = True
        p.kids.append(T.entry("no q-link frame", "dk_noq", {"version": 1, "handleName": "Data"}, "0 0 1280 628"))

    def crate_parts(self, p, search_param, with_amp=False):
        x0, y0, x1, y1 = D.STATUS_BOX       # along the bottom, on the amp (PLAY) or its slim twin
        p.lcd_text("search_status", x0 + 18, (y0 + y1) / 2, x1 - x0 - 30, size=18, h=30, colour=AMBER)
        self.key(p, search_param, D.SEARCH_BOX, lambda im, b, on: self.red_key(im, b, on), name="search")
        if with_amp:   # the amp is on PLAY only
            self.vu(p)
            self.knob(p, "gain", D.GAIN_KNOB[0], D.GAIN_KNOB[1], D.GAIN_KNOB[2], ink=(70, 58, 44))

    @staticmethod
    def red_key(im, b, pressed):
        D.key(im, b, "red", "SEARCH", 18, r=5)
        if pressed:
            ImageDraw.Draw(im, "RGBA").rounded_rectangle(D.B((b[0] + 1, b[1] + 1, b[2] - 1, b[3] - 3)), D.s(4), fill=(0, 0, 0, 60))

    def row_def(self, light=False):
        """A result row: the playing one lit, its text in the sleeve's ink (cream on the dark sleeves, D.SLEEVES)."""
        T = self.T
        w, h = 592, 49
        key = "dk_row_lt" if light else "dk_row"
        if key not in self.made:
            with canvas(w, h) as im:
                d = ImageDraw.Draw(im, "RGBA")
                L = Image.new("RGBA", im.size, (0, 0, 0, 0))
                ImageDraw.Draw(L).rectangle((0, 0, w * D.S, h * D.S), outline=D.AMBER + (200,), width=D.s(5))
                from PIL import ImageFilter
                im.alpha_composite(L.filter(ImageFilter.GaussianBlur(D.s(3))))
                d.line(D.B((2, 1, w - 2, 1)), fill=D.AMBER, width=D.s(2))
            on = self.save(warm(im.resize((w, h), Image.LANCZOS)), "row_on.png")
            T.add_def(key, T.component([
                T.entry("Button", "Button", {"version": 1, "onImage": on, "offImage": CLEAR, "buttonId": 1, "numButtonsInGroup": 1, "handleName": "Data"},
                        "0 0 %d %d" % (w, h)),
                T.entry("Value", "Label", {"version": 1, "textStyle": T.text_style(h=T.th(17), colour=CREAM if light else INK,
                                                                                    just="left verticallyCentred", case="Original"),
                                           "type": "Value", "handleName": "Data"}, "46 0 %d %d" % (w - 56, h)),
            ], actions=[T.act("Mouse Down", "Toggle Switch"), T.act("Enter Pressed", "Toggle Switch")]))
            self.made[key] = (w, h)
        return key, w, h

    def page_play(self):
        T = self.T
        p = T.Page("PLAY", 0)
        D.LIVE = False
        im = Image.new("RGBA", (D.W * D.S, D.H * D.S), (20, 18, 17, 255))
        D.wall(im)
        D.deck(im)
        D.crate_back(im)
        D.divider_tab(im, 664, 784, 12, "PAGE", "l", seed=71)
        D.divider_tab(im, 880, 1016, 16, "", seed=72)
        D.divider_tab(im, 1112, 1232, 12, "PAGE", "r", seed=73)
        D.sleeves(im)
        D.crate_front(im)
        self.deck_parts(p)
        self.crate_parts(p, "search", with_amp=True)
        self.tap(p, "page_prev", (664, 12, 784, 62))
        self.tap(p, "page_next", (1112, 12, 1232, 62))
        p.lcd_text("page", 884, 33, 128, size=14, h=24, just=CEN, handle="Text", colour=INK)
        for i in range(8):
            rk, w, h = self.row_def(light=D.SLEEVES[i][3] == D.CREAM)
            p.kids.append(T.entry("result %d" % (i + 1), rk, {"version": 1, "handleName": "Data"}, "654 %d %d %d" % (D.ROW0 + i * D.ROW_H, w, h),
                                  remap=T.P("result_%d" % (i + 1)), focus="Yes" if i == 0 else "No"))
        D.LIVE = True
        return p, im

    def page_filters(self):
        T = self.T
        p = T.Page("FILTERS", 1)
        D.LIVE = False
        im = Image.new("RGBA", (D.W * D.S, D.H * D.S), (20, 18, 17, 255))
        D.wall(im)
        D.deck(im)
        D.filters_console(im)
        for i, (num, name, value, v) in enumerate(D.FILTERS):
            cx = D.FILTER_X[i]
            key = name.lower()
            # two lines tall: the MPC wraps a value that is too wide for one (FOLK, WORLD, & COUNTRY) instead of cutting it short
            p.lcd_text(key, cx - 56, 118, 112, size=17, h=64, just=CEN, handle="Text", colour=AMBER)
            self.fader(p, key, cx, D.FADER_Y0, D.FADER_Y1)   # up the list: the fader's top is the list's end
            self.black_arrow(p, key + "_next", (cx - 44, 180, cx + 44, 226), "u")
            self.black_arrow(p, key + "_prev", (cx - 44, 472, cx + 44, 518), "d")
        self.deck_parts(p)
        self.crate_parts(p, "search")
        D.LIVE = True
        return p, im

    def page_find(self):
        T = self.T
        p = T.Page("FIND", 2)
        D.LIVE = False
        im = Image.new("RGBA", (D.W * D.S, D.H * D.S), (20, 18, 17, 255))
        D.wall(im)
        D.deck(im)
        D.find_console(im)
        for name, param, box in D.FIND_SRC:   # the input selector: the lit key is the source
            self.key(p, param, box, lambda m, b, on, name=name: self.source_key(m, b, name, on), toggle=True)
        for i, (x0, x1) in enumerate(D.FIND_COLS):   # the source's column on the display glows (source: 0 DISCOGS, 1 CHANNEL, 2 YOUTUBE)
            src = (0, 2, 1)[i]
            lit = Image.new("RGBA", (x1 - x0 + 8, D.FIND_VFD[3] - D.FIND_VFD[1] - 12), (0, 0, 0, 0))
            ImageDraw.Draw(lit).rounded_rectangle((0, 0, lit.width - 1, lit.height - 1), 3, fill=(255, 150, 40, 34), outline=(255, 176, 66, 110))
            p.kids.append(T.entry("source %d" % i, "Image", {"version": 2, "imageType": "Regular", "colour": "0", "image": self.save(lit, "srclit_%d.png" % i)},
                                  "%d %d %d %d" % (x0 - 4, D.FIND_VFD[1] + 6, lit.width, lit.height), ind=["IndexedEnabling/%d/3/%s" % (src, T.P("source"))]))
        for j, key in enumerate(("genre", "style", "decade", "country")):
            p.lcd_text(key, 736, 138 + j * 20, 104, size=13, h=20, handle="Text", colour=AMBER)
        p.lcd_text("music", 878, 140, 152, size=18, h=28, just=CEN, handle="Text", colour=AMBER)
        for cx, cap, key in D.FIND_FADERS:   # the readout straight above its fader
            p.lcd_text(key, cx - 48, 190, 96, size=18, h=28, just=CEN, handle="Text", colour=AMBER)
            self.fader(p, key, cx, *D.FIND_FADER_Y)
        p.lcd_text("channel", 1070, 148, 172, size=14, h=24, handle="Text", colour=AMBER)
        for cx, cap, key in D.FIND_KNOBS:
            self.knob(p, key, cx, 312, 38)
            self.black_arrow(p, key + "_prev", (cx - 58, 362, cx - 3, 406), "l")
            self.black_arrow(p, key + "_next", (cx + 3, 362, cx + 58, 406), "r")
        self.key(p, "music_btn", D.FIND_MUSIC, lambda m, b, on: self.music_key(m, b, on), toggle=True)
        x0, y0, x1, y1 = D.FIND_TEXT
        p.lcd_text("query", x0 + 60, (y0 + y1) / 2, x1 - x0 - 130, size=22, h=34, colour=AMBER)
        self.tap(p, "keys", D.FIND_TEXT, pad=0, name="type_panel")   # the text panel is the key: tap to type
        self.key(p, "skin", D.SKIN_BOX, lambda m, b, on: D.deck_key(m, "skin", lit=on, box=b), toggle=True)
        self.deck_parts(p)
        self.crate_parts(p, "find_search")
        self.T.add_keyboard(p)
        D.LIVE = True
        return p, im

    @staticmethod
    def music_key(im, b, on):
        """MUSIC ONLY: a silver key level with the length knobs, its lamp at the corner."""
        D.key(im, b, "silver", None, lamp=on)
        D.text(im, ((b[0] + b[2]) / 2 - 6, (b[1] + b[3]) / 2 - 1), "MUSIC ONLY", 13, (36, 36, 34), spacing=1.0)

    @staticmethod
    def source_key(im, b, name, on):
        """An amp's input selector key: silver, its name, an amber lamp lit when it is the source."""
        D.key(im, b, "silver", None, lamp=on)
        D.text(im, ((b[0] + b[2]) / 2 - 6, (b[1] + b[3]) / 2 - 1), name, 15, (36, 36, 34), spacing=1.2)

    @staticmethod
    def black_text_key(im, b, label, pressed):
        D.key(im, b, "black", label, 13)
        if pressed:
            ImageDraw.Draw(im, "RGBA").rounded_rectangle(D.B((b[0] + 1, b[1] + 1, b[2] - 1, b[3] - 3)), D.s(4), fill=(0, 0, 0, 70))

    @staticmethod
    def bin_sign(im, b, name, on):
        """A record shop's bin sign, the source key: lit amber when it is the source."""
        x0, y0, x1, y1 = b
        D.soft_shadow(im, b, 5, off=(3, 5), blur=5, alpha=200)
        if on:
            L = Image.new("RGBA", im.size, (0, 0, 0, 0))
            ImageDraw.Draw(L).rounded_rectangle(D.B(b), D.s(6), fill=D.AMBER + (190,))
            from PIL import ImageFilter
            im.alpha_composite(L.filter(ImageFilter.GaussianBlur(D.s(8))))
        D.grad(im, b, (34, 31, 28), (15, 14, 13), r=4)
        ImageDraw.Draw(im, "RGBA").rounded_rectangle(D.B((x0 + 4, y0 + 4, x1 - 4, y1 - 4)), D.s(3), outline=(232, 222, 200, 110), width=D.s(1))
        D.dust(im, b, 80, light=True, seed=int(x0), alpha=(20, 70))
        if on:
            D.glow_text(im, ((x0 + x1) / 2, (y0 + y1) / 2), name, 18, D.AMBER, blur=4)
        else:
            D.worn_text(im, ((x0 + x1) / 2, (y0 + y1) / 2), name, 18, (224, 214, 192), spacing=1.5, wear=0.25, seed=len(name))


def q_proxies(T, p, keys):
    """The tab's Q-Linked parameters the deck shows no control for (PAGE's knob, SOURCE, MUSIC, GAIN off PLAY): an invisible stand-in
    for each, so a Q-Link turned on one lands on a deck component, which keeps the Q-Link frame hidden."""
    bound = {m["value"] for e in p.kids if e["componentData"]["type"] not in ("Label", "Image") for m in e["handle remapping"]["map"]}
    if "dk_qproxy" not in T.DEFKEYS:
        T.add_def("dk_qproxy", T.component([T.entry("proxy", "Image", {"version": 2, "imageType": "Regular", "colour": "0", "image": CLEAR,
                                                                         "handleName": "Data"}, "0 0 2 2")], ignore=True, background=T.bg("00000000")))
    for k in keys:
        if T.P(k) not in bound:
            p.kids.insert(0, T.entry("q " + k, "dk_qproxy", {"version": 1, "handleName": "Data"}, "0 0 2 2", remap=T.P(k), focus="Yes"))


def build(T, sampler_pages=()):
    """The deck pages: [(page, background file name)], in tab order."""
    dk = Deck(T)
    T.save(Image.new("RGBA", (8, 8), (0, 0, 0, 0)), CLEAR)
    T.save(Image.new("RGBA", (8, 8), (0, 0, 0, 4)), TOUCH)
    out = []
    for fn in (dk.page_play, dk.page_filters, dk.page_find):
        p, im = fn()
        bg = D.finish(im.resize((D.W, D.H), Image.LANCZOS))
        if not out:
            dk.label_mask(bg)   # the deck is the same on every tab: one mask
        out.append((p, T.save(bg, "dk_bg_%s.png" % p.name.lower())))
    # no Q-Link frame in the deck look: the frames are the tab's (placed for the sampler look), and the MPC hides them while a component
    # that asks it to is in use, so every deck-only component asks (the sampler's own components don't)
    for sp, (p, _) in zip(sampler_pages, out):
        q_proxies(T, p, [k for row in sp.qrows[:4] for k in row])
    import copy
    defs = {d["key"]: d["value"] for d in T.DEFS}
    for p, _ in out:   # the deck's own copies of anything it borrows from the sampler (the popup keyboard), so they hide the frame too
        for e in p.kids:
            typ = e["componentData"]["type"]
            if typ.startswith("cd_"):
                if "dk_" + typ not in T.DEFKEYS:
                    T.add_def("dk_" + typ, copy.deepcopy(defs[typ]))
                e["componentData"]["type"] = "dk_" + typ
    for d in T.DEFS:
        if d["key"].startswith("dk_"):
            v = d["value"]
            d["value"] = {"version": 4, "actions": v["actions"], "backgroundData": v["backgroundData"], "ignoreMousePresses": v["ignoreMousePresses"],
                          "disableCoarseDataWheel": v["disableCoarseDataWheel"], "hideQLinkBounds": True, "componentsData": v["componentsData"]}
    return out


def preview(T, deck):
    """Compose the deck pages offline as the MPC would (art, components, sample text): build/preview/deck_<tab>.png."""
    from PIL import ImageFont
    defs = {d["key"]: d["value"] for d in T.DEFS}
    kb = "Parameter %d" % T.LOCK.index("kb")
    sample = dict(T.SAMPLE, page="PAGE 1 / 2")
    cover = None
    if os.environ.get("DECK_PREVIEW_COVER"):    # a picture to show on the label, as the plugin would (16 x 16 cells)
        src = Image.open(os.environ["DECK_PREVIEW_COVER"]).convert("RGB")
        w = min(src.size)
        cover = src.crop(((src.width - w) // 2, (src.height - w) // 2, (src.width + w) // 2, (src.height + w) // 2)).resize((16, 16), Image.BOX)
    for p, bgname in deck:
        im = Image.open(os.path.join(T.OUT, bgname)).convert("RGBA")
        d = ImageDraw.Draw(im)

        def paste(name, x, y, w, h, frame=0, n=1):
            st = Image.open(os.path.join(T.OUT, name)).convert("RGBA")
            if n > 1:
                fh = st.height // n
                st = st.crop((0, fh * frame, st.width, fh * (frame + 1)))
            im.alpha_composite(st.resize((int(w), int(h)), Image.LANCZOS), (int(x), int(y)))

        def say(txt, ts, x, y, w, h):
            f = ImageFont.truetype(D.M.TITB, max(6, int(float(ts["font"]["height"]) * T.TUI_PX)))
            c = ts["colour"]
            col = tuple(int(c[i:i + 2], 16) for i in (2, 4, 6))
            cen = "horizontallyCentred" in ts["justification"]
            d.text((x + w / 2 if cen else x + 2, y + h / 2), txt, font=f, fill=col, anchor="mm" if cen else "lm")

        for e in p.kids:
            cd, data = e["componentData"], e["componentData"]["data"]
            x, y, w, h = [float(v) for v in e["bounds"]["bounds"].split()]
            if any(kb in i for i in e["bounds"].get("additionalInvalidatingHandles", [])):
                continue                                           # the popup keyboard: hidden
            rp = e["handle remapping"]["map"][0]["value"] if e["handle remapping"]["map"] else ""
            key = T.LOCK[int(rp.split()[1])] if rp else ""
            if cd["type"] == "Image" and cd["name"].startswith("art "):
                i = int(cd["name"].split()[1])
                c = cover.getpixel((i % 16, i // 16)) if cover else (232, 221, 196)
                frame = (((c[0] * 7 + 127) // 255) << 6) | (((c[1] * 7 + 127) // 255) << 3) | ((c[2] * 7 + 127) // 255)
                paste(data["image"], x, y, w, h, frame, data["numFrames"])
            elif cd["type"] == "Image":
                n = data.get("numFrames", 1)
                frame = {"arm": 5, "strobe": 1, "label paper": 3, "vu_level_l": 8, "vu_level_r": 7}.get(cd["name"], 0)
                paste(data["image"], x, y, w, h, min(frame, n - 1), n)
            elif cd["type"] == "Knob" and data.get("knobType") == "FilmStrip":
                paste(data["filmStrip"], x, y, w, h, data["numFrames"] * 2 // 5, data["numFrames"])
            elif cd["type"] == "Knob":
                paste(data["foregroundImage"], x, y, w, h)
            elif cd["type"] == "Label":
                say(sample.get(key, key), data["textStyle"], x, y, w, h)
            elif cd["type"] in defs:
                for sub in defs[cd["type"]]["componentsData"]:
                    sd, dd = sub["componentData"], sub["componentData"]["data"]
                    sx, sy, sw, sh = [float(v) for v in sub["bounds"]["bounds"].split()]
                    if sd["type"] == "Button":
                        lit = key in ("speed_33", "transport_sync", "skin", "source_youtube", "result_1")
                        paste(dd["onImage"] if lit else dd["offImage"], x + sx, y + sy, sw, sh)
                    elif sd["type"] == "Knob" and "filmStrip" in dd:
                        paste(dd["filmStrip"], x + sx, y + sy, sw, sh, 40 if key == "gain" else 5 if key == "arm" else 22, dd["numFrames"])
                    elif sd["type"] == "Knob":
                        paste(dd["foregroundImage"], x + sx, y + sy, sw, sh)
                    elif sd["type"] == "Slider":
                        th = Image.open(os.path.join(T.OUT, dd["thumbImage"]))
                        v = 0.42
                        paste(dd["thumbImage"], x + (sw - th.width) / 2, y + (1 - v) * (sh - th.height), th.width, th.height)
                    elif sd["type"] == "Label":
                        txt = T.ROWS[int(cd["name"].split()[-1]) - 1] if key.startswith("result_") else ""
                        say(txt, dd["textStyle"], x + sx, y + sy, sw, sh)
        os.makedirs(os.path.join(T.ROOT, "build", "preview"), exist_ok=True)
        im.convert("RGB").save(os.path.join(T.ROOT, "build", "preview", "deck_%s.png" % p.name.lower()))
