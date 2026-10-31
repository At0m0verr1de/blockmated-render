"""Render every shot of a reel to out/<id>/shots/NN.mp4.

blender -b -P blender/render_reel.py -- out/<id>/timing.json [--only 3,4] [--force] [--preview]
timing.json is the content spec plus per-shot start/end seconds (written by pipeline/voice.py).
--preview renders at half resolution with fewer samples, for quick checks.
"""
import copy
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import anim  # noqa: E402
import blocky  # noqa: E402
import sets  # noqa: E402
import kit  # noqa: E402
import sets_fixed  # noqa: E402
import sets_study  # noqa: E402

args = sys.argv[sys.argv.index("--") + 1:]
timing_path = Path(args[0])
only = set()
if "--only" in args:
    only = {int(i) for i in args[args.index("--only") + 1].split(",")}
force = "--force" in args
preview = "--preview" in args

spec = json.loads(timing_path.read_text())
cast = blocky.load_cast()
blocky.FACE_STYLE = spec.get("face_style", "geo")
blocky.BODY_STYLE = spec.get("body", "classic")   # "slim" = longer legs, smaller head
out_dir = timing_path.parent / ("shots_preview" if preview else "shots")
out_dir.mkdir(parents=True, exist_ok=True)


def facing(at, target):
    return math.degrees(math.atan2(target[0] - at[0], -(target[1] - at[1])))


def add_prop(kind, cid, a=None):
    arm = bpy.data.objects[f"{cid}.arm.R"]
    body = bpy.data.objects[f"{cid}.body"]
    if kind == "can":
        sets.soda_can((0, -0.5, -2.0), (a or {}).get("can_color", "#E2526B"), arm, s=0.75)
    elif kind == "carrot":
        blocky.box(f"{cid}.carrot", (0.3, 0.3, 1.0), (0, -0.5, -2.1), "#F08A2A", arm, bevel=0.1)
        blocky.box(f"{cid}.carrot.top", (0.36, 0.36, 0.3), (0, -0.5, -1.5), "#7CC444", arm, bevel=0.08)
        anim.key_rot(arm, 1, -100, 0, 20)
    elif kind == "phone":
        arm_l = bpy.data.objects[f"{cid}.arm.L"]
        blocky.box(f"{cid}.phone", (0.16, 0.5, 0.8), (-0.2, -0.3, -1.9), "#1A1A1A", arm_l, bevel=0.05)
    elif kind == "pencil":
        blocky.box(f"{cid}.pencil", (0.14, 1.0, 0.14), (0, -0.6, -1.7), "#F2C230", arm, bevel=0.04)
    elif kind == "crate":
        blocky.box(f"{cid}.crate", (2.4, 1.4, 1.1), (0, -1.3, 0.9), "#B9874B", body, bevel=0.06)
        for i in range(4):
            sets.soda_can((-0.8 + i * 0.53, -1.3, 1.45), sets.CAN_COLORS[i], body, s=0.6)
        for side in ("L", "R"):
            anim.key_rot(bpy.data.objects[f"{cid}.arm.{side}"], 1, -60, 0, 25 if side == "R" else -25)


