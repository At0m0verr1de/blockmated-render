"""Render the cast lineup and a close-up of each character.

blender -b -P blender/render_lineup.py
Writes out/brand/lineup.png and out/brand/<id>.png
"""
import math
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blocky  # noqa: E402

OUT = blocky.ROOT / "out" / "brand"
OUT.mkdir(parents=True, exist_ok=True)


def label(text, x, z):
    cu = bpy.data.curves.new(f"label.{text}", "FONT")
    cu.body = text
    cu.align_x = "CENTER"
    cu.size = 0.75
    ob = bpy.data.objects.new(f"label.{text}", cu)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = (x, -5.5, z)
    ob.rotation_euler = (math.radians(90), 0, 0)
    ob.data.materials.append(blocky.mat("#2A2A3A"))
    ob.data.extrude = 0.04


def stage(w, h):
    blocky.reset_scene()
    blocky.setup_render(w, h, sky="#BFE3FF")
    blocky.add_floor("#F4EFE6")
    blocky.add_sun()


stage(1920, 1080)
cast = list(blocky.load_cast().values())
gap = 5.4
xs = [(i - (len(cast) - 1) / 2) * gap for i in range(len(cast))]
for c, x in zip(cast, xs):
    blocky.build(c, loc=(x, 0, 0), rot_z=-x * 1.6)
    label(c["name"], x, 0.05)
cam = blocky.add_camera((0, -50, 6.5), (0, 0, 3.4), lens=50)
bpy.context.scene.render.filepath = str(OUT / "lineup.png")
bpy.ops.render.render(write_still=True)

# close-ups: 3/4 view of each character, portrait
for c in cast:
    stage(1080, 1350)
    blocky.build(c, rot_z=0)
    s = c.get("scale", 1.0)
    blocky.add_camera((-4.8, -11, 4.8 * s), (0, 0, 3.3 * s), lens=50)
    bpy.context.scene.render.filepath = str(OUT / f"{c['id']}.png")
    bpy.ops.render.render(write_still=True)
print("done")
