"""Sets for the private study copy of craftee_films' "Teleportation Curse" (never published).

Denser dressing than our story sets: food on tables, posters, laptops, sleeping bags, trees with petals,
and a warm golden-hour look. Same conventions as sets.py (floor z=0, camera usually looks toward +Y).
"""
import math
import random

import bpy

from blocky import box, hex_rgba
from kit import place, place_tinted
from sets import area_light, ebox, point_light, room_shell, set_world, text
import sets_fixed

FOOD = "food-kit"


def golden(sun_rot=(68, 0, -35), energy=4.5):
    """Low warm sun + orange sky, the 'golden hour' look of the reference."""
    li = bpy.data.lights.new("sun", "SUN")
    li.energy = energy
    li.color = (1.0, 0.72, 0.42)
    li.angle = math.radians(6)
    ob = bpy.data.objects.new("sun", li)
    bpy.context.scene.collection.objects.link(ob)
    ob.rotation_euler = [math.radians(a) for a in sun_rot]
    set_world("#F2B07A", 0.9)
    bpy.context.scene.eevee.bloom_intensity = 0.08


def cherry_tree(x, y, s=1.0, seed=0):
    rnd = random.Random(seed)
    box("trunk", (1.2 * s, 1.2 * s, 7 * s), (x, y, 3.5 * s), "#6B4430", None, bevel=0.1)
    for bx, rz in ((-1.4, 25), (1.5, -30)):
        box("branch", (0.6 * s, 0.6 * s, 3.2 * s), (x + bx * s, y, 7.2 * s), "#6B4430", None, bevel=0.08, rot=(0, rz, 0))
    pinks = ["#F7A8C4", "#F49AB9", "#FBC3D6", "#EE8FB0"]
    for _ in range(26):
        size = rnd.uniform(2.0, 3.4) * s
        box("bloom", (size, size, size * 0.8), (x + rnd.uniform(-4, 4) * s, y + rnd.uniform(-3, 3) * s,
            rnd.uniform(7.5, 11.5) * s), rnd.choice(pinks), None, bevel=0.3)


def petals(n_frames, count=60, area=(-14, 14, -10, 14), top=16, seed=3):
    """Falling petals across the frame (small pink squares drifting down)."""
    rnd = random.Random(seed)
    for i in range(count):
        p = box("petal", (0.22, 0.04, 0.18), (0, 0, 0), "#F8B6CD", None, bevel=0.02)
        x0, y0 = rnd.uniform(area[0], area[1]), rnd.uniform(area[2], area[3])
        z0 = rnd.uniform(2, top)
        speed = rnd.uniform(1.2, 2.2) / 24          # units per frame
        drift = rnd.uniform(-0.6, 0.6) / 24
        for f in (1, n_frames):
            dz = (f - 1) * speed
            p.location = (x0 + (f - 1) * drift, y0, (z0 - dz) % top + 0.2)
            p.rotation_euler = (rnd.uniform(0, 6), rnd.uniform(0, 6), f * 0.05)
            p.keyframe_insert("location", frame=f)
            p.keyframe_insert("rotation_euler", frame=f)


def park(time="day", spec=None):
    box("grass", (200, 160, 0.2), (0, 40, -0.1), "#7DA75A", None, bevel=0, rough=0.9)
    box("path", (8, 160, 0.06), (-12, 40, 0.02), "#D9C3A0", None, bevel=0)
    for i, (x, y) in enumerate(((-9, 12), (9, 14), (-20, 24), (20, 28), (0, 34), (-30, 40), (30, 44))):
        cherry_tree(x, y, 1.0 + 0.15 * (i % 3), seed=i)
    for x in (-40, -26, 26, 40):
        place("nature-kit", "tree_default", (x, 52, 0), scale=1.4)
    # the bench
    box("bench.seat", (7, 2.0, 0.3), (0, 1.0, 2.2), "#8A5A30", None, bevel=0.05)
    box("bench.back", (7, 0.3, 2.0), (0, 2.0, 3.4), "#8A5A30", None, bevel=0.05)
    for sx in (-3.2, 3.2):
        box("bench.leg", (0.3, 2.0, 2.2), (sx, 1.0, 1.1), "#3A3A3A", None, bevel=0.03)
    golden()
    area_light((0, -20, 12), 30, 1200, "#FFE2C4", rot=(70, 0, 0))


