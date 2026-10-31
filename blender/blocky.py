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


FACE_STYLE = "geo"   # "decal" = drawn image faces from assets/faces (set per story by render_reel)
FACES_DIR = Path(__file__).resolve().parent.parent / "assets" / "faces"

# Body proportions. "classic" = the original chunky 2-2-1 blockmate; "slim" = narrower torso, longer legs and
# arms, slightly smaller head (closer to the reference style). Set per story by render_reel (spec "body").
BODY_STYLE = "classic"
BODIES = {
    "classic": dict(leg=2.04, leg_w=0.98, leg_x=0.5, torso_h=2.0, torso_d=1.0, width_k=1.0, arm=2.0, arm_w=0.98, head=1.0),
    "slim": dict(leg=2.9, leg_w=0.74, leg_x=0.38, torso_h=2.15, torso_d=0.8, width_k=0.76, arm=2.45, arm_w=0.68, head=0.95),
}
_decal_mats = {}


def _decal_mat(path):
    if path in _decal_mats:
        return _decal_mats[path]
    m = bpy.data.materials.new(f"decal.{Path(path).stem}")
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(str(path), check_existing=True)
    tex.interpolation = "Linear"
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
    bsdf.inputs["Roughness"].default_value = 0.8
    bsdf.inputs["Specular"].default_value = 0.1
    m.blend_method = "CLIP"
    m.alpha_threshold = 0.4
    m.shadow_method = "NONE"
    _decal_mats[path] = m
    return m


