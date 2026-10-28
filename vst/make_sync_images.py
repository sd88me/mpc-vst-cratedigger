#!/usr/bin/env python3
"""Draws the lit buttons, each a light grey "off" and an amber "on" picture with its label baked in: images/sync_off/on.png
(TRANSPORT SYNC) and images/src_discogs|channel|youtube_off/on.png and music_off/on.png (the FIND tab's SOURCE and MUSIC ONLY).

The label is baked in dark ink (the skin builder's own button label is light, unreadable on light grey).
Needs Pillow and Titillium Web SemiBold (OFL): FONT=<path to TitilliumWeb-SemiBold.ttf>, e.g. from
mpc-vst's tools/html_art/fonts/.  Run:  FONT=... python3 vst/make_sync_images.py
"""
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.environ["FONT"]
S, W, H = 4, 176, 48


def lerp(c0, c1, t):
    return tuple(int(c0[i] + (c1[i] - c0[i]) * t) for i in range(3))


def make(name, base, lit=False, txt="TRANSPORT SYNC"):
    """A keycap lit from the top left: dark outline, a stepped lower edge, a gradient face, a gloss band and a lit rim."""
    mul = lambda k: tuple(max(0, min(255, int(c * k))) for c in base)
    face_h = H - 4
    im = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, W * S - 1, H * S - 1), 7 * S, fill=(20, 14, 6, 255))              # outline + hard shadow
    d.rounded_rectangle((S, 3 * S, W * S - 1 - S, H * S - 1 - S), 6 * S, fill=mul(0.5) + (255,))  # lower edge
    face = Image.new("RGBA", (W * S, face_h * S), (0, 0, 0, 0))
    fd = ImageDraw.Draw(face)
    for y in range(face_h * S):
        t = y / (face_h * S - 1)
        fd.line((0, y, W * S, y), fill=lerp(mul(1.22), mul(0.84), t) + (255,))
    mask = Image.new("L", face.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, W * S - 1 - 2 * S, face_h * S - 1), 6 * S, fill=255)
    im.paste(face.crop((0, 0, W * S - 2 * S, face_h * S)), (S, S), mask.crop((0, 0, W * S - 2 * S, face_h * S)))
    d = ImageDraw.Draw(im, "RGBA")
    d.rounded_rectangle((S, S, W * S - 1 - S, (face_h + 1) * S - 1), 6 * S, outline=mul(1.45) + (150,), width=S)  # lit rim
    d.rounded_rectangle((3 * S, 2 * S, W * S - 1 - 3 * S, (face_h // 2) * S), 4 * S, fill=(255, 255, 255, 38))  # gloss
    f = ImageFont.truetype(FONT, 17 * S)
    tw = d.textlength(txt, font=f)
    ink = (58, 53, 43, 255)
    ty = (face_h + 1) * S / 2
    d.text(((W * S - tw) / 2, ty + S), txt, font=f, fill=(255, 255, 255, 110), anchor="lm")  # engraved: light lip below
    d.text(((W * S - tw) / 2, ty), txt, font=f, fill=ink, anchor="lm")
    im.resize((W, H), Image.LANCZOS).save(os.path.join(HERE, "images", name))


make("sync_off.png", (196, 193, 184))
make("sync_on.png", (232, 163, 23))
for key, label in (("src_discogs", "DISCOGS"), ("src_channel", "CHANNEL"), ("src_youtube", "YOUTUBE"), ("music", "MUSIC ONLY")):
    make(key + "_off.png", (196, 193, 184), txt=label)
    make(key + "_on.png", (232, 163, 23), True, txt=label)