def class_tc(time="day", spec=None):
    """Busy grey-white classroom: 3 rows x 4 desks, solar-system poster, door, ceiling lights."""
    room_shell(48, 44, 14, "#BFC4CB", "#EDEEEF", "#9AA3AD", back_y=20.0)
    sets_fixed.checker_floor(bpy.data.objects["floor"], "#D8DBDF", "#C6CAD0", 0.4)
    box("board", (16, 0.2, 5.0), (0, 19.75, 7.4), "#2F3A36", None, bevel=0.04)
    box("poster", (5.0, 0.12, 7.0), (14, 19.7, 7.8), "#0F1530", None, bevel=0.04)
    for i, (dx, dz, c, r) in enumerate(((-1.4, 2.0, "#F2C230", 0.7), (0.4, 0.8, "#E2526B", 0.35), (1.3, -0.6, "#3FA7D6", 0.45),
                                        (-0.8, -1.8, "#7CC444", 0.3), (1.0, -2.6, "#C89BF2", 0.5))):
        box("planet", (r * 2, 0.1, r * 2), (14 + dx, 19.6, 7.8 + dz), c, None, bevel=r * 0.9)
    box("door", (4.5, 0.3, 9.0), (-18, 19.8, 4.5), "#8A5A30", None, bevel=0.05)
    for x in (-15, -5, 5, 15):
        ebox("light", (6, 1.6, 0.2), (x, 4, 13.8), "#FFFFFF", 5.0)
    for x in (-10.5, -3.5, 3.5, 10.5):
        for y in (8.0, 1.5, -5.0):
            box("desk.top", (4.0, 2.6, 0.25), (x, y, 3.3), "#C88A4A", None, bevel=0.04)
            box("desk.frame", (3.6, 2.2, 0.2), (x, y, 2.9), "#6C7A89", None, bevel=0.03)
            for dx in (-1.6, 1.6):
                box("desk.leg", (0.18, 0.18, 2.9), (x + dx, y + 0.9, 1.45), "#6C7A89", None, bevel=0.03)
            box("chair.seat", (2.0, 1.8, 0.2), (x, y - 2.6, 1.6), "#C88A4A", None, bevel=0.04)
            box("chair.back", (2.0, 0.2, 2.0), (x, y - 3.5, 2.6), "#C88A4A", None, bevel=0.04)
            box("paper", (1.4, 1.0, 0.03), (x + 0.6, y - 0.2, 3.44), "#FAFAFA", None, bevel=0)
    set_world("#E9ECEF", 0.9)
    area_light((0, 0, 13.5), 36, 4200, "#FFF7EC")
    area_light((-18, -16, 9), 12, 1500, "#FFFFFF", rot=(60, 0, -40))


def dining(time="night", spec=None):
    """Her family's dinner table, piled with food, warm pendant light."""
    room_shell(40, 32, 12, "#8C6E52", "#E7D2B4", "#6E4F38", back_y=14.0)
    x = -14.0
    for name in ("kitchenFridgeLarge", "kitchenCabinet", "kitchenSink", "kitchenStove", "kitchenCabinetDrawer", "kitchenCabinet"):
        place("furniture-kit", name, (x, 13.6, 0), rot=180)
        x += 4.2
    box("table", (12, 7, 0.5), (0, 2, 3.4), "#A0632E", None, bevel=0.08)
    for sx in (-5.4, 5.4):
        for sy in (-1, 5):
            box("table.leg", (0.5, 0.5, 3.2), (sx, sy, 1.6), "#7A4A22", None, bevel=0.05)
    rnd = random.Random(7)
    spots = [(-4.5, 0.2), (-1.5, 0.2), (1.5, 0.2), (4.5, 0.2), (-4.5, 3.8), (-1.5, 3.8), (1.5, 3.8), (4.5, 3.8)]
    for sx, sy in spots:
        place(FOOD, "plate-dinner", (sx, sy, 3.66), scale=2.4)
        place(FOOD, rnd.choice(["burger", "burger-cheese", "pizza", "pancakes"]), (sx, sy, 3.9), scale=2.4)
        place(FOOD, "soda-glass", (sx + 1.1, sy + 0.9, 3.66), scale=2.6)
    place(FOOD, "cake-birthday", (0, 2, 3.66), scale=2.8)
    place(FOOD, "fries", (-2.8, 2, 3.66), scale=2.6)
    place(FOOD, "donut-sprinkles", (2.8, 2, 3.66), scale=2.6)
    for sx, r in ((-4.5, 0), (-1.5, 0), (1.5, 0), (4.5, 0)):
        box("chair", (2.2, 2.0, 0.25), (sx, -2.6, 2.0), "#7A4A22", None, bevel=0.05)
        box("chair", (2.2, 2.0, 0.25), (sx, 6.6, 2.0), "#7A4A22", None, bevel=0.05)
    ebox("pendant", (2.4, 2.4, 1.2), (0, 2, 9.5), "#FFC98A", 8.0, bevel=0.3)
    point_light((0, 2, 8.6), 2600, "#FFB46B", radius=1.0)
    set_world("#2A1C14", 0.5)
    area_light((0, -14, 8), 18, 900, "#FFD2A0", rot=(70, 0, 0))


def street_car(time="night", spec=None):
    """The night street with a red sedan driving."""
    sets_fixed.street("night", spec)
    place_tinted("car-kit", "sedan", "#E04A3A", (-2, -12.5, 0), rot=90)


