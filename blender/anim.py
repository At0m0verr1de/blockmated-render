"""Keyframed actions for Blockmates characters.

Every action works on frames 1..n of a shot and only keys pivot rotations
(and the root/body location), so any action can run on any character.
Euler notes (character faces -Y):
  arm/leg rotation_euler.x = -90  -> limb points forward
  arm rotation_euler.y = +150 on R / -150 on L -> arm raised out and up
  body/neck rotation_euler.x = +deg -> lean/look forward and down
"""
import math

import bpy

FPS = 24
R = math.radians


def obj(cid, part=""):
    return bpy.data.objects[f"{cid}{'.' + part if part else ''}"]


def key_rot(ob, frame, x=None, y=None, z=None):
    e = ob.rotation_euler
    if x is not None:
        e.x = R(x)
    if y is not None:
        e.y = R(y)
    if z is not None:
        e.z = R(z)
    ob.keyframe_insert("rotation_euler", frame=frame)


def key_loc(ob, frame, loc):
    ob.location = loc
    ob.keyframe_insert("location", frame=frame)


def smooth_all():
    for ob in bpy.data.objects:
        ad = ob.animation_data
        if ad and ad.action:
            for fc in ad.action.fcurves:
                if fc.data_path == "hide_render":
                    continue
                for kp in fc.keyframe_points:
                    kp.interpolation = "BEZIER"
                    kp.easing = "AUTO"


def rest(cid, frame):
    for part in ("arm.L", "arm.R", "leg.L", "leg.R", "neck", "body"):
        key_rot(obj(cid, part), frame, 0, 0, 0)