def _decal_plane(name, w, h, loc, parent, path):
    hw, hh = w / 2, h / 2
    me = bpy.data.meshes.new(name)
    me.from_pydata([(-hw, 0, -hh), (hw, 0, -hh), (hw, 0, hh), (-hw, 0, hh)], [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new()
    for i, co in enumerate(((0, 0), (1, 0), (1, 1), (0, 1))):
        uv.data[i].uv = co
    me.materials.append(_decal_mat(path))
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.parent = parent
    ob.location = loc
    return ob


def build_decal_face(c, neck, ex):
    """Image face: '<id>.face.<ex>' group with a face layer and an eye strip ('...eyes', squashed to blink)."""
    cid = c["id"]
    name = ex if (FACES_DIR / f"{ex}_face.png").exists() else "neutral"
    grp = empty(f"{cid}.face.{ex}", neck)
    _decal_plane(f"{cid}.face.{ex}.layer", 1.28, 1.22, (0, FACE_Y - 0.012, 0.64), grp, FACES_DIR / f"{name}_face.png")
    _decal_plane(f"{cid}.face.{ex}.eyes", 1.28, 0.46, (0, FACE_Y - 0.018, 0.69), grp, FACES_DIR / f"{name}_eyes.png")
    if c["face"].get("mustache"):
        box(f"{cid}.mustache", (0.46, 0.05, 0.1), (0, FACE_Y - 0.03, 0.5), c["face"]["mustache"], grp, bevel=0.03)
    return grp


def build_face(c, neck, ex=None):
    """Build one expression as a group (empty '<id>.face.<expr>') so shots can switch faces.
    Eyes sit under '<id>.face.<expr>.eyes' so they can blink (scale z)."""
    if FACE_STYLE == "decal":
        return build_decal_face(c, neck, ex or c["face"].get("expression", "neutral"))
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
    elif style == "long":          # straight, past the shoulders, with bangs
        top(0.3)
        box(f"{cid}.hair", (1.42, 0.3, 2.1), (0, 0.5, 0.35), col, neck, bevel=0.08)       # back, down to the shoulders
        box(f"{cid}.hair", (1.36, 0.2, 0.3), (0, -0.52, 1.1), col, neck, bevel=0.06)     # bangs
        for s in (-1, 1):
            box(f"{cid}.hair", (0.22, 1.2, 1.9), (s * 0.71, 0.06, 0.45), col, neck, bevel=0.07)
    elif style == "curly":         # a cluster of curls
        import random
        rnd = random.Random(sum(map(ord, cid)))
        for _ in range(26):
            x, y, z = rnd.uniform(-0.62, 0.62), rnd.uniform(-0.45, 0.62), rnd.uniform(0.95, 1.45)
            if y < -0.3 and z < 1.15:
                continue
            sz = rnd.uniform(0.3, 0.42)
            box(f"{cid}.hair", (sz, sz, sz), (x, y, z), col, neck, bevel=0.12)
        back(0.5)
    elif style == "spiky":         # anime-style spikes on top
        top(0.22)
        back(0.7)
        for x, y, ry, rx in ((-0.42, -0.2, 20, -15), (-0.1, -0.3, 5, -25), (0.25, -0.25, -12, -20), (0.5, 0.0, -25, -5),
                             (-0.5, 0.3, 25, 10), (0.0, 0.25, 0, 15), (0.4, 0.4, -18, 18)):
            box(f"{cid}.hair", (0.32, 0.32, 0.6), (x, y, 1.42), col, neck, bevel=0.05, rot=(rx, ry, 45))
    elif style == "layered":       # long hair in stepped layers with a centre part and face-framing strands
        top(0.3)
        for s_ in (-1, 1):
            box(f"{cid}.hair", (0.62, 1.3, 0.2), (s_ * 0.34, 0.02, 1.3), col, neck, bevel=0.07, rot=(0, -6 * s_, 0))
            box(f"{cid}.hair", (0.24, 0.5, 1.9), (s_ * 0.6, -0.42, 0.4), col, neck, bevel=0.07)        # strands by the face
            box(f"{cid}.hair", (0.26, 0.9, 2.2), (s_ * 0.72, 0.2, 0.3), col, neck, bevel=0.07)
        for k, (wid, z, hgt) in enumerate(((1.46, 0.6, 1.6), (1.36, -0.5, 1.0), (1.1, -1.25, 0.7))):
            box(f"{cid}.hair", (wid, 0.32 - 0.04 * k, hgt), (0, 0.5 + 0.06 * k, z), col, neck, bevel=0.1)
    elif style == "swoop":         # boy's side-swept fringe with a few spikes
        top(0.3)
        back(0.62)
        box(f"{cid}.hair", (1.0, 0.3, 0.4), (-0.18, -0.5, 1.08), col, neck, bevel=0.08, rot=(0, -12, 0))
        box(f"{cid}.hair", (0.4, 0.3, 0.5), (0.48, -0.48, 1.12), col, neck, bevel=0.08, rot=(0, 18, 0))
        for x, y, ry, rx in ((-0.4, 0.0, 22, -10), (-0.05, -0.15, 0, -22), (0.35, 0.05, -20, -10), (0.0, 0.35, 0, 18)):
            box(f"{cid}.hair", (0.36, 0.36, 0.5), (x, y, 1.4), col, neck, bevel=0.06, rot=(rx, ry, 45))
        for s_ in (-1, 1):
            box(f"{cid}.hair", (0.18, 1.0, 0.5), (s_ * 0.66, 0.1, 1.0), col, neck, bevel=0.05)
    elif style == "afro":
        box(f"{cid}.hair", (1.9, 1.75, 1.15), (0, 0.15, 1.35), col, neck, bevel=0.45)


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
        elif t == "beard":
            box(f"{cid}.beard", (1.2, 0.12, 0.24), (0, FACE_Y - 0.02, 0.13), col, neck, bevel=0.08)      # chin, below the mouth
            for s in (-1, 1):
                box(f"{cid}.beard", (0.2, 0.12, 0.5), (s * 0.55, FACE_Y - 0.02, 0.38), col, neck, bevel=0.06)  # jaw sides
            box(f"{cid}.beard", (0.42, 0.1, 0.08), (0, FACE_Y - 0.04, 0.47), col, neck, bevel=0.03)  # moustache
        elif t == "bow":            # big hair bow on one side
            for dx, rz in ((-0.32, 25), (0.32, -25)):
                box(f"{cid}.bow", (0.5, 0.26, 0.38), (0.42 + dx * 0.9, 0.05, 1.38), col, neck, bevel=0.1, rot=(0, rz, 0))
            box(f"{cid}.bow", (0.2, 0.3, 0.22), (0.42, 0.05, 1.38), col, neck, bevel=0.06)
        elif t == "beanie":
            box(f"{cid}.beanie", (1.42, 1.3, 0.62), (0, 0.02, 1.36), col, neck, bevel=0.2)
            box(f"{cid}.beanie", (1.46, 1.34, 0.24), (0, 0.02, 1.12), a.get("band", shade(col, 0.8)), neck, bevel=0.08)
            box(f"{cid}.beanie", (0.36, 0.36, 0.3), (0, 0.02, 1.75), a.get("pom", "#FFFFFF"), neck, bevel=0.14)
        elif t == "headband":
            box(f"{cid}.headband", (1.38, 1.26, 0.16), (0, 0.02, 1.17), col, neck, bevel=0.06)
        elif t == "headphones":
            box(f"{cid}.phones", (1.5, 0.22, 0.16), (0, 0.0, 1.42), col, neck, bevel=0.06)
            for sx in (-1, 1):
                box(f"{cid}.phones", (0.12, 0.2, 0.7), (sx * 0.74, 0.0, 1.05), col, neck, bevel=0.04)
                box(f"{cid}.phones", (0.26, 0.6, 0.6), (sx * 0.74, 0.0, 0.62), a.get("cups", col), neck, bevel=0.12)
        elif t == "earrings":
            for sx in (-1, 1):
                box(f"{cid}.earring", (0.12, 0.12, 0.2), (sx * 0.68, -0.05, 0.3), col, neck, bevel=0.05)
        elif t == "backpack":       # on the back, straps over the shoulders
            d = BODIES[BODY_STYLE]["torso_d"]
            box(f"{cid}.backpack", (1.3, 0.6, 1.5), (0, d / 2 + 0.3, 1.05), col, chest, bevel=0.15)
            box(f"{cid}.backpack", (1.0, 0.25, 0.6), (0, d / 2 + 0.66, 0.75), shade(col, 0.85), chest, bevel=0.1)
            for sx in (-1, 1):
                box(f"{cid}.strap", (0.18, d + 0.08, 0.14), (sx * 0.42, 0, 2.0), shade(col, 0.7), chest, bevel=0.04)
                box(f"{cid}.strap", (0.18, 0.08, 1.2), (sx * 0.42, -d / 2 - 0.04, 1.4), shade(col, 0.7), chest, bevel=0.04)
        elif t == "fedora":
            box(f"{cid}.hat", (1.85, 1.75, 0.07), (0, 0.02, 1.24), col, neck, bevel=0.03)
            box(f"{cid}.hat", (1.3, 1.2, 0.55), (0, 0.02, 1.53), col, neck, bevel=0.1)
            box(f"{cid}.hat", (1.33, 1.23, 0.12), (0, 0.02, 1.33), a.get("band", "#7A2A2A"), neck, bevel=0.03)


# ---------------------------------------------------------------- torso detail

def build_torso(c, body, width_k=1.0):
    t, cid = c["torso"], c["id"]
    w, col, acc = t.get("width", 2.0) * width_k, t["color"], t.get("accent", "#FFFFFF")
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
    elif d == "stripes":           # rugby/striped tee: bands all the way round
        for z in (0.25, 0.75, 1.25, 1.75):
            box(f"{cid}.stripe", (w + 0.02, 1.02, 0.24), (0, 0, z), acc, body, bevel=0.03)
    elif d == "cardigan":
        box(f"{cid}.blouse", (0.6, 0.06, 2.0), (0, fy, 1.0), acc, body, bevel=0.03)
        for z in (0.4, 0.85, 1.3):
            box(f"{cid}.button", (0.1, 0.06, 0.1), (0.4, fy - 0.02, z), "#E8D9B0", body, bevel=0.03)
    elif d == "sweater":
        box(f"{cid}.hem", (w + 0.02, 1.02, 0.2), (0, 0, 0.1), acc, body, bevel=0.04)
        box(f"{cid}.collar", (0.8, 1.04, 0.14), (0, 0, 1.95), acc, body, bevel=0.04)
    elif d == "pajamas":           # dotted pajama top with piped collar
        for i in range(12):
            box(f"{cid}.dot", (0.14, 0.05, 0.14), (-0.7 + (i % 4) * 0.47 + (0.23 if (i // 4) % 2 else 0), fy - 0.01,
                                                   0.35 + (i // 4) * 0.6), acc, body, bevel=0.03)
        box(f"{cid}.collar", (0.9, 1.04, 0.16), (0, 0, 1.95), acc, body, bevel=0.04)
        box(f"{cid}.placket", (0.08, 0.06, 1.9), (0, fy - 0.01, 1.0), acc, body, bevel=0.02)
    elif d == "suit":              # blazer over white shirt and tie
        box(f"{cid}.shirt", (0.6, 0.06, 2.0), (0, fy, 1.0), "#F4F4F4", body, bevel=0.03)
        box(f"{cid}.tie", (0.2, 0.08, 1.2), (0, fy - 0.02, 1.25), acc, body, bevel=0.03)
        box(f"{cid}.knot", (0.24, 0.09, 0.18), (0, fy - 0.03, 1.88), acc, body, bevel=0.04)
        for s in (-1, 1):
            box(f"{cid}.lapel", (0.4, 0.06, 0.95), (s * 0.36, fy - 0.01, 1.45), shade(col, 0.8), body, bevel=0.03, rot=(0, -10 * s, 0))
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
    B = BODIES[BODY_STYLE]
    root = empty(cid, loc=loc)
    root.rotation_euler.z = math.radians(rot_z)
    root.scale = (c.get("scale", 1.0),) * 3
    root["blockmate"] = cid
    root["leg_w"] = B["leg_w"]

    body = empty(f"{cid}.body", root, (0, 0, B["leg"]))
    torso = empty(f"{cid}.torso_grp", body)
    torso.scale = (1.0, B["torso_d"], B["torso_h"] / 2.0)
    w = build_torso(c, torso, B["width_k"])
    sl = c["sleeves"]
    stripes = c["torso"].get("detail") == "stripes" and sl["length"] == "long"

    for side, s in (("L", 1), ("R", -1)):
        leg = empty(f"{cid}.leg.{side}", body, (s * B["leg_x"], 0, 0))
        lw, pants_len = B["leg_w"], B["leg"] - 0.36
        box(f"{cid}.pants", (lw, lw, pants_len), (0, 0, -pants_len / 2), c["pants"], leg, bevel=0.06)
        box(f"{cid}.shoe", (lw + 0.04, lw + 0.14, 0.36), (0, -0.05, -B["leg"] + 0.18), c["shoes"], leg, bevel=0.08)
        if BODY_STYLE == "slim":   # sole + lace strip read as a real sneaker
            box(f"{cid}.sole", (lw + 0.06, lw + 0.16, 0.1), (0, -0.05, -B["leg"] + 0.05), c.get("soles", "#F2F2F2"), leg, bevel=0.03)

        arm = empty(f"{cid}.arm.{side}", body, (s * (w / 2 + B["arm_w"] / 2 + 0.02), 0, B["torso_h"] - 0.2))
        aw, alen = B["arm_w"], B["arm"]
        sleeve_len = alen * (0.78 if sl["length"] == "long" else 0.35)
        box(f"{cid}.sleeve", (aw, aw, sleeve_len), (0, 0, 0.2 - sleeve_len / 2), sl["color"], arm, bevel=0.06)
        if stripes:
            for k in range(int(sleeve_len / 0.5)):
                box(f"{cid}.stripe", (aw + 0.02, aw + 0.02, 0.2), (0, 0, 0.05 - 0.5 * k - 0.25), c["torso"].get("accent", "#FFFFFF"), arm, bevel=0.03)
        skin_len = alen - sleeve_len
        box(f"{cid}.skin", (aw - 0.04, aw - 0.04, skin_len), (0, 0, 0.2 - sleeve_len - skin_len / 2 + 0.02), c["skin"], arm,
            bevel=0.08)
        if c["torso"].get("detail") == "trench":
            box(f"{cid}.coat", (lw + 0.01, lw + 0.01, 0.9), (0, 0, -0.44), c["torso"]["color"], leg, bevel=0.05)

    neck = empty(f"{cid}.neck", body, (0, 0, B["torso_h"]))
    neck.scale = (B["head"],) * 3
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
    _decal_mats.clear()


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
