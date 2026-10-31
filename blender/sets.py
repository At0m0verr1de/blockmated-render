"""Procedural sets for Blockmated, in the same blocky style as the characters.

Each builder returns a dict of named handles that shots can animate
(e.g. the vending machine's glass glow or RETURN button).
Coordinates: floor is z=0, characters face -Y by default, a kid is ~5.2 units tall.
"""
import math

import bpy

from blocky import box, empty, hex_rgba, mat


def emissive(color, strength):
    m = bpy.data.materials.new(f"e{color}")
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = hex_rgba(color)
    b.inputs["Emission"].default_value = hex_rgba(color)
    b.inputs["Emission Strength"].default_value = strength
    return m


def ebox(name, size, loc, color, strength, parent=None, bevel=0.03):
    ob = box(name, size, loc, color, parent, bevel=bevel)
    ob.data.materials[0] = emissive(color, strength)
    return ob


def text(body, loc, size, color, parent=None, rot=(90, 0, 0), emit=0.0, align="CENTER"):
    cu = bpy.data.curves.new(f"text.{body[:12]}", "FONT")
    cu.body = body
    cu.align_x = align
    cu.align_y = "CENTER"
    cu.size = size
    cu.extrude = 0.01
    ob = bpy.data.objects.new(cu.name, cu)
    bpy.context.scene.collection.objects.link(ob)
    ob.parent = parent
    ob.location = loc
    ob.rotation_euler = [math.radians(a) for a in rot]
    cu.materials.append(emissive(color, emit) if emit else mat(color))
    return ob


def area_light(loc, size, energy, color="#FFF4E0", rot=(0, 0, 0)):
    li = bpy.data.lights.new("area", "AREA")
    li.size = size
    li.energy = energy
    li.color = hex_rgba(color)[:3]
    ob = bpy.data.objects.new("area", li)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = [math.radians(a) for a in rot]
    return ob


def point_light(loc, energy, color, radius=0.5):
    li = bpy.data.lights.new("point", "POINT")
    li.energy = energy
    li.color = hex_rgba(color)[:3]
    li.shadow_soft_size = radius
    ob = bpy.data.objects.new("point", li)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    return ob


def set_world(color, strength):
    bg = bpy.context.scene.world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = hex_rgba(color)
    bg.inputs["Strength"].default_value = strength


def room_shell(width, depth, height, floor, wall, trim, back_y):
    box("floor", (width, depth, 0.2), (0, back_y - depth / 2, -0.1), floor, None, bevel=0, rough=0.7)
    box("wall.back", (width, 0.4, height), (0, back_y + 0.2, height / 2), wall, None, bevel=0, rough=0.9)
    box("wall.trim", (width, 0.5, 1.4), (0, back_y + 0.1, 0.7), trim, None, bevel=0.02)
    for s in (-1, 1):
        box("wall.side", (0.4, depth, height), (s * width / 2, back_y - depth / 2, height / 2), wall, None, bevel=0, rough=0.9)
    box("ceiling", (width, depth, 0.3), (0, back_y - depth / 2, height + 0.15), "#F2EEE6", None, bevel=0)


def checker_floor(ob, a, b, scale):
    m = bpy.data.materials.new("checker")
    m.use_nodes = True
    nt = m.node_tree
    tex = nt.nodes.new("ShaderNodeTexChecker")
    tex.inputs["Color1"].default_value = hex_rgba(a)
    tex.inputs["Color2"].default_value = hex_rgba(b)
    tex.inputs["Scale"].default_value = scale
    coord = nt.nodes.new("ShaderNodeTexCoord")
    nt.links.new(coord.outputs["Object"], tex.inputs["Vector"])
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 0.35
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    ob.data.materials[0] = m


# ------------------------------------------------------------------ soda can

def _cyl(name, r, h, z, color, parent, rough=0.35, metal=0.0):
    bpy.ops.mesh.primitive_cylinder_add(vertices=28, radius=r, depth=h, location=(0, 0, z))
    ob = bpy.context.active_object
    ob.name = name
    ob.data.materials.append(mat(color, rough))
    if metal:
        ob.data.materials[0].node_tree.nodes["Principled BSDF"].inputs["Metallic"].default_value = metal
    for poly in ob.data.polygons:
        poly.use_smooth = True
    ob.data.use_auto_smooth = True
    ob.data.auto_smooth_angle = math.radians(40)
    ob.parent = parent
    ob.location = (0, 0, z)
    return ob


