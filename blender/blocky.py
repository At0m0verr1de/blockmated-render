"""Build Blockmates characters in Blender from brand/characters.json.

Each character is a hierarchy of empties (pivots) with bevelled boxes under them,
so animation is just keyframing pivot rotations:

    <id>            root, at the feet; move/turn the whole character here
      <id>.body     hips (z=2); torso + every limb hangs off this
        <id>.neck   head pivot
        <id>.arm.L / <id>.arm.R   shoulder pivots
        <id>.leg.L / <id>.leg.R   hip pivots

The character faces -Y. Run inside Blender (bpy).
"""
import json
import math
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parent.parent
_mats = {}


def load_cast():
    data = json.loads((ROOT / "brand" / "characters.json").read_text())
    return {c["id"]: c for c in data["characters"] + data.get("extras", [])}


def hex_rgba(h):
    h = h.lstrip("#")
    srgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in srgb]
    return (*lin, 1.0)


def mat(color, rough=0.55):
    key = (color, rough)
    if key not in _mats:
        m = bpy.data.materials.new(f"m{color}")
        m.use_nodes = True
        bsdf = m.node_tree.nodes["Principled BSDF"]
        bsdf.inputs["Base Color"].default_value = hex_rgba(color)
        bsdf.inputs["Roughness"].default_value = rough
        bsdf.inputs["Specular"].default_value = 0.3
        m.diffuse_color = hex_rgba(color)
        _mats[key] = m
    return _mats[key]


def empty(name, parent=None, loc=(0, 0, 0)):
    e = bpy.data.objects.new(name, None)
    e.empty_display_size = 0.3
    bpy.context.scene.collection.objects.link(e)
    e.parent = parent
    e.location = loc
    return e


def box(name, size, loc, color, parent, bevel=0.06, rot=(0, 0, 0), rough=0.55):
    sx, sy, sz = size
    hx, hy, hz = sx / 2, sy / 2, sz / 2
    verts = [(x, y, z) for x in (-hx, hx) for y in (-hy, hy) for z in (-hz, hz)]
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.materials.append(mat(color, rough))
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.parent = parent
    ob.location = loc
    ob.rotation_euler = [math.radians(a) for a in rot]
    if bevel:
        b = ob.modifiers.new("bevel", "BEVEL")
        b.width = min(bevel, min(size) / 2 - 0.001)
        b.segments = 3
        b.limit_method = "NONE"
        for p in me.polygons:
            p.use_smooth = True
        me.use_auto_smooth = True
        me.auto_smooth_angle = math.radians(35)
    return ob


# ---------------------------------------------------------------- face

FACE_Y = -0.585  # front surface of the head, in neck space


# Expressions: eye style, lid cover (0..1 of the eye hidden from the top), brow (z, tilt toward the
# nose in degrees: + = angry V, - = worried), mouth shape, extras.
EXPRESSIONS = {
    "neutral":    dict(eyes="open", lid=0.0, brow=(0.88, 4), mouth="line"),
    "smile":      dict(eyes="open", lid=0.0, brow=(0.90, -4), mouth="smile", blush=True),
    "happy":      dict(eyes="arc", brow=(0.92, -6), mouth="open_smile", blush=True),
    "grin":       dict(eyes="open", lid=0.0, brow=(0.92, -6), mouth="open_smile", blush=True),
    "laugh":      dict(eyes="arc", brow=(0.94, -8), mouth="laugh", blush=True),
    "smirk":      dict(eyes="open", lid=0.25, brow=(0.88, 0), mouth="smirk", brow_raise=True),
    "shock":      dict(eyes="wide", lid=0.0, brow=(1.00, -10), mouth="o"),
    "scared":     dict(eyes="wide", lid=0.0, brow=(0.96, -22), mouth="wobble"),
    "worried":    dict(eyes="open", lid=0.0, brow=(0.90, -20), mouth="wobble"),
    "sad":        dict(eyes="open", lid=0.2, brow=(0.88, -22), mouth="frown", look=(0, -0.05)),
    "cry":        dict(eyes="arc_down", brow=(0.88, -24), mouth="cry", tears=True),
    "angry":      dict(eyes="open", lid=0.35, brow=(0.82, 24), mouth="frown"),
    "stern":      dict(eyes="open", lid=0.4, brow=(0.80, 14), mouth="line"),
    "determined": dict(eyes="open", lid=0.35, brow=(0.82, 12), mouth="tight"),
    "closed":     dict(eyes="closed", brow=(0.86, -4), mouth="line"),
    "confused":   dict(eyes="open", lid=0.0, brow=(0.90, 0), mouth="wobble", brow_raise=True, look=(0.04, 0.02)),
}
EXPR_ALIASES = {"thinking": "confused"}


