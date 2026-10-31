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

sys.path.insert(0, str(Path(__file__).resolve().parent))
import anim  # noqa: E402
import blocky  # noqa: E402
import sets  # noqa: E402

args = sys.argv[sys.argv.index("--") + 1:]
timing_path = Path(args[0])
only = set()
if "--only" in args:
    only = {int(i) for i in args[args.index("--only") + 1].split(",")}
force = "--force" in args
preview = "--preview" in args

spec = json.loads(timing_path.read_text())
cast = blocky.load_cast()
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


def camera(shot, n):
    c = shot["cam"]
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
    anim.blink(cid, n, seed=idx + len(cid))
    if "sit" in a:
        anim.sit(cid, n, a["sit"])
    if a.get("holding"):
        add_prop(a["holding"], cid, a)
    for item in a.get("do", [["idle"]]):
        name, params = item[0], (item[1] if len(item) > 1 else {})
        fn = anim.ACTIONS[name]
        if name in ("walk", "run"):
            fn(cid, n, start=at, **params)
        elif name == "idle":
            fn(cid, n, seed=idx)
        else:
            fn(cid, n, **params)
    return root


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
        sets.classroom(shot.get("time", "day"))
    elif shot["set"] == "bedroom":
        sets.bedroom(shot.get("time", "night"))
    for k, a in enumerate(shot.get("actors", [])):
        actor(a, n, k)
    machine_fx(m, shot.get("machine"), n)
    camera(shot, n)
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
