"""Sets for the story "Fixed": a watched suburban street, a classroom, the Clinic, a bathroom
and a night kitchen. Built from Kenney CC0 kits (blender/kit.py) plus a few blocky details.

Same conventions as sets.py: floor is z=0, characters face -Y, the camera usually looks toward +Y.
"""
from blocky import box
from kit import place, place_tinted
from sets import area_light, checker_floor, ebox, point_light, room_shell, set_world, text

CAM_RED = "#FF2B3A"


def street_camera(x, y, h=13.2):
    """A streetlight camera: dark housing with a red lens, facing the sidewalk (-Y side)."""
    box("cam.body", (0.9, 1.3, 0.8), (x, y - 0.4, h), "#2A2D34", None, bevel=0.08)
    ebox("cam.lens", (0.42, 0.12, 0.42), (x, y - 1.08, h), CAM_RED, 6.0, bevel=0.05)


def street(time="day", spec=None):
    """Sidewalk along X at y≈0, houses behind (+Y), road in front (-Y), streetlights with cameras."""
    night = time == "night"
    box("grass", (260, 120, 0.2), (0, 40, -0.12), "#6FA457", None, bevel=0, rough=0.9)
    box("sidewalk", (260, 8, 0.25), (0, 0, 0.0), "#C9C4BA", None, bevel=0, rough=0.8)
    box("curb", (260, 0.6, 0.45), (0, -4.2, 0.1), "#B4AEA3", None, bevel=0.02)
    for x in range(-128, 129, 16):
        place("city-kit-roads", "road-straight", (x, -12.5, 0.02), rot=90)
    houses = ["building-type-a", "building-type-c", "building-type-e", "building-type-h", "building-type-k", "building-type-n"]
    for i, x in enumerate(range(-90, 91, 30)):
        place("city-kit-suburban", houses[i % len(houses)], (x, 26, 0), rot=180, scale=1.35)
        place("city-kit-suburban", "fence-low", (x - 9, 9, 0), rot=0, scale=1.2)
        place("city-kit-suburban", "fence-low", (x + 9, 9, 0), rot=0, scale=1.2)
        place("city-kit-suburban", "tree-large" if i % 2 else "tree-small", (x + 15, 14, 0))
    for x in range(-80, 81, 26):
        place("city-kit-roads", "light-square", (x, -3.2, 0), rot=90, scale=1.5)
        street_camera(x, -3.0)
    # Mr. Daly's mailbox
    box("mailbox.post", (0.35, 0.35, 3.2), (6, 3.2, 1.6), "#5A4630", None, bevel=0.03)
    box("mailbox", (1.1, 1.7, 1.0), (6, 3.2, 3.6), "#3B5BA5", None, bevel=0.15)
    if night:
        set_world("#0E1838", 0.6)
        area_light((0, -30, 40), 70, 3200, "#7D93E0", rot=(40, 0, 0))  # moonlight
        area_light((6, -16, 8), 16, 500, "#9AAAE8", rot=(75, 0, 20))   # soft fill so faces read
        for x in range(-80, 81, 26):
            point_light((x, -3.0, 13.6), 2600, "#FFC98A", radius=1.2)
    else:
        set_world("#BFE0FF", 1.0)
        area_light((10, -40, 60), 80, 9000, "#FFF1D8", rot=(35, 0, 15))
        area_light((-30, 20, 30), 40, 1500, "#CFE3FF", rot=(-30, 0, 0))


def van(x=-6.0, y=-12.0, rot=90, lights=True):
    """The Clinic's white van on the road, headlights pointing along its travel direction."""
    place_tinted("car-kit", "van", "#F4F6F8", (x, y, 0), rot=rot)
    if lights:
        import math
        import bpy
        for dy in (-1.8, 1.8):
            li = bpy.data.lights.new("headlight", "SPOT")
            li.energy = 6000
            li.spot_size = math.radians(55)
            li.color = (1.0, 0.95, 0.85)
            ob = bpy.data.objects.new("headlight", li)
            bpy.context.scene.collection.objects.link(ob)
            ob.location = (x + 8.5, y + dy, 3.0)
            ob.rotation_euler = (math.radians(90), 0, math.radians(-90))


def classroom_b(time="day", spec=None):
    """A brighter, newer classroom than blockmated's: mint walls, rows of kit desks, a smile poster."""
    room_shell(48, 40, 14, "#9AA3AE", "#CFEDE2", "#5C8C7A", back_y=18.0)
    checker_floor(__import__("bpy").data.objects["floor"], "#B7BEC8", "#A3ABB6", 0.25)
    box("whiteboard", (16, 0.2, 5.0), (0, 17.75, 7.4), "#F8F8F4", None, bevel=0.04)
    text("Remember to SMILE :)", (0, 17.6, 8.2), 0.95, "#2C7A62")
    text("Strikes this week: 0", (0, 17.6, 6.6), 0.8, "#C2394A")
    box("poster", (5.0, 0.1, 6.5), (-17, 17.7, 7.6), "#FFD34E", None, bevel=0.03)
    text(":)", (-17, 17.6, 8.2), 2.6, "#2B2B2B")
    for x in (-7.5, -2.5, 2.5, 7.5):
        for y in (3.0, -3.5):
            place("furniture-kit", "desk", (x - 2.9, y + 1.6, 0), rot=0)
            place("furniture-kit", "chairDesk", (x - 1.6, y - 0.6, 0), rot=180)
    # Teo's desk (front row, second from right): his name carved underneath
    text("TEO", (2.5, 4.55, 2.3), 0.5, "#4A3A2A", rot=(180, 0, 0))
    # a dome camera in the corner
    box("dome.base", (1.4, 1.4, 0.3), (21, 15, 13.7), "#2A2D34", None, bevel=0.1)
    ebox("dome.lens", (0.5, 0.5, 0.5), (21, 15, 13.3), CAM_RED, 5.0, bevel=0.2)
    for s in (-1, 1):
        for y in (-6, 6):
            ebox("window", (0.2, 6.0, 5.0), (s * 23.7, y, 8.0), "#CFEFFF", 1.4)
    set_world("#E6F2EE", 0.9)
    area_light((0, -2, 13.6), 30, 3600, "#FFFFFF")
    area_light((-14, -14, 9), 10, 1200, "#FFFFFF", rot=(60, 0, -30))