def build_face(c, neck, ex=None):
    """Build one expression as a group (empty '<id>.face.<expr>') so shots can switch faces.
    Eyes sit under '<id>.face.<expr>.eyes' so they can blink (scale z)."""
    cid = c["id"]
    f = c["face"]
    ex = EXPR_ALIASES.get(ex or f.get("expression", "neutral"), ex or f.get("expression", "neutral"))
    spec = EXPRESSIONS.get(ex, EXPRESSIONS["neutral"])
    hair, skin = c["hair"]["color"], c["skin"]
    y = FACE_Y - 0.012
    grp = empty(f"{cid}.face.{ex}", neck)
    eyes = empty(f"{cid}.face.{ex}.eyes", grp, (0, 0, 0.68))
    ink, white = "#1A1414", "#FFFFFF"
    lx, ly = spec.get("look", (0, 0))
    for s in (-1, 1):
        ex_x = s * 0.25
        style = spec["eyes"]
        if style in ("open", "wide"):
            w, h = (0.27, 0.36) if style == "wide" else (0.24, 0.31)
            box(f"{cid}.eye.white", (w, 0.03, h), (ex_x, y, 0), white, eyes, bevel=0.09)
            pw, ph = (0.11, 0.15) if style == "wide" else (0.15, 0.21)
            box(f"{cid}.eye.pupil", (pw, 0.03, ph), (ex_x + lx + s * -0.015, y - 0.012, -0.02 + ly), ink, eyes, bevel=0.05)
            box(f"{cid}.eye.shine", (0.05, 0.02, 0.06), (ex_x + lx - 0.03, y - 0.024, 0.04 + ly), white, eyes, bevel=0.015)
            lid = spec.get("lid", 0)
            if lid:
                lh = h * lid + 0.03
                tilt = spec["brow"][1] * s * 0.6
                box(f"{cid}.eye.lid", (w + 0.04, 0.035, lh), (ex_x, y - 0.03, h / 2 - lh / 2 + 0.02), skin, eyes,
                    bevel=0.02, rot=(0, tilt, 0))
        elif style == "arc":  # happy ^ ^
            for k in (-1, 1):
                box(f"{cid}.eye.arc", (0.15, 0.03, 0.05), (ex_x + k * 0.055, y, 0.0), ink, eyes, bevel=0.02, rot=(0, k * 35, 0))
        elif style == "arc_down":  # squeezed shut, crying
            for k in (-1, 1):
                box(f"{cid}.eye.arc", (0.15, 0.03, 0.05), (ex_x + k * 0.055, y, 0.02), ink, eyes, bevel=0.02, rot=(0, -k * 30, 0))
        else:  # closed, calm
            for k in (-1, 1):
                box(f"{cid}.eye.arc", (0.14, 0.03, 0.045), (ex_x + k * 0.05, y, -0.03), ink, eyes, bevel=0.02, rot=(0, -k * 15, 0))
        bz, btilt = spec["brow"]
        if spec.get("brow_raise") and s == 1:
            bz += 0.07
        box(f"{cid}.brow", (0.3, 0.035, 0.075), (ex_x, y, bz), hair, grp, bevel=0.025, rot=(0, btilt * s, 0))
        if spec.get("blush"):
            box(f"{cid}.blush", (0.17, 0.02, 0.07), (s * 0.43, y + 0.004, 0.44), "#F28B9A", grp, bevel=0.03)
        if spec.get("tears"):
            box(f"{cid}.tear", (0.07, 0.03, 0.28), (ex_x + s * 0.06, y - 0.01, 0.46), "#7FD0FF", grp, bevel=0.03)

    m, mz = "#3A1414", 0.36
    mouth = spec["mouth"]
    if mouth == "line":
        box(f"{cid}.mouth", (0.2, 0.03, 0.05), (0, y, mz), m, grp, bevel=0.02)
    elif mouth == "tight":
        box(f"{cid}.mouth", (0.24, 0.03, 0.045), (0, y, mz), m, grp, bevel=0.02)
        for s in (-1, 1):
            box(f"{cid}.mouth", (0.06, 0.03, 0.045), (s * 0.14, y, mz - 0.02), m, grp, bevel=0.015, rot=(0, 25 * s, 0))
    elif mouth in ("smile", "frown"):
        d = 1 if mouth == "smile" else -1
        box(f"{cid}.mouth", (0.2, 0.03, 0.05), (0, y, mz - 0.01 * d), m, grp, bevel=0.02)
        for s in (-1, 1):
            box(f"{cid}.mouth", (0.11, 0.03, 0.05), (s * 0.14, y, mz + 0.035 * d), m, grp, bevel=0.02, rot=(0, -30 * s * d, 0))
    elif mouth == "smirk":
        box(f"{cid}.mouth", (0.2, 0.03, 0.05), (0.02, y, mz), m, grp, bevel=0.02)
        box(f"{cid}.mouth", (0.1, 0.03, 0.05), (0.15, y, mz + 0.04), m, grp, bevel=0.02, rot=(0, -30, 0))
    elif mouth in ("open_smile", "laugh"):
        h = 0.2 if mouth == "open_smile" else 0.26
        box(f"{cid}.mouth", (0.38, 0.03, h), (0, y, mz), m, grp, bevel=0.08)
        box(f"{cid}.teeth", (0.3, 0.02, 0.05), (0, y - 0.012, mz + h / 2 - 0.045), white, grp, bevel=0.015)
        box(f"{cid}.tongue", (0.2, 0.02, 0.07), (0, y - 0.012, mz - h / 2 + 0.06), "#E86A7A", grp, bevel=0.03)
    elif mouth == "o":
        box(f"{cid}.mouth", (0.18, 0.03, 0.24), (0, y, mz - 0.02), m, grp, bevel=0.08)
    elif mouth == "wobble":
        for k, dz in enumerate((0.0, 0.03, 0.0, 0.03)):
            box(f"{cid}.mouth", (0.08, 0.03, 0.045), (-0.12 + k * 0.08, y, mz + dz), m, grp, bevel=0.015,
                rot=(0, 30 if k % 2 else -30, 0))
    elif mouth == "cry":
        box(f"{cid}.mouth", (0.3, 0.03, 0.16), (0, y, mz - 0.02), m, grp, bevel=0.06)
        box(f"{cid}.tongue", (0.18, 0.02, 0.05), (0, y - 0.012, mz - 0.07), "#E86A7A", grp, bevel=0.02)

    if f.get("mustache"):
        box(f"{cid}.mustache", (0.46, 0.05, 0.1), (0, y - 0.01, 0.5), f["mustache"], grp, bevel=0.03)
    return grp