def machine_fx(m, fx, n):
    if not fx or not m:
        return
    glass_bsdf = m["glow"].data.materials[0].node_tree.nodes["Principled BSDF"]
    sock = glass_bsdf.inputs["Emission Strength"]
    if fx.get("glow_down"):
        sock.default_value = 2.5
        sock.keyframe_insert("default_value", frame=1)
        sock.keyframe_insert("default_value", frame=int(n * 0.5))
        sock.default_value = 0.0
        sock.keyframe_insert("default_value", frame=n)
    if fx.get("return_flash"):
        r = m["ret"].data.materials[0].node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]
        for i, f in enumerate(range(1, n + 1, 6)):
            r.default_value = 8 if i % 2 else 0.5
            r.keyframe_insert("default_value", frame=f)
    if fx.get("glow_up"):
        sock.default_value = 0.8
        sock.keyframe_insert("default_value", frame=1)
        sock.default_value = fx.get("glow_max", 4.0)
        sock.keyframe_insert("default_value", frame=n)
    if fx.get("pulse"):
        s = m["sign"].data.materials[0].node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]
        for i, f in enumerate(range(1, n + 1, 8)):
            s.default_value = 7 if i % 2 else 2.5
            s.keyframe_insert("default_value", frame=f)
    if "return_on" in fx:
        r = m["ret"].data.materials[0].node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]
        f = max(1, int(fx["return_on"] * n))
        r.default_value = 0
        r.keyframe_insert("default_value", frame=f - 1)
        r.default_value = 8
        r.keyframe_insert("default_value", frame=f)
    if fx.get("shake"):
        root = m["root"]
        base = root.location.copy()
        for i, f in enumerate(range(1, 20, 2)):
            d = 0.06 if i % 2 else -0.06
            anim.key_loc(root, f, (base.x + d, base.y, base.z))
        anim.key_loc(root, 21, base)
    if "drop" in fx:
        f0 = max(1, int(fx["drop"] * n))
        x, y, _ = m["can_spawn"]
        can = sets.soda_can((x, 3.0, 1.55), fx.get("drop_color", "#7B4FD6"), None, s=0.8)
        for part in [can] + list(can.children_recursive):
            part.hide_render = True
            part.keyframe_insert("hide_render", frame=f0 - 1)
            part.hide_render = False
            part.keyframe_insert("hide_render", frame=f0)
        anim.key_loc(can, f0, (x, 3.0, 1.55))
        anim.key_loc(can, f0 + 5, (x, 3.0, 0.6))
        anim.key_loc(can, f0 + 8, (x, 3.0, 0.75))
        anim.key_loc(can, f0 + 11, (x, 3.0, 0.6))


FRAMES = {  # shot size -> (distance, look-point drop below the head centre); lens 35, portrait frame
    "close": (5.5, 0.6), "medium": (8.5, 1.4), "cowboy": (10.5, 2.0), "full": (13.0, 2.8), "wide": (18.0, 3.2),
}


def frame_cam(f):
    """Camera from a framing request instead of coordinates, e.g. {"on": "tc_girl", "size": "medium", "angle": 25}.
    on: one actor id or a list (framed on their centre); size: close/medium/cowboy/full/wide;
    angle: degrees around the (first) actor from straight in front (+ = toward their left); rise: extra camera height;
    lens: default 35. Uses the actors as built at frame 1 (after sitting), so it follows sit/scale."""
    bpy.context.scene.frame_set(1)
    ids = f["on"] if isinstance(f["on"], list) else [f["on"]]
    heads = []
    for cid in ids:
        neck = bpy.data.objects[f"{cid}.neck"]
        heads.append(neck.matrix_world @ Vector((0, 0, 0.62)))
    centre = sum(heads, Vector((0, 0, 0))) / len(heads)
    root = bpy.data.objects[ids[0]]
    rz = root.rotation_euler.z + math.radians(f.get("angle", 0))
    dist, drop = FRAMES[f.get("size", "medium")]
    dist *= f.get("dist_k", 1.0)
    if len(ids) > 1:   # pull back so everyone fits across the narrow portrait frame
        spread = max((h - centre).length for h in heads)
        dist = max(dist, spread * 3.4 + 2.5)
    k = root.scale.z
    look = centre - Vector((0, 0, drop * k))
    pos = look + Vector((math.sin(rz), -math.cos(rz), 0)) * dist   # actors face (sin rz, -cos rz)
    pos.z = look.z + 0.35 * k + f.get("rise", 0.0)
    return {"pos": list(pos), "look": list(look), "lens": f.get("lens", 35)}


def key_light(c, strength=1.0):
    """Soft key from above the camera onto the framed subject, so close-ups never fall into a dark corner.
    Energy grows with distance so the face gets about the same light at any shot size."""
    pos, look = Vector(c["pos"]), Vector(c["look"])
    d = (look - pos).length
    side = Vector((-(look - pos).y, (look - pos).x, 0)).normalized()   # a little to the camera's left
    lp = pos + Vector((0, 0, 2.5)) + side * 1.8
    li = bpy.data.lights.new("key", "AREA")
    li.size = 3.0
    li.energy = min(2500, 8 * (lp - look).length ** 2) * strength
    li.color = (1.0, 0.94, 0.86)
    ob = bpy.data.objects.new("key", li)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = lp
    tgt = blocky.empty("key.target", loc=tuple(look))
    con = ob.constraints.new("TRACK_TO")
    con.target, con.track_axis, con.up_axis = tgt, "TRACK_NEGATIVE_Z", "UP_Y"


