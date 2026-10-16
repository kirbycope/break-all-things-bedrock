"""Draws the two item textures and the pack icon, so the art is code rather than a hand-edited PNG.

    python tools/make_textures.py

Both tools are laid out along one diagonal handle running from the bottom left corner to the top right, the way
Minecraft draws its own tools, so they sit in the hand at the same angle as a vanilla pickaxe or axe. Each shape is
a mask in the handle's own frame (u along it, v across it), which keeps the head and the blade at right angles to
the handle at 16 pixels. The pack icon is both of them side by side on a slab of deepslate with ore in it.
"""

import math
import os

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ITEMS = os.path.join(ROOT, "development_resource_packs", "break_all_things", "textures", "items")
ICONS = [os.path.join(ROOT, "development_behavior_packs", "break_all_things", "pack_icon.png"),
         os.path.join(ROOT, "development_resource_packs", "break_all_things", "pack_icon.png")]

OUTLINE = (24, 22, 30, 255)
STICK_LIGHT, STICK_DARK = (137, 103, 39, 255), (73, 54, 21, 255)
DIAMOND = [(14, 63, 54, 255), (32, 197, 181, 255), (74, 237, 217, 255), (209, 250, 245, 255)]   # dark to light
REDSTONE = (255, 30, 20, 255)
LEAF = (88, 178, 38, 255)
DIAG = 1 / math.sqrt(2)


def frame(x: int, y: int) -> tuple[float, float]:
    """A pixel's centre as (u, v): u along the handle from its bottom left end, v across it towards the top left."""
    dx, dy = x + 0.5 - 1.5, y + 0.5 - 14.5
    return (dx - dy) * DIAG, (-dx - dy) * DIAG


def handle(u: float, v: float, top: float) -> tuple | None:
    if 0 <= u <= top and -0.8 <= v <= 0.8:
        return STICK_LIGHT if v >= 0 else STICK_DARK
    return None


def pickaxe(u: float, v: float) -> tuple | None:
    """A crescent head across the top of the handle, its points bent back down towards the hand, a redstone seam along it."""
    r = math.hypot(u + 2.0, v)   # rings around a point behind the hand, so the head bows away from it
    angle = math.degrees(math.atan2(v, u + 2.0))
    if abs(angle) <= 34:
        thickness = 2.4 - 1.2 * (abs(angle) / 34) ** 2
        inner = 11.6
        if inner <= r <= inner + thickness:
            depth = (r - inner) / thickness
            if 0.3 <= depth <= 0.65 and 6 < abs(angle) < 26:
                return REDSTONE
            return DIAMOND[3] if depth > 0.8 else DIAMOND[2] if depth > 0.45 else DIAMOND[1]
    return handle(u, v, 11.8)


def axe(u: float, v: float) -> tuple | None:
    """A broad blade on the top left of the handle whose cutting edge fans out, a leaf green band where it meets the haft."""
    if 0.6 <= v <= 5.2:
        low, high = 9.6 - 0.5 * v, 12.2 + 0.15 * v
        if low <= u <= high:
            if v >= 4.4:
                return DIAMOND[3]
            if v <= 1.5:
                return LEAF
            return DIAMOND[2] if u > (low + high) / 2 else DIAMOND[1]
    if -2.0 <= v < -0.6 and 10.4 <= u <= 12.0:   # the poll, a short stub behind the handle
        return DIAMOND[0]
    return handle(u, v, 12.2)


def draw(shape) -> Image.Image:
    image = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    pixels = image.load()
    for y in range(16):
        for x in range(16):
            colour = shape(*frame(x, y))
            if colour:
                pixels[x, y] = colour
    # A one pixel outline wherever an empty pixel shares an edge with the drawing, the way vanilla items are bordered
    filled = {(x, y) for y in range(16) for x in range(16) if pixels[x, y][3]}
    for y in range(16):
        for x in range(16):
            if (x, y) not in filled and any((x + dx, y + dy) in filled for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                pixels[x, y] = OUTLINE
    return image


def icon(pick: Image.Image, axe_image: Image.Image) -> Image.Image:
    """128 pixels: deepslate with ore flecks, the pickaxe and the axe side by side on it."""
    background = Image.new("RGBA", (32, 32), (60, 60, 68, 255))
    pixels = background.load()
    for y in range(32):
        for x in range(32):
            shade = 52 + ((x * 7 + y * 13) % 11)
            pixels[x, y] = (shade, shade, shade + 6, 255)
    for x, y, colour in [(4, 3, DIAMOND[2]), (5, 3, DIAMOND[2]), (5, 4, DIAMOND[1]), (25, 28, REDSTONE), (26, 29, REDSTONE),
                         (27, 28, REDSTONE), (14, 2, (216, 175, 147, 255)), (15, 2, (216, 175, 147, 255)), (27, 3, (240, 205, 70, 255))]:
        pixels[x, y] = colour
    background.alpha_composite(pick, (0, 8))
    background.alpha_composite(axe_image, (16, 8))
    return background.resize((128, 128), Image.Resampling.NEAREST)


def main() -> None:
    os.makedirs(ITEMS, exist_ok=True)
    pick, axe_image = draw(pickaxe), draw(axe)
    pick.save(os.path.join(ITEMS, "vein_pickaxe.png"), optimize=True)
    axe_image.save(os.path.join(ITEMS, "timber_axe.png"), optimize=True)
    pack = icon(pick, axe_image)
    for path in ICONS:
        pack.save(path, optimize=True)
    print("wrote", ", ".join(os.path.relpath(p, ROOT) for p in [os.path.join(ITEMS, "vein_pickaxe.png"), os.path.join(ITEMS, "timber_axe.png"), *ICONS]))


if __name__ == "__main__":
    main()