# ---------------------------------------------------------------- hair & hats

def build_hair(c, neck):
    h = c["hair"]
    col, style, cid = h["color"], h["style"], c["id"]
    top = lambda t=0.28: box(f"{cid}.hair", (1.35, 1.25, t), (0, 0.02, 1.22 + t / 2 - 0.1), col, neck, bevel=0.08)
    back = lambda bottom=0.55: box(f"{cid}.hair", (1.35, 0.22, 1.32 - bottom), (0, 0.55, (1.32 + bottom) / 2), col, neck,
                                   bevel=0.06)
    if style == "messy":
        top(0.32)
        back(0.6)
        for x, rz, ry in ((-0.38, 0, 14), (0.02, 0, -8), (0.4, 0, 20)):
            box(f"{cid}.hair", (0.46, 0.24, 0.34), (x, -0.5, 1.1), col, neck, bevel=0.05, rot=(0, ry, rz))
        for s in (-1, 1):
            box(f"{cid}.hair", (0.18, 1.0, 0.5), (s * 0.66, 0.1, 1.0), col, neck, bevel=0.05)
    elif style == "ponytail":
        top(0.26)
        back(0.7)
        box(f"{cid}.hair", (1.3, 0.16, 0.2), (0, -0.52, 1.13), col, neck, bevel=0.05)
        for s in (-1, 1):
            box(f"{cid}.hair", (0.16, 1.0, 0.45), (s * 0.66, 0.1, 1.02), col, neck, bevel=0.05)
        box(f"{cid}.band", (0.4, 0.2, 0.2), (0, 0.7, 1.12), h.get("band", "#FFD23F"), neck, bevel=0.05)
        box(f"{cid}.hair", (0.34, 0.34, 0.9), (0, 0.82, 0.68), col, neck, bevel=0.1, rot=(-18, 0, 0))
    elif style == "buzz":
        box(f"{cid}.hair", (1.3, 1.2, 0.14), (0, 0.02, 1.2), col, neck, bevel=0.06)
        back(0.75)
    elif style == "bun":
        top(0.24)
        back(0.62)
        for s in (-1, 1):
            box(f"{cid}.hair", (0.16, 1.05, 0.6), (s * 0.66, 0.05, 0.95), col, neck, bevel=0.05)
        box(f"{cid}.hair", (0.6, 0.6, 0.5), (0, 0.32, 1.5), col, neck, bevel=0.14)
    elif style == "bob":
        top(0.3)
        back(0.2)
        box(f"{cid}.hair", (1.36, 0.18, 0.24), (0, -0.52, 1.12), col, neck, bevel=0.06)
        for s in (-1, 1):
            box(f"{cid}.hair", (0.2, 1.15, 1.05), (s * 0.69, 0.06, 0.74), col, neck, bevel=0.06)