def camera(shot, n):
    c = frame_cam(shot["frame"]) if "frame" in shot else shot["cam"]
    if "frame" in shot and shot.get("key", spec.get("key_light", True)) is not False:
        key_light(c if isinstance(c, dict) else spec["cams"][c], float(shot.get("key", 1.0) or 1.0))
    c = dict(spec["cams"][c]) if isinstance(c, str) else dict(c)
    cam = blocky.add_camera(tuple(c["pos"]), tuple(c["look"]), lens=c.get("lens", 35))
    target = bpy.data.objects["cam.target"]
    push = shot.get("push", 0.0)
    if push:
        p0 = cam.location.copy()
        look = target.location.copy()
        anim.key_loc(cam, 1, p0)
        anim.key_loc(cam, n, p0.lerp(look, push))
    if "pan_to" in shot:
        anim.key_loc(target, 1, target.location.copy())
        anim.key_loc(target, n, tuple(shot["pan_to"]))
    if not shot.get("static"):
        drift(cam)
    # Punch-in: long shots cut to a tighter angle on a word near the middle (craftee cuts every 1-2 s)
    cut = punch_frame(shot, n)
    if cut:
        look = target.location.copy()
        start = cam.location.copy().lerp(look, push)
        dist = (look - start).length
        new = max(dist * 0.6, min(dist, 3.2))  # 40% tighter, but never closer than ~3 units
        p1 = look + (start - look).normalized() * new
        cam2 = bpy.data.objects.new("cam2", cam.data.copy())
        bpy.context.scene.collection.objects.link(cam2)
        cam2.location = p1
        tr = cam2.constraints.new("TRACK_TO")
        tr.target, tr.track_axis, tr.up_axis = target, "TRACK_NEGATIVE_Z", "UP_Y"
        drift(cam2, seed=7)
        sc = bpy.context.scene
        sc.timeline_markers.new("A", frame=1).camera = cam
        sc.timeline_markers.new("B", frame=cut).camera = cam2
    return cam


def drift(cam, seed=0):
    """Subtle handheld float so no shot is ever perfectly still."""
    if not (cam.animation_data and cam.animation_data.action):
        cam.keyframe_insert("location", frame=1)
    for fc in cam.animation_data.action.fcurves:
        if fc.data_path == "location":
            mod = fc.modifiers.new("NOISE")
            mod.strength, mod.scale, mod.phase = 0.08, 45, seed * 10 + fc.array_index * 23


def punch_frame(shot, n):
    """Frame to cut to the tighter angle, or None. Only for shots over ~2.4 s, cut on a word start."""
    if n < 58 or shot.get("no_punch"):
        return None
    starts = [round((w["start"] - shot["start"]) * anim.FPS) for w in shot.get("words", [])]
    starts = [f for f in starts if n * 0.3 < f < n * 0.75]
    return min(starts, key=lambda f: abs(f - n / 2)) if starts else None


shot_words, shot_start = [], 0.0


