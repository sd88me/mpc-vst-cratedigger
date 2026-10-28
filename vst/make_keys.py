#!/usr/bin/env python3
"""Draws the FIND tab's popup keyboard into images/ (SVG): key_<X>.svg, key_space/back/clear/hide/send.svg and kb_bg.svg.

Keycaps in the skin's own palette (cream face, dark ink, blue SEND). Sizes match layout.conf's [tab FIND] key lines, so
re-run this after changing either:  python3 vst/make_keys.py   (plain Python, no dependencies; the build never runs it).
"""
import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")
INK, DIM, LINE, FACE_HI, FACE_LO, EDGE = "#2b2822", "#6b6558", "#3a352c", "#efead9", "#d3ceba", "#8f8a78"
BLUE, BLUE_HI, BLUE_EDGE, LIGHT = "#2f4a6b", "#3d5f88", "#1d3049", "#e9e4d3"
FONT = "font-family=\"Titillium Web\" font-weight=\"700\""


def svg(name, w, h, body, defs=""):
    with open(os.path.join(OUT, name), "w") as f:
        f.write('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">%s%s</svg>\n'
                % (w, h, w, h, "<defs>%s</defs>" % defs if defs else "", body))


def key(name, w, h, label, size, hi=FACE_HI, lo=FACE_LO, edge=EDGE, ink=INK):
    gid = "g" + name.replace(".svg", "").replace("key_", "")
    defs = ('<linearGradient id="%s" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="%s"/>'
            '<stop offset="1" stop-color="%s"/></linearGradient>' % (gid, hi, lo))
    face_h = h - 5
    body = ('<rect x="0.5" y="0.5" width="%g" height="%g" rx="8" fill="%s" stroke="#16120d" stroke-width="1"/>' % (w - 1, h - 1, edge)
            + '<rect x="1.5" y="1.5" width="%g" height="%g" rx="7" fill="url(#%s)"/>' % (w - 3, face_h, gid)
            + '<rect x="3" y="3" width="%g" height="1.5" rx="0.75" fill="#fff" fill-opacity="0.55"/>' % (w - 6)
            + '<text x="%g" y="%g" %s font-size="%d" fill="%s" text-anchor="middle" letter-spacing="1">%s</text>'
            % (w / 2, face_h / 2 + size * 0.36 + 1, FONT, size, ink, label))
    svg(name, w, h, body, defs)


KW, KH, DH = 108, 52, 30          # letter key, its height, the digit row's height
for c in "QWERTYUIOPASDFGHJKLZXCVBNM":
    key("key_%s.svg" % c, KW, KH, c, 28)
for c in "1234567890":
    key("key_%s.svg" % c, KW, DH, c, 20)
key("key_space.svg", 520, KH, "SPACE", 22)
key("key_back.svg", 170, KH, "BACK", 22)
key("key_clear.svg", 190, KH, "CLEAR", 22)
key("key_hide.svg", 180, KH, "HIDE", 22, ink=DIM)
key("key_send.svg", 226, KH, "SEARCH", 24, hi=BLUE_HI, lo=BLUE, edge=BLUE_EDGE, ink=LIGHT)
# the panel behind the keys: a recessed well like the frames' (make_chassis.py), 1280 x 286 from layout y 424
svg("kb_bg.svg", 1280, 286,
    '<rect x="40" y="0" width="1200" height="276" rx="6" fill="#aca793"/>'
    '<rect x="41" y="1" width="1198" height="274" rx="5" fill="#b9b4a1" stroke="#8f8a78" stroke-width="1"/>'
    '<rect x="42" y="2" width="1196" height="2" fill="#000" fill-opacity="0.18"/>')
print("wrote %d key images + kb_bg.svg" % (26 + 10 + 5))