def build_accessories(c, neck, chest):
    cid = c["id"]
    for a in c.get("accessories", []):
        t, col = a["type"], a["color"]
        if t == "glasses":
            y = FACE_Y - 0.035
            for s in (-1, 1):
                cx = s * 0.25
                box(f"{cid}.glasses", (0.4, 0.04, 0.05), (cx, y, 0.85), col, neck, bevel=0.015)
                box(f"{cid}.glasses", (0.4, 0.04, 0.05), (cx, y, 0.48), col, neck, bevel=0.015)
                for e in (-1, 1):
                    box(f"{cid}.glasses", (0.05, 0.04, 0.42), (cx + e * 0.18, y, 0.665), col, neck, bevel=0.015)
                box(f"{cid}.glasses", (0.04, 1.0, 0.04), (s * 0.66, -0.08, 0.8), col, neck, bevel=0.01)
            box(f"{cid}.glasses", (0.1, 0.04, 0.04), (0, y, 0.72), col, neck, bevel=0.01)
        elif t == "cap_back":
            box(f"{cid}.cap", (1.4, 1.3, 0.4), (0, 0.02, 1.32), col, neck, bevel=0.12)
            box(f"{cid}.cap", (0.95, 0.65, 0.08), (0, 0.85, 1.2), col, neck, bevel=0.03)
            box(f"{cid}.cap", (0.16, 0.16, 0.08), (0, 0.02, 1.55), "#FFFFFF", neck, bevel=0.03)
        elif t == "fedora":
            box(f"{cid}.hat", (1.85, 1.75, 0.07), (0, 0.02, 1.24), col, neck, bevel=0.03)
            box(f"{cid}.hat", (1.3, 1.2, 0.55), (0, 0.02, 1.53), col, neck, bevel=0.1)
            box(f"{cid}.hat", (1.33, 1.23, 0.12), (0, 0.02, 1.33), a.get("band", "#7A2A2A"), neck, bevel=0.03)