def soda_can(loc, color, parent=None, s=1.0, label=None):
    """A real-looking soda can about 0.9*s tall, standing on loc. Returns its root empty (animate that)."""
    root = empty("can", parent, loc)
    root.scale = (s, s, s)
    _cyl("can.body", 0.3, 0.78, 0.45, color, root)
    _cyl("can.band", 0.305, 0.3 if label else 0.26, 0.47, "#F8F4E8", root)
    if not label:
        _cyl("can.stripe", 0.306, 0.06, 0.47, color, root)
    _cyl("can.top", 0.27, 0.08, 0.88, "#C9CED8", root, rough=0.25, metal=0.8)
    _cyl("can.tab", 0.07, 0.03, 0.93, "#A0A8B4", root, rough=0.25, metal=0.8)
    _cyl("can.bottom", 0.26, 0.08, 0.04, "#C9CED8", root, rough=0.25, metal=0.8)
    if label:
        text(label, (0, -0.32, 0.47), 0.1, "#101010", root)
    return root


# ------------------------------------------------------------------ vending machine

CAN_COLORS = ["#E2526B", "#3FA7D6", "#F2C230", "#7CC444", "#B79CF0", "#F08A2A", "#3FD6A0", "#FFFFFF"]


def vending_machine(loc, labels=None):
    """Front face is at loc.y - 1.3. Returns handles: root, glass, sign, ret, can_spawn, tray."""
    root = empty("machine", loc=loc)
    body = "#253B6E"
    # hollow cabinet: the can compartment (x -2.0..0.8, z 1.9..7.2) is open at the front
    box("machine.back", (4.6, 0.3, 8.6), (0, 1.15, 4.3), body, root, bevel=0.08)
    box("machine.side", (0.3, 2.6, 8.6), (-2.15, 0, 4.3), body, root, bevel=0.08)
    box("machine.column", (1.5, 2.6, 8.6), (1.55, 0, 4.3), body, root, bevel=0.08)
    box("machine.base", (4.6, 2.6, 1.9), (0, 0, 0.95), body, root, bevel=0.08)
    box("machine.head", (4.6, 2.6, 1.4), (0, 0, 7.9), body, root, bevel=0.08)
    box("machine.top", (4.8, 2.7, 0.4), (0, 0, 8.6), "#1A2A50", root, bevel=0.1)
    sign = ebox("machine.sign", (4.0, 0.1, 1.0), (0, -1.33, 7.85), "#7FF5FF", 3.0, root)
    text("MEMORIES", (0, -1.42, 7.85), 0.62, "#0B1C3A", root)
    # lit back panel behind the cans (this is what "glows"), then clear glass in front
    glow = ebox("machine.backlight", (2.8, 0.1, 5.0), (-0.65, 0.9, 4.5), "#BFEFFF", 0.8, root)
    glass = box("machine.glass", (2.9, 0.06, 5.2), (-0.65, -1.3, 4.5), "#DDF6FF", root, bevel=0.02, rough=0.05)
    gm = bpy.data.materials.new("glass")
    gm.use_nodes = True
    gb = gm.node_tree.nodes["Principled BSDF"]
    gb.inputs["Base Color"].default_value = hex_rgba("#DDF6FF")
    gb.inputs["Roughness"].default_value = 0.05
    gb.inputs["Alpha"].default_value = 0.07
    gm.blend_method = "BLEND"
    gm.shadow_method = "NONE"
    glass.data.materials[0] = gm
    box("machine.frame", (3.1, 0.12, 0.2), (-0.65, -1.3, 7.15), "#1A2A50", root, bevel=0.03)
    box("machine.frame", (3.1, 0.12, 0.2), (-0.65, -1.3, 1.85), "#1A2A50", root, bevel=0.03)
    for row in range(4):
        z = 2.6 + row * 1.25
        box("machine.shelf", (2.8, 1.6, 0.08), (-0.65, -0.4, z - 0.35), "#C9D3E0", root, bevel=0.02)
        for col in range(5):
            colr = CAN_COLORS[(row * 5 + col * 3) % len(CAN_COLORS)]
            soda_can((-1.75 + col * 0.55, -0.6, z - 0.31), colr, root, s=0.7)
    # hero cans with labels, front row bottom shelf
    for i, (label, colr) in enumerate(labels or []):
        x = -1.5 + i * 1.6
        soda_can((x, -0.85, 2.05), colr, root, s=1.15, label=label)
    # control panel
    box("machine.panel", (1.2, 0.1, 5.2), (1.6, -1.32, 4.5), "#1A2A50", root, bevel=0.04)
    for r in range(3):
        for c in range(3):
            box("key", (0.24, 0.08, 0.2), (1.32 + c * 0.28, -1.4, 5.6 - r * 0.3), "#D8DEE8", root, bevel=0.03)
    box("slot", (0.5, 0.08, 0.12), (1.6, -1.4, 4.3), "#0A0A0A", root, bevel=0.02)
    text("RETURN", (1.6, -1.4, 3.75), 0.16, "#FFFFFF", root)
    ret = ebox("machine.return", (0.5, 0.12, 0.35), (1.6, -1.42, 3.35), "#D63A3A", 0.0, root, bevel=0.06)
    text("Returns cost one memory\nof equal value.", (1.6, -1.4, 2.55), 0.085, "#FFFFFF", root)
    tray = box("machine.tray", (2.6, 0.2, 0.9), (-0.65, -1.35, 0.95), "#0A0F1E", root, bevel=0.05)
    return {"root": root, "glow": glow, "sign": sign, "ret": ret, "tray_z": 0.9,
            "can_spawn": (loc[0] - 0.65, loc[1] - 1.0, 2.2), "can_land": (loc[0] - 0.65, loc[1] - 1.55, 0.9)}