def actor(a, n, idx):
    c = copy.deepcopy(cast[a["id"]])
    if "scale" in a:
        c["scale"] = a["scale"]
    e = a.get("expr", c["face"].get("expression", "neutral"))
    timeline = [(0.0, e)] if isinstance(e, str) else [(float(fr), ex) for fr, ex in e]
    at = a["at"]
    face = a.get("face", 0)
    if "face_to" in a:
        face = facing(at, a["face_to"])
    root = blocky.build(c, loc=(at[0], at[1], 0), rot_z=face, exprs=list(dict.fromkeys(ex for _, ex in timeline)))
    cid = c["id"]
    anim.face_timeline(cid, n, timeline)
    anim.blink(cid, n, seed=idx + len(cid), every=a.get("blink_every"), at=a.get("blink_at"))
    if "sit" in a:
        (anim.sit_cross if a.get("cross") else anim.sit)(cid, n, a["sit"])
    if a.get("holding"):
        add_prop(a["holding"], cid, a)
    for item in a.get("do", [["idle"]]):
        name, params = item[0], dict(item[1] if len(item) > 1 else {})
        # timing: {"word": k} starts on the k-th word of this shot, {"at": 0.4} at 40% of the shot
        f0 = 1
        if "word" in params:
            ws = shot_words[params.pop("word")] if shot_words else None
            f0 = max(1, round((ws["start"] - shot_start) * anim.FPS)) if ws else 1
        elif "at" in params:
            f0 = max(1, round(params.pop("at") * n))
        before = _keys(cid) if f0 > 1 else None
        m = n - f0 + 1
        fn = anim.ACTIONS[name]
        if name in ("walk", "run"):
            fn(cid, m, start=at, **params)
        elif name == "idle":
            fn(cid, m, seed=idx)
        else:
            fn(cid, m, **params)
        if before is not None:
            _shift_new(cid, before, f0 - 1)
    return root


def _char_objects(cid):
    return [o for o in bpy.data.objects if o.name == cid or o.name.startswith(cid + ".")]


def _keys(cid):
    seen = set()
    for o in _char_objects(cid):
        ad = o.animation_data
        if ad and ad.action:
            for fc in ad.action.fcurves:
                for kp in fc.keyframe_points:
                    seen.add((o.name, fc.data_path, fc.array_index, round(kp.co.x)))
    return seen


def _shift_new(cid, before, df):
    """Move keyframes an action just added so it starts df frames later (it holds the earlier pose until then)."""
    for o in _char_objects(cid):
        ad = o.animation_data
        if not (ad and ad.action):
            continue
        for fc in ad.action.fcurves:
            new = [kp for kp in fc.keyframe_points if (o.name, fc.data_path, fc.array_index, round(kp.co.x)) not in before]
            for kp in sorted(new, key=lambda k: -k.co.x):
                kp.co.x += df
                kp.handle_left.x += df
                kp.handle_right.x += df
            fc.update()


def hud(items):
    """On-screen text fixed to the camera, e.g. {"text": "STRIKE 1/3", "pos": [0, 0.3], "size": 0.06, "color": "#FF2B3A"}.
    pos is in frame units: x and y from -0.5 (left/bottom) to 0.5 (right/top)."""
    cam = bpy.context.scene.camera
    if not cam or not items:
        return
    d = 0.6  # close to the lens so nothing in the scene can cover it
    vh = 36.0 / cam.data.lens * d          # portrait frame: the 36 mm sensor spans the height
    vw = vh * 9 / 16
    for it in items:
        ob = sets.text(it["text"], (it.get("pos", [0, 0])[0] * vw, it.get("pos", [0, 0])[1] * vh, -d),
                       it.get("size", 0.06) * vh, it.get("color", "#FFFFFF"), parent=cam, rot=(0, 0, 0), emit=4.0)
        ob.data.extrude = 0.0


def grade(kind):
    """Colour grade in the compositor. "warm": golden lift/gain, a touch more contrast and a soft vignette."""
    if not kind:
        return
    sc = bpy.context.scene
    try:
        sc.view_settings.look = "Medium High Contrast"
    except TypeError:
        pass
    sc.use_nodes = True
    nt = sc.node_tree
    for nd in list(nt.nodes):
        nt.nodes.remove(nd)
    rl = nt.nodes.new("CompositorNodeRLayers")
    cb = nt.nodes.new("CompositorNodeColorBalance")
    cb.correction_method = "LIFT_GAMMA_GAIN"
    cb.lift = (1.01, 1.0, 0.98)
    cb.gamma = (1.01, 1.0, 0.97)
    cb.gain = (1.05, 1.01, 0.95)
    mask = nt.nodes.new("CompositorNodeEllipseMask")
    mask.width, mask.height = 0.95, 0.9
    blur = nt.nodes.new("CompositorNodeBlur")
    blur.filter_type = "FAST_GAUSS"
    blur.use_relative = True
    blur.factor_x = blur.factor_y = 40
    ramp = nt.nodes.new("CompositorNodeMapRange")
    ramp.inputs["To Min"].default_value = 0.72
    mix = nt.nodes.new("CompositorNodeMixRGB")
    mix.blend_type = "MULTIPLY"
    comp = nt.nodes.new("CompositorNodeComposite")
    nt.links.new(rl.outputs["Image"], cb.inputs["Image"])
    nt.links.new(mask.outputs["Mask"], blur.inputs["Image"])
    nt.links.new(blur.outputs["Image"], ramp.inputs["Value"])
    nt.links.new(cb.outputs["Image"], mix.inputs[1])
    nt.links.new(ramp.outputs["Value"], mix.inputs[2])
    nt.links.new(mix.outputs["Image"], comp.inputs["Image"])