# ---------------------------------------------------------------- torso detail

def build_torso(c, body):
    t, cid = c["torso"], c["id"]
    w, col, acc = t.get("width", 2.0), t["color"], t.get("accent", "#FFFFFF")
    box(f"{cid}.torso", (w, 1.0, 2.0), (0, 0, 1.0), col, body, bevel=0.08)
    fy = -0.51
    d = t.get("detail")
    if d == "hoodie":
        box(f"{cid}.pocket", (1.3, 0.06, 0.6), (0, fy, 0.45), shade(col, 0.82), body, bevel=0.04)
        for s in (-1, 1):
            box(f"{cid}.string", (0.06, 0.05, 0.5), (s * 0.22, fy - 0.02, 1.62), acc, body, bevel=0.02)
        box(f"{cid}.hood", (1.6, 0.4, 0.45), (0, 0.55, 1.85), shade(col, 0.88), body, bevel=0.12)
    elif d == "jacket":
        box(f"{cid}.shirt", (0.7, 0.06, 2.0), (0, fy, 1.0), acc, body, bevel=0.03)
        box(f"{cid}.zip", (0.05, 0.07, 1.9), (-0.37, fy - 0.01, 1.0), "#D8D8D8", body, bevel=0.01)
        box(f"{cid}.collar", (w + 0.06, 1.06, 0.18), (0, 0, 1.95), shade(col, 0.8), body, bevel=0.05)
    elif d == "tee_stripe":
        box(f"{cid}.stripe", (w + 0.02, 1.02, 0.3), (0, 0, 1.2), acc, body, bevel=0.04)
    elif d == "cardigan":
        box(f"{cid}.blouse", (0.6, 0.06, 2.0), (0, fy, 1.0), acc, body, bevel=0.03)
        for z in (0.4, 0.85, 1.3):
            box(f"{cid}.button", (0.1, 0.06, 0.1), (0.4, fy - 0.02, z), "#E8D9B0", body, bevel=0.03)
    elif d == "sweater":
        box(f"{cid}.hem", (w + 0.02, 1.02, 0.2), (0, 0, 0.1), acc, body, bevel=0.04)
        box(f"{cid}.collar", (0.8, 1.04, 0.14), (0, 0, 1.95), acc, body, bevel=0.04)
    elif d == "trench":
        box(f"{cid}.belt", (w + 0.04, 1.04, 0.18), (0, 0, 0.5), acc, body, bevel=0.04)
        box(f"{cid}.lapel", (0.5, 0.06, 0.9), (-0.25, fy, 1.5), shade(col, 0.85), body, bevel=0.03, rot=(0, -12, 0))
        box(f"{cid}.lapel", (0.5, 0.06, 0.9), (0.25, fy, 1.5), shade(col, 0.85), body, bevel=0.03, rot=(0, 12, 0))
        box(f"{cid}.collar", (w + 0.1, 1.1, 0.3), (0, 0.05, 1.95), shade(col, 0.85), body, bevel=0.06)
    return w


def shade(hex_color, k):
    h = hex_color.lstrip("#")
    r, g, b = (int(int(h[i:i + 2], 16) * k) for i in (0, 2, 4))
    return f"#{r:02X}{g:02X}{b:02X}"


# ---------------------------------------------------------------- whole character