# ------------------------------------------------------------------ sets

def hallway(time="day", labels=None):
    room_shell(70, 40, 15, "#E8E2D4", "#F3E7C9", "#4E7FB8", back_y=6.0)
    floor = bpy.data.objects["floor"]
    checker_floor(floor, "#D2CCC0", "#AEB6C4", 0.35)
    lockers = ["#4E7FB8", "#5B8CC6"]
    for i, x in enumerate([v * 1.7 for v in range(-18, 19)]):
        if abs(x) < 3.4:
            continue
        col = lockers[i % 2]
        box("locker", (1.6, 1.4, 7.4), (x, 5.1, 3.7), col, None, bevel=0.05)
        for k in range(3):
            box("vent", (0.9, 0.05, 0.08), (x, 4.37, 6.6 - k * 0.22), "#2C4870", None, bevel=0.01)
        box("handle", (0.12, 0.08, 0.5), (x + 0.5, 4.36, 4.0), "#C9CED8", None, bevel=0.02)
    # bulletin board + posters
    box("board", (6.0, 0.15, 3.2), (-11.0, 5.75, 10.2), "#B9874B", None, bevel=0.06)
    for i, (dx, dz, c) in enumerate([(-1.8, 0.5, "#F2C230"), (0.2, 0.7, "#E2526B"), (1.9, 0.2, "#7CC444"),
                                     (-0.8, -0.8, "#FFFFFF"), (1.2, -0.9, "#3FA7D6")]):
        box("paper", (1.3, 0.05, 1.0), (-11.0 + dx, 5.66, 10.2 + dz), c, None, bevel=0.01, rot=(0, (i % 3 - 1) * 6, 0))
    box("poster", (3.0, 0.08, 2.2), (11.5, 5.7, 10.4), "#7B4FD6", None, bevel=0.03)
    text("READ!", (11.5, 5.64, 10.4), 0.9, "#FFFFFF")
    for x in (-20, -7, 7, 20):
        ebox("ceiling.light", (5.0, 1.4, 0.15), (x, -2, 14.8), "#FFF8E8", 4.0 if time == "day" else 0.15)

    m = vending_machine((0, 4.6, 0), labels)
    if time == "day":
        set_world("#DCE8F2", 0.9)
        area_light((0, -4, 14.5), 30, 3200, "#FFF4E0")
        area_light((-12, -12, 9), 10, 1500, "#FFFFFF", rot=(60, 0, -30))
    else:
        set_world("#0A1028", 0.25)
        point_light((-0.6, 1.8, 4.5), 1200, "#7FD8FF", radius=1.5)  # machine glow
        area_light((0, -6, 14.5), 12, 120, "#5B6FB0")
        m["glow"].data.materials[0].node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 2.0
    return m


