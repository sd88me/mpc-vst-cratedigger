#!/usr/bin/env python3
"""Draws the GAIN fader's two pictures into images/: fader_base.png (the recessed slot and its engraved scale, stays still)
and fader_cap.png (the bakelite cap with grip ridges and a cast shadow, the part that slides).

layout.conf: slider_v w=110 h=146 ... base=images/fader_base.png img=images/fader_cap.png. The skin tool stretches the base over
the slider's w x h and moves the cap (as wide as the slider, 48 tall here) from the top (full) to the bottom (zero), so the
slot below is drawn between the cap's centre line at either end of that travel. Gain runs 0..2, unity in the middle.
Needs Pillow and Titillium Web SemiBold (OFL): FONT=<path>, e.g. mpc-vst-plugins/tools/html_art/fonts/TitilliumWeb-SemiBold.ttf.
Run:  FONT=... python3 vst/make_fader.py   (the build never runs it).
"""
import os
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.environ["FONT"]
S = 4                              # supersampling
W, H = 110, 146                    # the slider box in layout.conf
CW, CH = 110, 48                   # the cap picture (its width is the slider's)
CAP_MID = 21                       # the cap's centre line, from its picture's top (the body is 3..39, shadow below)
TOP, BOT = CAP_MID, H - CH + CAP_MID   # slot ends: the centre line at full and at zero
CX = W // 2


class Over:
    """Draws like ImageDraw but alpha-composites every shape (ImageDraw's own RGBA blend also blends the alpha channel, which
    leaves translucent holes in an opaque cap)."""

    def __init__(self, im):
        self.im = im

    def __getattr__(self, name):
        def draw(*a, **k):
            layer = Image.new("RGBA", self.im.size, (0, 0, 0, 0))
            getattr(ImageDraw.Draw(layer), name)(*a, **k)
            self.im.alpha_composite(layer)
        return draw


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def vgrad(w, h, stops):
    """A w x h RGBA vertical gradient through (position 0..1, rgb) stops."""
    im = Image.new("RGBA", (w, h))
    d = ImageDraw.Draw(im)
    for y in range(h):
        t = y / max(1, h - 1)
        for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
            if t0 <= t <= t1:
                d.line((0, y, w, y), fill=lerp(c0, c1, (t - t0) / max(1e-9, t1 - t0)) + (255,))
                break
    return im


def rr_mask(size, box, r):
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).rounded_rectangle(box, r, fill=255)
    return m