def idle(cid, n, seed=0):
    """Small breathing bob + occasional head turn so nobody looks frozen."""
    body = obj(cid, "body")
    base = body.location.copy()
    for f in range(1, n + 1, 12):
        k = math.sin((f + seed * 7) / 12)
        key_loc(body, f, (base.x, base.y, base.z + 0.04 * k))
    neck = obj(cid, "neck")
    key_rot(neck, 1, 0, 0, 0)
    if n > 60:
        key_rot(neck, n // 2, 0, 0, 10 if seed % 2 else -10)
        key_rot(neck, n, 0, 0, 0)


def walk(cid, n, start, to, speed=4.0, stride=32):
    """Walk from start to `to` (x, y) at `speed` units/s, then stop."""
    root = obj(cid)
    dx, dy = to[0] - start[0], to[1] - start[1]
    dist = math.hypot(dx, dy)
    frames = max(2, min(n, int(dist / speed * FPS)))
    root.rotation_euler.z = math.atan2(dx, -dy)  # face the direction of travel
    root.keyframe_insert("rotation_euler", frame=1)
    key_loc(root, 1, (start[0], start[1], 0))
    key_loc(root, frames, (to[0], to[1], 0))
    for fc in root.animation_data.action.fcurves:
        if fc.data_path == "location":
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"
    period = 14 if speed < 6 else 9
    body = obj(cid, "body")
    bz = body.location.z
    for f in range(1, frames + 1, period // 2):
        s = 1 if (f // (period // 2)) % 2 == 0 else -1
        key_rot(obj(cid, "leg.L"), f, s * stride)
        key_rot(obj(cid, "leg.R"), f, -s * stride)
        key_rot(obj(cid, "arm.L"), f, -s * stride * 0.8)
        key_rot(obj(cid, "arm.R"), f, s * stride * 0.8)
        key_loc(body, f, (0, 0, bz + 0.12))
        key_loc(body, f + period // 4, (0, 0, bz))
    if speed >= 6:
        key_rot(body, 1, 10)
    rest(cid, frames + 4)
    key_loc(body, frames + 4, (0, 0, bz))


def wave(cid, n, side="R"):
    arm = obj(cid, f"arm.{side}")
    s = 1 if side == "R" else -1
    key_rot(arm, 1, 0, 0, 0)
    for i, f in enumerate(range(6, n - 6, 7)):
        key_rot(arm, f, 0, s * (150 if i % 2 else 125), 0)
    key_rot(arm, n, 0, s * 140, 0)


def point(cid, n, side="R"):
    key_rot(obj(cid, f"arm.{side}"), 1, 0, 0, 0)
    key_rot(obj(cid, f"arm.{side}"), 8, -90, 0, 0)


def give(cid, n):
    key_rot(obj(cid, "arm.R"), 1, 0, 0, 0)
    key_rot(obj(cid, "arm.R"), 14, -75, 0, 15)
    key_rot(obj(cid, "neck"), 14, 8, 0, 0)


def cross_arms(cid, n):
    for f in (1, n):
        key_rot(obj(cid, "arm.L"), f, -80, 0, -45)
        key_rot(obj(cid, "arm.R"), f, -80, 0, 45)
    key_rot(obj(cid, "neck"), 1, 0, 0, 0)
    key_rot(obj(cid, "neck"), n // 2, -6, 0, 18)


def lean_in(cid, n, body_deg=10, neck_deg=8):
    """Lean in until the forehead rests on glass in front.
    Stand the character so its root is ~1.4 units from the glass (see LEAN_GAP)."""
    for f, k in ((1, 0), (14, 1), (n, 1)):
        key_rot(obj(cid, "body"), f, body_deg * k)
        key_rot(obj(cid, "neck"), f, neck_deg * k)
        key_rot(obj(cid, "arm.L"), f, -22 * k, 0, -10 * k)
        key_rot(obj(cid, "arm.R"), f, -22 * k, 0, 10 * k)


LEAN_GAP = 1.42  # root-to-glass distance for lean_in at scale 1


def unlean(cid, n):
    key_rot(obj(cid, "body"), 1, 18)
    key_rot(obj(cid, "neck"), 1, 12)
    key_rot(obj(cid, "body"), 14, 0)
    key_rot(obj(cid, "neck"), 14, 0)


def drink(cid, n):
    arm = obj(cid, "arm.R")
    key_rot(arm, 1, 0, 0, 0)
    key_rot(arm, 10, -150, 0, 30)
    key_rot(obj(cid, "neck"), 10, -18)
    key_rot(arm, n - 8, -150, 0, 30)
    key_rot(arm, n, -70, 0, 20)
    key_rot(obj(cid, "neck"), n, 0)


def hold(cid, n):
    key_rot(obj(cid, "arm.R"), 1, -70, 0, 20)


def shock(cid, n):
    root = obj(cid)
    loc = root.location.copy()
    key_loc(root, 1, loc)
    key_loc(root, 5, (loc.x, loc.y, 0.7))
    key_loc(root, 10, loc)
    key_rot(obj(cid, "arm.L"), 1, 0, 0, 0)
    key_rot(obj(cid, "arm.R"), 1, 0, 0, 0)
    key_rot(obj(cid, "arm.L"), 5, 0, -150, 0)
    key_rot(obj(cid, "arm.R"), 5, 0, 150, 0)
    key_rot(obj(cid, "arm.L"), 16, -20, -40, 0)
    key_rot(obj(cid, "arm.R"), 16, -20, 40, 0)


def cheer(cid, n):
    for i, f in enumerate(range(1, n, 8)):
        up = 160 if i % 2 else 130
        key_rot(obj(cid, "arm.L"), f, 0, -up, 0)
        key_rot(obj(cid, "arm.R"), f, 0, up, 0)


def shrug(cid, n):
    for f, a in ((1, 0), (10, 1), (n - 6, 1), (n, 0.3)):
        key_rot(obj(cid, "arm.L"), f, -30 * a, -40 * a, 0)
        key_rot(obj(cid, "arm.R"), f, -30 * a, 40 * a, 0)
        key_rot(obj(cid, "neck"), f, 0, 12 * a, 0)


def sad(cid, n):
    key_rot(obj(cid, "neck"), 1, 0)
    key_rot(obj(cid, "neck"), 16, 22)
    key_rot(obj(cid, "body"), 16, 6)


def fan(cid, n):
    arm = obj(cid, "arm.R")
    for i, f in enumerate(range(1, n, 6)):
        key_rot(arm, f, -150 + (15 if i % 2 else 0), 0, 35)
    key_rot(obj(cid, "neck"), 1, -10)


def look_around(cid, n):
    neck = obj(cid, "neck")
    for f, a in ((1, 0), (n // 4, 35), (n // 2, -35), (3 * n // 4, 20), (n, 0)):
        key_rot(neck, f, 0, 0, a)


def look_through(cid, n):
    """Head turns slowly past someone without stopping."""
    neck = obj(cid, "neck")
    key_rot(neck, 1, 0, 0, -30)
    key_rot(neck, n, 0, 0, 35)


def turn(cid, n, to_deg):
    root = obj(cid)
    key_rot(root, 1, z=math.degrees(root.rotation_euler.z))
    key_rot(root, 10, z=to_deg)


def sit(cid, n, seat_top):
    """Sit with legs forward. seat_top is the chair surface height."""
    root = obj(cid)
    sc = root.scale.z
    body = obj(cid, "body")
    body.location.z = (seat_top + 0.5) / sc
    for side in ("L", "R"):
        key_rot(obj(cid, f"leg.{side}"), 1, -90)


def hug(cid, n):
    for f, k in ((1, 0), (8, 1), (n, 1)):
        key_rot(obj(cid, "arm.L"), f, -85 * k, 0, -40 * k)
        key_rot(obj(cid, "arm.R"), f, -85 * k, 0, 40 * k)
        key_rot(obj(cid, "body"), f, 8 * k)


def talk(cid, n):
    """Explaining with both hands, head bobbing."""
    for i, f in enumerate(range(1, n, 9)):
        a = i % 3
        key_rot(obj(cid, "arm.L"), f, -40 - 25 * (a == 0), 0, -15 - 10 * (a == 1))
        key_rot(obj(cid, "arm.R"), f, -40 - 25 * (a == 2), 0, 15 + 10 * (a == 1))
        key_rot(obj(cid, "neck"), f, 4 * (i % 2), 0, 8 * ((i % 4) - 1.5) / 1.5)


def phone(cid, n):
    key_rot(obj(cid, "arm.L"), 1, -128, 0, -58)
    for i, f in enumerate(range(1, n, 14)):
        key_rot(obj(cid, "neck"), f, -6 if i % 2 else 4, 0, 10 if i % 2 else -6)


ACTIONS = {
    "idle": idle, "walk": walk, "run": walk, "wave": wave, "point": point, "give": give,
    "cross_arms": cross_arms, "lean_in": lean_in, "unlean": unlean, "drink": drink, "hold": hold,
    "shock": shock, "cheer": cheer, "shrug": shrug, "sad": sad, "fan": fan,
    "look_around": look_around, "look_through": look_through, "turn": turn,
    "hug": hug, "talk": talk, "phone": phone,
}


def _show(group, frame, visible):
    for ob in [group] + list(group.children_recursive):
        ob.hide_render = not visible
        ob.keyframe_insert("hide_render", frame=frame)
        for fc in (ob.animation_data.action.fcurves if ob.animation_data else []):
            if fc.data_path == "hide_render":
                for kp in fc.keyframe_points:
                    kp.interpolation = "CONSTANT"


def face_timeline(cid, n, timeline):
    """timeline: [(fraction_of_shot, expression), ...] sorted; first entry should be at 0."""
    root = obj(cid)
    starts = [(max(1, int(fr * n)), ex) for fr, ex in timeline]
    for ex in root["faces"]:
        grp = obj(cid, f"face.{ex}")
        _show(grp, 1, ex == starts[0][1])
        for f, active in starts[1:]:
            _show(grp, f, ex == active)


def blink(cid, n, seed=0):
    """Blink every 2.5-4 s. Squashes each face's eye group."""
    root = obj(cid)
    rng = (seed * 37 + 11) % 29
    frames = list(range(18 + rng, n - 4, 60 + (seed * 13) % 36))
    for ex in root["faces"]:
        eyes = bpy.data.objects.get(f"{cid}.face.{ex}.eyes")
        if not eyes:
            continue
        eyes.keyframe_insert("scale", frame=1)
        for f in frames:
            for df, sz in ((0, 1.0), (2, 0.1), (4, 1.0)):
                eyes.scale = (1, 1, sz)
                eyes.keyframe_insert("scale", frame=f + df)