def classroom(time="day"):
    room_shell(44, 36, 14, "#C8935A", "#F6EBD0", "#7A5A3A", back_y=18.0)
    box("chalkboard", (14, 0.2, 4.8), (0, 17.8, 7.0), "#2F4F3A", None, bevel=0.05)
    box("chalk.tray", (14, 0.6, 0.2), (0, 17.6, 4.5), "#B9874B", None, bevel=0.03)
    text("First Day of School!", (0, 17.68, 7.6), 0.8, "#F4F1E8")
    text("2 + 2 = 4", (-3.5, 17.68, 6.0), 0.6, "#F4F1E8")
    for s in (-1, 1):  # windows on the side walls
        for y in (-4, 4):
            ebox("window", (0.2, 5.0, 4.5), (s * 21.7, y, 7.5), "#BFE3FF", 1.2)
    box("teacher.desk", (6.0, 3.0, 3.2), (9.0, 13.0, 1.6), "#8A5A30", None, bevel=0.08)
    box("apple", (0.6, 0.6, 0.6), (8.0, 13.0, 3.5), "#D63A3A", None, bevel=0.2)
    for x in (-6.0, -2.4, 2.4, 6.0):
        for y in (2.5, -3.5):
            desk(x, y)
    if time == "day":
        set_world("#DCE8F2", 0.9)
        area_light((0, 0, 13.5), 26, 4500, "#FFF4E0")
        area_light((-18, -10, 8), 10, 1200, "#FFFFFF", rot=(60, 0, -60))


def desk(x, y):
    """Student desk at (x, y): the student sits at (x, y-1.6) facing +Y."""
    box("desk.top", (3.0, 2.0, 0.2), (x, y, 3.2), "#E0B070", None, bevel=0.05)
    box("desk.body", (2.8, 1.8, 0.35), (x, y + 0.1, 2.92), "#6C7A89", None, bevel=0.05)
    for dx in (-1.3, 1.3):
        box("desk.leg", (0.18, 0.18, 2.3), (x + dx, y + 0.8, 1.15), "#6C7A89", None, bevel=0.03)
    cy = y - 2.4
    box("chair.seat", (1.9, 1.7, 0.2), (x, cy, 1.5), "#E2526B", None, bevel=0.05)
    box("chair.back", (1.9, 0.2, 1.9), (x, cy - 0.85, 2.5), "#E2526B", None, bevel=0.05)
    for dx in (-0.8, 0.8):
        box("chair.leg", (0.16, 0.16, 1.5), (x + dx, cy, 0.75), "#3A3A48", None, bevel=0.03)


def bedroom(time="night"):
    room_shell(36, 30, 13, "#8A6A4A", "#7C8FC4", "#F2EEE6", back_y=8.0)
    box("rug", (10, 7, 0.06), (0, 1.5, 0.03), "#E2526B", None, bevel=0.02)
    box("bed.frame", (7.0, 11.0, 1.6), (-9.5, 2.0, 0.8), "#8A5A30", None, bevel=0.1)
    box("bed.mattress", (6.6, 10.6, 0.8), (-9.5, 2.0, 2.0), "#F2EEE6", None, bevel=0.15)
    box("bed.blanket", (6.8, 7.0, 0.5), (-9.5, 0.2, 2.45), "#F07A2A", None, bevel=0.15)
    box("bed.pillow", (4.0, 1.8, 0.7), (-9.5, 6.3, 2.7), "#FFFFFF", None, bevel=0.2)
    box("bed.head", (7.0, 0.4, 3.6), (-9.5, 7.6, 1.8), "#8A5A30", None, bevel=0.08)
    ebox("window", (6.0, 0.2, 5.0), (5.0, 7.85, 8.0), "#1B2A5A", 0.6)
    ebox("moon", (1.2, 0.1, 1.2), (6.6, 7.7, 9.3), "#FFF3C4", 6.0, bevel=0.3)
    box("window.frame.v", (0.25, 0.3, 5.2), (5.0, 7.75, 8.0), "#F2EEE6", None, bevel=0.03)
    box("window.frame.h", (6.2, 0.3, 0.25), (5.0, 7.75, 8.0), "#F2EEE6", None, bevel=0.03)
    box("poster", (3.0, 0.08, 4.0), (-3.0, 7.75, 8.5), "#F2C230", None, bevel=0.03)
    text("SPACE", (-3.0, 7.7, 9.6), 0.6, "#253B6E")
    box("nightstand", (2.4, 2.4, 2.4), (-4.8, 6.5, 1.2), "#8A5A30", None, bevel=0.08)
    box("lamp.base", (0.6, 0.6, 1.2), (-4.8, 6.5, 3.0), "#F2EEE6", None, bevel=0.1)
    ebox("lamp.shade", (1.4, 1.4, 1.0), (-4.8, 6.5, 4.0), "#FFD58A", 2.5, bevel=0.15)
    set_world("#0A1028", 0.3)
    point_light((-4.8, 5.5, 4.2), 900, "#FFC870", radius=0.8)
    area_light((5.0, 4.0, 9.0), 6, 400, "#8FA8FF", rot=(-70, 0, 0))
    area_light((4.0, -8.0, 7.0), 10, 1100, "#FFD9A8", rot=(60, 0, 30))  # soft warm fill so faces read