def base():
    im = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
    # the slot: a lip catching light below/right, a dark well with its own inner shadow top-left, a faint steel rail
    box = ((CX - 7) * S, (TOP - 4) * S, (CX + 7) * S, (BOT + 4) * S)
    sz = im.size
    lip = rr_mask(sz, (box[0] + S, box[1] + S, box[2] + S, box[3] + S), 7 * S)
    im.alpha_composite(Image.composite(Image.new("RGBA", sz, (255, 255, 255, 120)), Image.new("RGBA", sz, (0, 0, 0, 0)), lip))
    well = rr_mask(sz, box, 7 * S)
    fill = vgrad(sz[0], sz[1], [(0, (30, 25, 18)), (1, (46, 40, 31))])
    im.alpha_composite(Image.composite(fill, Image.new("RGBA", sz, (0, 0, 0, 0)), well))
    shade = ImageChops.subtract(well, ImageChops.offset(well, 2 * S, 3 * S)).filter(ImageFilter.GaussianBlur(1.5 * S))
    sh = Image.new("RGBA", sz, (0, 0, 0, 0))
    sh.paste((0, 0, 0, 175), mask=ImageChops.multiply(shade, well))
    im.alpha_composite(sh)
    d = Over(im)
    d.rounded_rectangle(((CX + 3) * S, (TOP + 2) * S, (CX + 4) * S, (BOT - 2) * S), S // 2, fill=(255, 255, 255, 28))
    d.rounded_rectangle(((CX - 1) * S, (TOP + 2) * S, (CX + 1) * S, (BOT - 2) * S), S // 2, fill=(86, 76, 58, 255))
    # the engraved scale: dark ink with a light lip underneath
    ink, lipc = (43, 40, 34, 225), (255, 255, 255, 100)
    font = ImageFont.truetype(FONT, 11 * S)

    def y_at(t):
        return BOT - (BOT - TOP) * t

    for i in range(21):
        t = i / 20
        ln = 14 if i % 10 == 0 else 9 if i % 5 == 0 else 5
        y = y_at(t) * S
        x1 = (CX - 11) * S
        for off, c in ((S * 0.8, lipc), (0, ink)):
            d.line((x1 - ln * S, y + off, x1, y + off), fill=c, width=max(1, round(S * 0.9)))
    for t, txt in ((0, "0"), (0.5, "1"), (1, "2")):
        y = y_at(t) * S
        for off, c in ((S * 0.8, lipc), (0, ink)):
            d.text(((CX + 14) * S, y + off), txt, font=font, fill=c, anchor="lm")
    # "GAIN" up the right-hand side, reading bottom to top
    lab = Image.new("RGBA", (60 * S, 16 * S), (0, 0, 0, 0))
    ld = ImageDraw.Draw(lab)
    f2 = ImageFont.truetype(FONT, 12 * S)
    for off, c in ((S * 0.8, lipc), (0, ink)):
        ld.text((30 * S, 8 * S + off), "G A I N", font=f2, fill=c, anchor="mm")
    lab = lab.rotate(90, expand=True)
    im.alpha_composite(lab, (round((CX + 36) * S - lab.size[0] / 2), round(y_at(0.5) * S - lab.size[1] / 2)))
    return im.resize((W, H), Image.LANCZOS)


def cap():
    sz = (CW * S, CH * S)
    im = Image.new("RGBA", sz, (0, 0, 0, 0))
    x0, y0, x1, y1 = 9 * S, 3 * S, (CW - 9) * S, 39 * S
    # cast shadow on the plate: light is top left
    sh = Image.new("L", sz, 0)
    ImageDraw.Draw(sh).rounded_rectangle((x0 + 3 * S, y0 + 6 * S, x1 + 3 * S, y1 + 6 * S), 7 * S, fill=170)
    sh = sh.filter(ImageFilter.GaussianBlur(3 * S))
    shadow = Image.new("RGBA", sz, (12, 8, 2, 0))
    shadow.putalpha(sh)
    im.alpha_composite(shadow)
    # body: dark outline, a darker lower lip (the cap's thickness), a bakelite face lit from the top
    d = Over(im)
    d.rounded_rectangle((x0, y0, x1, y1), 7 * S, fill=(14, 11, 7, 255))
    d.rounded_rectangle((x0 + S, y0 + S, x1 - S, y1 - S), 6 * S, fill=(30, 25, 18, 255))
    fh = 33 * S
    face = vgrad(x1 - x0 - 2 * S, fh, [(0, (86, 76, 62)), (0.18, (62, 54, 43)), (0.7, (40, 34, 27)), (1, (28, 23, 17))])
    im.paste(face, (x0 + S, y0 + S), rr_mask(face.size, (0, 0, face.size[0] - 1, fh - 1), 6 * S))
    d.rounded_rectangle((x0 + S, y0 + S, x1 - S, y0 + S + fh), 6 * S, outline=(255, 235, 200, 70), width=S)   # lit rim
    d.rounded_rectangle((x0 + 4 * S, y0 + 2 * S, x1 - 4 * S, y0 + 12 * S), 4 * S, fill=(255, 255, 255, 26))     # gloss
    mid = CAP_MID * S
    # grip ridges: a dark groove with a light edge under it, two above and two below the indicator
    for k in (-12, -7, 7, 12):
        y = mid + k * S
        d.line((x0 + 6 * S, y, x1 - 6 * S, y), fill=(8, 6, 3, 190), width=round(1.4 * S))
        d.line((x0 + 6 * S, y + 1.4 * S, x1 - 6 * S, y + 1.4 * S), fill=(255, 235, 200, 38), width=round(0.9 * S))
    # the indicator: a cream line, inset, with a shadow lip
    d.line((x0 + 5 * S, mid + 1.6 * S, x1 - 5 * S, mid + 1.6 * S), fill=(0, 0, 0, 150), width=round(2.4 * S))
    d.line((x0 + 5 * S, mid, x1 - 5 * S, mid), fill=(233, 228, 211, 255), width=round(2.4 * S))
    d.line((x0 + 5 * S, mid - 0.8 * S, x1 - 5 * S, mid - 0.8 * S), fill=(255, 255, 255, 90), width=S)
    return im.resize((CW, CH), Image.LANCZOS)


base().save(os.path.join(HERE, "images", "fader_base.png"))
cap().save(os.path.join(HERE, "images", "fader_cap.png"))
# a look at the result on the frame well's colour: the cap at zero, unity and full
prev = Image.new("RGBA", (W * 3 + 40, H + 20), (185, 180, 161, 255))
b, c = base(), cap()
for i, t in enumerate((0, 0.5, 1)):
    x = 10 + i * (W + 10)
    prev.alpha_composite(b, (x, 10))
    prev.alpha_composite(c, (x, 10 + round((H - CH) * (1 - t))))
prev.save(os.environ.get("PREVIEW", os.path.join(HERE, "build", "fader_preview.png")))
print("wrote images/fader_base.png, images/fader_cap.png")
