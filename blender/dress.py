"""Set dressing: the small things that make a room feel lived-in (frames, shelves of books, windows with
curtains, clocks, cork boards, fairy lights, bunting).

Everything hangs on a wall anchor so the same helper works on any wall:
    w = wall("back", y=16)            # back wall at y=16, items face -Y (toward the usual camera)
    w = wall("left", x=-18)           # left wall, items face +X;  wall("right", x=18) faces -X
    frame(w, u=-4, z=7, size=(3, 4))  # u = position along the wall (left->right as seen from the room), z = centre height
"""
import math
import random

import bpy

from blocky import box, empty
from sets import ebox, text

WOOD, DARK = "#7A5232", "#2B2522"
BOOK_COLORS = ["#C0392B", "#2E86C1", "#27AE60", "#F1C40F", "#8E44AD", "#E67E22", "#16A085", "#ECF0F1", "#34495E", "#D35400"]
ART = ["#F7B6D2", "#9AD8FF", "#FFD27D", "#7CC4A4", "#E57373", "#B39DDB", "#FFAB91", "#81D4FA"]


def wall(side, x=0.0, y=0.0):
    """Anchor whose local -Y points into the room and local +X runs left->right as seen from inside."""
    rot = {"back": 0, "left": 90, "right": -90, "front": 180}[side]
    a = empty(f"wall.{side}", None, (x, y, 0))
    a.rotation_euler.z = math.radians(rot)
    return a


def frame(w, u, z, size=(3.0, 4.0), art=None, seed=0, border=DARK):
    """Framed picture: border, mat and a simple abstract print."""
    rnd = random.Random(seed)
    fw, fh = size
    box("frame", (fw, 0.16, fh), (u, -0.08, z), border, w, bevel=0.04)
    box("frame.mat", (fw - 0.3, 0.06, fh - 0.3), (u, -0.18, z), "#F4F0E6", w, bevel=0.01)
    box("frame.art", (fw - 0.7, 0.04, fh - 0.7), (u, -0.22, z), art or rnd.choice(ART), w, bevel=0.01)
    for _ in range(3):   # a few shapes on the print
        sw, sh = rnd.uniform(0.3, 0.45) * fw, rnd.uniform(0.2, 0.4) * fh
        box("frame.shape", (sw, 0.03, sh), (u + rnd.uniform(-0.2, 0.2) * fw, -0.25, z + rnd.uniform(-0.2, 0.2) * fh),
            rnd.choice(ART), w, bevel=0.02)


def poster(w, u, z, size=(3.4, 4.6), color="#9CC8E8", label=None, label_color="#2B2B2B", seed=0):
    """Unframed poster with a header band and optional text."""
    rnd = random.Random(seed)
    pw, ph = size
    box("poster", (pw, 0.06, ph), (u, -0.04, z), color, w, bevel=0.01)
    box("poster.band", (pw - 0.4, 0.03, ph * 0.18), (u, -0.08, z + ph * 0.3), rnd.choice(ART), w, bevel=0.01)
    box("poster.img", (pw - 0.8, 0.03, ph * 0.4), (u, -0.08, z - ph * 0.1), rnd.choice(ART), w, bevel=0.01)
    if label:
        t = text(label, (0, 0, 0), min(0.4, pw / max(6, len(label)) * 1.6), label_color, parent=w)
        t.location = (u, -0.1, z + ph * 0.27)


def shelf(w, u, z, width=5.0, seed=0, plant=True):
    """Wall shelf with a row of books, a few leaning, and maybe a small plant."""
    rnd = random.Random(seed)
    box("shelf", (width, 1.1, 0.16), (u, -0.55, z), WOOD, w, bevel=0.03)
    for s in (-1, 1):
        box("shelf.bracket", (0.12, 0.9, 0.5), (u + s * (width / 2 - 0.4), -0.45, z - 0.3), DARK, w, bevel=0.02)
    x = u - width / 2 + 0.3
    end = u + width / 2 - (1.2 if plant else 0.3)
    while x < end:
        bw, bh = rnd.uniform(0.18, 0.34), rnd.uniform(0.7, 1.1)
        tilt = rnd.choice((0, 0, 0, 0, 12, -10))
        box("book", (bw, 0.8, bh), (x + bw / 2, -0.55, z + 0.08 + bh / 2), rnd.choice(BOOK_COLORS), w, bevel=0.02,
            rot=(0, tilt, 0))
        x += bw + (0.25 if tilt else 0.02)
    if plant:
        pot(w, u + width / 2 - 0.6, -0.55, z + 0.08, s=0.8, seed=seed)


def pot(w, u, y, z, s=1.0, seed=0):
    """Small potted plant (terracotta pot + a few leafy cubes)."""
    rnd = random.Random(seed + 11)
    box("pot", (0.6 * s, 0.6 * s, 0.55 * s), (u, y, z + 0.28 * s), "#C8693E", w, bevel=0.06)
    for _ in range(5):
        k = rnd.uniform(0.35, 0.55) * s
        box("leaf", (k, k, k), (u + rnd.uniform(-0.25, 0.25) * s, y + rnd.uniform(-0.2, 0.2) * s,
                                 z + (0.7 + rnd.uniform(0, 0.5)) * s), rnd.choice(("#4CAF50", "#3E8E41", "#66BB6A")), w, bevel=0.08)