PROGRESS = timing_path.parent / "progress.json"


def report(i, n, frame):
    """Per-frame progress for tools/monitor.py."""
    import time
    PROGRESS.write_text(json.dumps({"shot": i, "frame": frame, "frames": n, "preview": preview, "t": time.time()}))


def render_shot(i, shot):
    out = out_dir / f"{i:02d}.mp4"
    if out.exists() and not force and not only:
        print(f"skip {out.name}")
        return
    n = max(12, round((shot["end"] - shot["start"]) * anim.FPS))
    blocky.reset_scene()
    w, h = (540, 960) if preview else (1080, 1920)
    blocky.setup_render(w, h, samples=8 if preview else 24)
    sc = bpy.context.scene
    sc.render.fps = anim.FPS
    sc.frame_start, sc.frame_end = 1, n
    m = None
    if shot["set"] == "hallway":
        m = sets.hallway(shot.get("time", "day"), [tuple(l) for l in spec.get("labels", [])])
    elif shot["set"] == "classroom":
        sets.classroom(shot.get("time", "day"), spec.get("board"))
    elif shot["set"] == "bedroom":
        sets.bedroom(shot.get("time", "night"))
    elif shot["set"] in sets_fixed.SETS:
        sets_fixed.SETS[shot["set"]](shot.get("time", "day"), spec)
    elif shot["set"] in sets_study.SETS:
        sets_study.SETS[shot["set"]](shot.get("time", "day"), spec)
    if shot.get("petals"):
        sets_study.petals(n)
    # per-shot props: {"van": {...}} or {"kit": "...", "name": "...", "at": [x, y, z], "rot": deg, "scale": s}
    for o in shot.get("objects", []):
        if "van" in o:
            sets_fixed.van(**o["van"])
        else:
            kit.place(o["kit"], o["name"], tuple(o.get("at", (0, 0, 0))), o.get("rot", 0), o.get("scale", 1))
    global shot_words, shot_start
    shot_words, shot_start = shot.get("words", []), shot["start"]
    for k, a in enumerate(shot.get("actors", [])):
        actor(a, n, k)
    machine_fx(m, shot.get("machine"), n)
    camera(shot, n)
    hud(shot.get("hud", []))
    grade(spec.get("grade"))
    anim.smooth_all()
    sc.render.image_settings.file_format = "FFMPEG"
    sc.render.ffmpeg.format = "MPEG4"
    sc.render.ffmpeg.codec = "H264"
    sc.render.ffmpeg.constant_rate_factor = "HIGH"
    sc.render.ffmpeg.ffmpeg_preset = "GOOD"
    bpy.app.handlers.render_post.clear()
    bpy.app.handlers.render_post.append(lambda scene, *_: report(i, n, scene.frame_current))
    report(i, n, 0)
    tmp = f"tmp{i:02d}_"
    sc.render.filepath = str(out_dir / tmp)
    bpy.ops.render.render(animation=True)
    next(out_dir.glob(tmp + "*")).replace(out)
    print(f"rendered {out.name} ({n} frames)")


for i, shot in enumerate(spec["shots"]):
    if only and i not in only:
        continue
    render_shot(i, shot)
print("all shots done")