def clinic(time="day", spec=None):
    """Too white, too bright. Three beds, a pink-cup tray, a potted plant and the motto."""
    room_shell(44, 36, 13, "#D9E4E4", "#EEF3F2", "#9FD3CF", back_y=16.0)
    text("TAKE THE FROWN", (0, 15.75, 10.4), 1.3, "#178F89")
    text("OUT OF THE TOWN", (0, 15.75, 8.8), 1.3, "#178F89")
    text(":)", (0, 15.75, 6.9), 1.6, "#178F89")
    for x in (-14, -6, 2):
        place("furniture-kit", "bedSingle", (x - 2.3, 14.8, 0), rot=180)
    place("furniture-kit", "pottedPlant", (12.5, 12.5, 0), scale=1.4)
    place("furniture-kit", "bathroomSink", (17.5, 15.6, 0), rot=180)
    box("cart", (4.0, 2.2, 3.4), (9, 5, 1.7), "#DDE3E6", None, bevel=0.1)
    for i in range(5):
        box("cup", (0.5, 0.5, 0.7), (7.6 + i * 0.7, 5, 3.75), "#FF8FB8", None, bevel=0.12)
    for x in (-12, 0, 12):
        ebox("panel", (8, 3, 0.15), (x, 2, 12.85), "#FFFFFF", 6.0)
    set_world("#EEF6F6", 0.6)
    area_light((0, 0, 12.5), 36, 2600, "#F4FBFF")
    area_light((0, -16, 7), 20, 900, "#FFFFFF", rot=(80, 0, 0))


def bathroom(time="day", spec=None):
    """A small tiled bathroom; the mirror is on the back wall at face height for 'mirror POV' shots."""
    room_shell(18, 16, 11, "#9FC3D8", "#E9F1F4", "#7FA9C2", back_y=6.0)
    checker_floor(__import__("bpy").data.objects["floor"], "#E7EDF0", "#A9C4D3", 0.5)
    place("furniture-kit", "bathroomSink", (-1.6, 5.4, 0), rot=180, scale=1.2)
    box("mirror.frame", (5.2, 0.25, 4.2), (0, 5.85, 7.4), "#D8DEE2", None, bevel=0.1)
    box("mirror.glass", (4.7, 0.1, 3.7), (0, 5.7, 7.4), "#9DB4C0", None, bevel=0.02, rough=0.08)
    place("furniture-kit", "toilet", (6.2, 4.6, 0), rot=180, scale=1.1)
    box("towel", (2.0, 0.2, 2.6), (-6.5, 5.7, 5.5), "#F2A9C0", None, bevel=0.1)
    set_world("#DDEBF2", 0.8)
    area_light((0, -2, 10.6), 10, 1400, "#FFF7EC")
    area_light((0, -12, 7), 8, 700, "#FFFFFF", rot=(80, 0, 0))


def kitchen(time="night", spec=None):
    """Night kitchen: counter along the back wall, fridge, a table, a window with moonlight."""
    night = time == "night"
    room_shell(40, 32, 12, "#8C6E52", "#E7D7BE", "#6E4F38", back_y=14.0)
    x = -12.0
    for name in ("kitchenFridgeLarge", "kitchenCabinet", "kitchenSink", "kitchenCabinet", "kitchenStove", "kitchenCabinetDrawer"):
        place("furniture-kit", name, (x, 13.6, 0), rot=180)
        x += 4.2
    place("furniture-kit", "table", (-3.0, 0.0, 0), rot=0, scale=1.1)
    for cx, r in ((-4.5, 0), (2.5, 180)):
        place("furniture-kit", "chair", (cx, -1.5 if r == 0 else 3.0, 0), rot=r)
    ebox("window", (6.0, 0.2, 5.0), (12, 13.85, 7.6), "#1B2A5A" if night else "#CFEFFF", 0.7 if night else 1.4)
    if night:
        ebox("moon", (1.0, 0.1, 1.0), (13.4, 13.7, 9.0), "#FFF3C4", 6.0)
        set_world("#0C1228", 0.45)
        area_light((12, 8, 9), 6, 1600, "#7D93E0", rot=(-70, 0, 0))  # moonlight through the window
        point_light((-3, 11.0, 8.5), 900, "#FFB66B", radius=0.6)      # stove-hood light
        area_light((6, -14, 8), 16, 900, "#6A7FD0", rot=(70, 0, 25))  # fill so faces read
        area_light((-3.6, 4.0, 7.5), 8, 650, "#8FA2E8", rot=(60, 0, 0))   # moonlight bounce on the sink
        area_light((-10, 5.0, 7.5), 6, 450, "#8FA2E8", rot=(60, 0, 0))    # ...and on the fridge
        point_light((-11.0, 12.0, 6.0), 420, "#CFE6FF", radius=1.0)       # cold fridge glow on faces
    else:
        set_world("#F3E9D8", 0.9)
        area_light((0, -2, 11.6), 26, 3000, "#FFF2DE")


SETS = {"street": street, "classroom_b": classroom_b, "clinic": clinic, "bathroom": bathroom, "kitchen": kitchen}
