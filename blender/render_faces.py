"""Expression sheet: one character's head in every expression. blender -b -P blender/render_faces.py -- [id]"""
import copy
import math
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blocky  # noqa: E402

cid = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "milo"
blocky.reset_scene()
blocky.setup_render(1600, 1600, sky="#BFE3FF")
blocky.add_sun(rot=(60, 0, -20))
exprs = list(blocky.EXPRESSIONS)
cols = 4
for i, ex in enumerate(exprs):
    c = copy.deepcopy(blocky.load_cast()[cid])
    c["id"] = f"{cid}_{ex}"
    x, z = (i % cols) * 2.2, -(i // cols) * 2.6
    root = blocky.build(c, loc=(x, 0, z - 4.0), exprs=[ex])
    cu = bpy.data.curves.new(ex, "FONT"); cu.body = ex; cu.size = 0.28; cu.align_x = "CENTER"
    t = bpy.data.objects.new(ex, cu); bpy.context.scene.collection.objects.link(t)
    t.location = (x, -0.7, z - 0.2); t.rotation_euler = (math.radians(90), 0, 0)
    t.data.materials.append(blocky.mat("#253B6E"))
cam = blocky.add_camera((3.3, -20, 0.2), (3.3, 0, -3.3), lens=60)
cam.data.type = "ORTHO"; cam.data.ortho_scale = 10.8
bpy.context.scene.render.filepath = str(blocky.ROOT / "out" / "brand" / f"faces_{cid}.png")
bpy.ops.render.render(write_still=True)