def build(c, loc=(0, 0, 0), rot_z=0.0, exprs=None):
    cid = c["id"]
    root = empty(cid, loc=loc)
    root.rotation_euler.z = math.radians(rot_z)
    root.scale = (c.get("scale", 1.0),) * 3
    root["blockmate"] = cid

    body = empty(f"{cid}.body", root, (0, 0, 2.0))
    w = build_torso(c, body)

    for side, s in (("L", 1), ("R", -1)):
        leg = empty(f"{cid}.leg.{side}", body, (s * 0.5, 0, 0))
        box(f"{cid}.pants", (0.98, 0.98, 1.68), (0, 0, -0.84), c["pants"], leg, bevel=0.06)
        box(f"{cid}.shoe", (1.02, 1.12, 0.36), (0, -0.05, -1.82), c["shoes"], leg, bevel=0.08)

        arm = empty(f"{cid}.arm.{side}", body, (s * (w / 2 + 0.5), 0, 1.8))
        sl = c["sleeves"]
        sleeve_len = 1.55 if sl["length"] == "long" else 0.7
        box(f"{cid}.sleeve", (0.98, 0.98, sleeve_len), (0, 0, 0.2 - sleeve_len / 2), sl["color"], arm, bevel=0.06)
        skin_len = 2.0 - sleeve_len
        box(f"{cid}.skin", (0.94, 0.94, skin_len), (0, 0, 0.2 - sleeve_len - skin_len / 2 + 0.02), c["skin"], arm,
            bevel=0.08)
        if c["torso"].get("detail") == "trench":
            box(f"{cid}.coat", (0.99, 0.99, 0.9), (0, 0, -0.44), c["torso"]["color"], leg, bevel=0.05)

    neck = empty(f"{cid}.neck", body, (0, 0, 2.0))
    box(f"{cid}.head", (1.28, 1.16, 1.22), (0, 0, 0.64), c["skin"], neck, bevel=0.16)
    faces = {}
    for ex in (exprs or [c["face"].get("expression", "neutral")]):
        faces[ex] = build_face(c, neck, ex)
    root["faces"] = list(faces)
    build_hair(c, neck)
    build_accessories(c, neck, body)
    return root


# ---------------------------------------------------------------- scene helpers

def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _mats.clear()


def setup_render(width, height, samples=48, sky="#CFE9FF"):
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.resolution_x, sc.render.resolution_y = width, height
    sc.render.resolution_percentage = 100
    sc.eevee.taa_render_samples = samples
    sc.eevee.use_gtao = True
    sc.eevee.gtao_distance = 1.5
    sc.eevee.use_soft_shadows = True
    sc.eevee.use_bloom = True
    sc.eevee.bloom_threshold = 1.0
    sc.eevee.bloom_intensity = 0.04
    sc.eevee.shadow_cube_size = "2048"
    sc.eevee.shadow_cascade_size = "4096"
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    world = bpy.data.worlds.new("world")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = hex_rgba(sky)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.75
    sc.world = world


def add_sun(rot=(50, 0, -30), strength=2.4, angle=8):
    sun = bpy.data.lights.new("sun", "SUN")
    sun.energy = strength
    sun.angle = math.radians(angle)
    ob = bpy.data.objects.new("sun", sun)
    bpy.context.scene.collection.objects.link(ob)
    ob.rotation_euler = [math.radians(a) for a in rot]
    return ob


def add_camera(loc, look_at, lens=50):
    cam = bpy.data.cameras.new("cam")
    cam.lens = lens
    ob = bpy.data.objects.new("cam", cam)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    target = empty("cam.target", loc=look_at)
    con = ob.constraints.new("TRACK_TO")
    con.target = target
    con.track_axis = "TRACK_NEGATIVE_Z"
    con.up_axis = "UP_Y"
    bpy.context.scene.camera = ob
    return ob


def add_floor(color="#EDE6DA", size=200):
    return box("floor", (size, size, 0.2), (0, 0, -0.1), color, None, bevel=0, rough=0.8)