def car_interior(time="night", spec=None):
    """Tight front-seat interior: two seats, dashboard, windscreen onto night street lights."""
    set_world("#0B1022", 0.4)
    box("floor", (12, 12, 0.2), (0, 0, -0.1), "#1E1E24", None, bevel=0)
    for sx in (-2.4, 2.4):
        box("seat", (3.2, 2.6, 1.0), (sx, 0, 2.0), "#2E2E36", None, bevel=0.2)
        box("seat.back", (3.2, 0.8, 4.2), (sx, 1.6, 4.0), "#2E2E36", None, bevel=0.2)
    box("dash", (10, 2.4, 1.6), (0, -4.2, 4.6), "#E04A3A", None, bevel=0.2)
    box("wheel", (2.0, 0.3, 2.0), (-2.4, -3.0, 5.4), "#151518", None, bevel=0.6)
    box("roof", (10, 8, 0.4), (0, -0.5, 8.6), "#E04A3A", None, bevel=0.1)
    for sx in (-5, 5):
        box("door", (0.4, 8, 3.2), (sx, -0.5, 2.6), "#E04A3A", None, bevel=0.1)
    for i in range(6):
        ebox("streetlight", (0.6, 0.6, 0.6), (-12 + i * 5, -14, 7 + (i % 2)), "#FFC98A", 8.0, bevel=0.2)
    point_light((0, -1, 7.6), 300, "#7F95E8", radius=1.0)
    area_light((0, -10, 6), 8, 500, "#FFC98A", rot=(80, 0, 0))
    area_light((0, -9, 6.5), 10, 900, "#9DB0F0", rot=(78, 0, 0))   # dashboard glow on their faces


def hallway_tc(time="day", spec=None):
    """Warm locker corridor with a glossy floor."""
    room_shell(18, 90, 14, "#C9A27A", "#E8D4B4", "#A07850", back_y=60.0)
    for s in (-1, 1):
        for i in range(-16, 30):
            y = i * 2.0
            box("locker", (1.4, 1.9, 7.4), (s * 8.2, y, 3.7), "#2F3B4A", None, bevel=0.05)
            for k in range(3):
                box("vent", (0.05, 1.0, 0.08), (s * 7.48, y, 6.6 - k * 0.22), "#1C2430", None, bevel=0.01)
    for y in range(-20, 60, 10):
        ebox("light", (4, 2, 0.2), (0, y, 13.8), "#FFE7C2", 5.0)
    set_world("#E8C79C", 0.8)
    area_light((0, 10, 13.5), 40, 5200, "#FFE1B8")
    area_light((0, -20, 7), 12, 1200, "#FFD8A8", rot=(80, 0, 0))


def sleepover(time="night", spec=None):
    """Brick-walled bedroom, 'stay positive' poster, laptops on a desk, ten sleeping bags in a ring."""
    room_shell(36, 36, 13, "#B9B4AE", "#C96F57", "#8F4B3B", back_y=16.0)
    bpy.data.objects.remove(bpy.data.objects["ceiling"], do_unlink=True)   # open top for overhead shots
    # brick pattern on the back wall
    for row in range(26):
        z = 0.5 + row * 0.5
        off = 0 if row % 2 else 0.75
        for col in range(24):
            x = -17.25 + off + col * 1.5
            if x > 17.4:
                continue
            box("brick", (1.36, 0.06, 0.42), (x, 15.78, z), "#B85A44" if (row + col) % 3 else "#A94F3B", None, bevel=0.03)
    box("poster", (4.2, 0.1, 5.4), (-6, 15.7, 8.2), "#9CC8E8", None, bevel=0.03)
    text("stay positive", (-6, 15.62, 10.3), 0.42, "#2B2B2B")
    box("poster2", (3.4, 0.1, 4.0), (6, 15.7, 8.6), "#E9D3E8", None, bevel=0.03)
    box("desk", (8, 3, 0.3), (10, 13.6, 3.8), "#F2EEE6", None, bevel=0.05)
    for lx in (8.2, 11.6):
        place("furniture-kit", "laptop", (lx, 13.6, 3.95), rot=180, scale=1.0)
    colors = ["#F7B6D2", "#C89BF2", "#9AD8FF", "#FFD27D", "#7CFFB2", "#FF8A80", "#B8E986", "#F2A9C0", "#9FA8DA", "#FFAB91"]
    for i in range(10):
        a = math.radians(i * 36)
        cx, cy = 7.5 * math.cos(a), 1.5 + 7.5 * math.sin(a)
        box("bag", (2.6, 5.2, 0.6), (cx, cy, 0.3), colors[i], None, bevel=0.2, rot=(0, 0, math.degrees(a) + 90))
        box("pillow", (2.0, 1.0, 0.5), (cx + 2.4 * math.cos(a), cy + 2.4 * math.sin(a), 0.6), "#FFFFFF", None, bevel=0.2,
            rot=(0, 0, math.degrees(a) + 90))
    set_world("#2A1C2E", 0.5)
    point_light((-8, 6, 10), 1800, "#FFC9E8", radius=1.5)
    area_light((0, -14, 10), 20, 1600, "#FFE0C2", rot=(60, 0, 0))
    area_light((0, 1.5, 12.5), 10, 900, "#FFF2E0")


def bathroom(time="night", spec=None):
    sets_fixed.bathroom(time, spec)


SETS = {"park": park, "class_tc": class_tc, "dining": dining, "street_car": street_car, "car_interior": car_interior,
        "hallway_tc": hallway_tc, "sleepover": sleepover, "bathroom_tc": bathroom}