def window(w, u, z, size=(5.0, 5.0), sky="#FFD9A8", glow=3.0, curtains="#C96F57", frame_col="#F4F0E6"):
    """Window: glowing pane (sky colour), cross mullions, sill and gathered curtains with a rod."""
    ww, wh = size
    ebox("window.glass", (ww - 0.3, 0.05, wh - 0.3), (u, 0.02, z), sky, glow, parent=w, bevel=0)
    for dz in (-wh / 2, wh / 2):
        box("window.frame", (ww, 0.3, 0.25), (u, -0.12, z + dz), frame_col, w, bevel=0.03)
    for du in (-ww / 2, ww / 2):
        box("window.frame", (0.25, 0.3, wh), (u + du, -0.12, z), frame_col, w, bevel=0.03)
    box("window.mullion", (0.14, 0.2, wh), (u, -0.1, z), frame_col, w, bevel=0.02)
    box("window.mullion", (ww, 0.2, 0.14), (u, -0.1, z), frame_col, w, bevel=0.02)
    box("window.sill", (ww + 0.6, 0.7, 0.18), (u, -0.35, z - wh / 2 - 0.1), frame_col, w, bevel=0.03)
    if curtains:
        box("curtain.rod", (ww + 2.4, 0.12, 0.12), (u, -0.5, z + wh / 2 + 0.5), DARK, w, bevel=0.04)
        for s in (-1, 1):   # gathered folds: alternating depth strips
            for k in range(5):
                box("curtain", (0.32, 0.22, wh + 0.9), (u + s * (ww / 2 + 0.3 - k * 0.28), -0.45 - 0.12 * (k % 2), z + 0.05),
                    curtains, w, bevel=0.06)


def clock(w, u, z, r=0.9):
    box("clock", (2 * r, 0.2, 2 * r), (u, -0.1, z), DARK, w, bevel=r * 0.9)
    box("clock.face", (2 * r - 0.25, 0.1, 2 * r - 0.25), (u, -0.2, z), "#FAFAFA", w, bevel=r * 0.8)
    box("clock.hand", (0.08, 0.06, r * 0.7), (u, -0.27, z + r * 0.3), DARK, w, bevel=0.01)
    box("clock.hand", (0.08, 0.06, r * 0.5), (u + r * 0.18, -0.27, z - r * 0.12), DARK, w, bevel=0.01, rot=(0, 60, 0))


def corkboard(w, u, z, size=(5.0, 3.4), seed=0):
    rnd = random.Random(seed)
    cw, ch = size
    box("cork.frame", (cw, 0.14, ch), (u, -0.07, z), WOOD, w, bevel=0.03)
    box("cork", (cw - 0.3, 0.06, ch - 0.3), (u, -0.15, z), "#C9A06A", w, bevel=0.01)
    for _ in range(7):
        pw, ph = rnd.uniform(0.7, 1.2), rnd.uniform(0.8, 1.2)
        box("note", (pw, 0.03, ph), (u + rnd.uniform(-cw / 2 + 0.8, cw / 2 - 0.8), -0.2, z + rnd.uniform(-ch / 2 + 0.7, ch / 2 - 0.7)),
            rnd.choice(("#FFF59D", "#FFFFFF", "#F8BBD0", "#B3E5FC", "#C8E6C9")), w, bevel=0.01, rot=(0, rnd.uniform(-8, 8), 0))


def fairy_lights(w, u0, u1, z, sag=0.8, n=24, colors=("#FFD27D", "#FFB3D9", "#FFF2C2")):
    """A sagging string of glowing bulbs along a wall (bloom makes them sparkle)."""
    for i in range(n):
        t = i / (n - 1)
        u = u0 + (u1 - u0) * t
        dz = -sag * 4 * t * (1 - t)
        ebox("bulb", (0.16, 0.16, 0.2), (u, -0.25, z + dz), colors[i % len(colors)], 6.0, parent=w, bevel=0.06)
    for k in range(n - 1):
        t = (k + 0.5) / (n - 1)
        box("wire", ((u1 - u0) / (n - 1), 0.03, 0.03), (u0 + (u1 - u0) * t, -0.22, z - sag * 4 * t * (1 - t) + 0.1), DARK, w, bevel=0)


def bunting(w, u0, u1, z, n=12, seed=0):
    rnd = random.Random(seed)
    for i in range(n):
        t = (i + 0.5) / n
        box("flag", (0.5, 0.04, 0.6), (u0 + (u1 - u0) * t, -0.3, z - 0.6 * 4 * t * (1 - t)), rnd.choice(ART), w, bevel=0.02,
            rot=(0, 45, 0))


def rug(x, y, size=(10, 7), color="#B5651D", border="#F3E5C8", rot=0):
    box("rug.border", (size[0], size[1], 0.05), (x, y, 0.03), border, None, bevel=0.02, rot=(0, 0, rot))
    box("rug", (size[0] - 0.8, size[1] - 0.8, 0.06), (x, y, 0.04), color, None, bevel=0.02, rot=(0, 0, rot))
