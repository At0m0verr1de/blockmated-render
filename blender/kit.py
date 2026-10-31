"""Place models from the free Kenney kits (CC0) in assets/kenney/.

Each model is imported once per shot into a hidden collection and then placed as lightweight
collection instances, so a street with forty houses costs about the same as one.
Scales bring each kit to our character size (a kid is ~5.4 units tall, an adult ~6.4).
"""
import math
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parent.parent
KIT_DIR = ROOT / "assets" / "kenney"
SCALE = {"furniture-kit": 8.0, "car-kit": 6.0, "city-kit-suburban": 16.0, "city-kit-roads": 16.0}


def _path(kit, name):
    for sub in ("Models/GLB format", "Models/GLTF format"):
        p = KIT_DIR / kit / sub / f"{name}.glb"
        if p.exists():
            return p
    raise FileNotFoundError(f"Kenney model not found: {kit}/{name}")


def source(kit, name):
    """Hidden collection holding one imported copy of the model."""
    key = f"kit:{kit}/{name}"
    col = bpy.data.collections.get(key)
    if col:
        return col
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(_path(kit, name)))
    new = [o for o in bpy.data.objects if o not in before]
    col = bpy.data.collections.new(key)
    for o in new:
        for c in list(o.users_collection):
            c.objects.unlink(o)
        col.objects.link(o)
    return col


def place(kit, name, loc=(0, 0, 0), rot=0.0, scale=1.0):
    """Instance a kit model. rot is degrees around Z; scale multiplies the kit's base scale."""
    col = source(kit, name)
    ob = bpy.data.objects.new(f"{name}", None)
    ob.instance_type = "COLLECTION"
    ob.instance_collection = col
    s = SCALE.get(kit, 1.0) * scale
    ob.scale = (s, s, s)
    ob.location = loc
    ob.rotation_euler = (0, 0, math.radians(rot))
    bpy.context.scene.collection.objects.link(ob)
    return ob


def place_tinted(kit, name, color, loc=(0, 0, 0), rot=0.0, scale=1.0):
    """A real copy whose materials are multiplied toward `color` (e.g. a white van)."""
    from blocky import hex_rgba
    col = source(kit, name)
    root = bpy.data.objects.new(f"{name}.tinted", None)
    bpy.context.scene.collection.objects.link(root)
    copies = {}
    for o in col.objects:
        c = o.copy()
        if o.data is not None:
            c.data = o.data.copy()
            for i, m in enumerate(c.data.materials):
                if m is None:
                    continue
                m2 = m.copy()
                bsdf = m2.node_tree.nodes.get("Principled BSDF") if m2.use_nodes else None
                if bsdf is not None:
                    tint = m2.node_tree.nodes.new("ShaderNodeMixRGB")
                    tint.blend_type = "MIX"  # blend toward the colour (multiply can't lighten a dark van)
                    tint.inputs["Fac"].default_value = 0.85
                    tint.inputs["Color2"].default_value = hex_rgba(color)
                    links = m2.node_tree.links
                    src = bsdf.inputs["Base Color"].links[0].from_socket if bsdf.inputs["Base Color"].links else None
                    if src is not None:
                        links.new(src, tint.inputs["Color1"])
                    else:
                        tint.inputs["Color1"].default_value = bsdf.inputs["Base Color"].default_value
                    links.new(tint.outputs["Color"], bsdf.inputs["Base Color"])
                c.data.materials[i] = m2
        bpy.context.scene.collection.objects.link(c)
        copies[o.name] = c
    for o in col.objects:
        c = copies[o.name]
        c.parent = copies[o.parent.name] if o.parent and o.parent.name in copies else root
        if not o.parent:
            c.matrix_parent_inverse.identity()
    s = SCALE.get(kit, 1.0) * scale
    root.scale = (s, s, s)
    root.location = loc
    root.rotation_euler = (0, 0, math.radians(rot))
    return root
