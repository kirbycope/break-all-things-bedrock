"""Checks both tools the way a player uses them: real mouse input in the Minecraft client, the world read back through
the minecraft-bedrock bridge. Needs the local BDS running this add-on's world with the bridge pack, and the client
joined to it (see README). Reuses cobblemon-bedrock's client driver and bridge client.

    python tools/client_check.py ore       a mixed stone and deepslate iron vein, with coal and a stray iron ore beside it
    python tools/client_check.py tree      a grown oak beside a log wall with no leaves; its crown goes too
    python tools/client_check.py twotrees  two oaks whose crowns touch: the felled one's leaves go, the other's all stay
    python tools/client_check.py cabin     a leafless log wall chopped with the axe: only the one log goes
    python tools/client_check.py sneak     the vein, mined while sneaking: only the one block goes
"""
import os
import sys
import time

DRIVER = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "cobblemon-bedrock", "tools")
sys.path.insert(0, DRIVER)
import client_drive  # noqa: E402
import pydirectinput  # noqa: E402
from bridge import Bridge  # noqa: E402

b = Bridge()
CAPTURES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "captures")
VEIN = [(0, 201, -2, "iron_ore"), (0, 202, -3, "deepslate_iron_ore"), (1, 203, -3, "iron_ore"), (2, 204, -4, "iron_ore"), (1, 202, -3, "deepslate_iron_ore")]
KEEP = [(0, 200, -2, "coal_ore"), (4, 201, -2, "iron_ore")]
# Facing north (yaw 180) from the middle of the platform, a little down: the crosshair sits on the first block of each test
AIM = "tp @a 0.5 200 0.5 180 4"


def run(*commands):
    for c in commands:
        b.command(c)


def is_block(x, y, z, block):
    return "success_count: 1" in b.command(f"testforblock {x} {y} {z} {block}")


def count_leaves(x1, y1, z1, x2, y2, z2):
    out = b.tool("mc_block_get_volume", dimension="overworld", **{"from": {"x": x1, "y": y1, "z": z1}, "to": {"x": x2, "y": y2, "z": z2}}, filter={"include": ["minecraft:oak_leaves"]})
    return out.count('type_id: "minecraft:oak_leaves"')


def platform():
    run("fill -8 199 -8 8 199 8 stone", "fill -8 200 -8 8 215 8 air", "kill @e[type=item]", "clear @a", "gamemode survival @a")


def mine(slot, seconds, sneak=False):
    client_drive.focus()
    pydirectinput.press(str(slot))
    if sneak: pydirectinput.keyDown("shift")
    time.sleep(0.3)
    pydirectinput.mouseDown()
    time.sleep(seconds)
    pydirectinput.mouseUp()
    if sneak: pydirectinput.keyUp("shift")
    time.sleep(1.0)


def ore(sneak=False):
    platform()
    run(*(f"setblock {x} {y} {z} {block}" for x, y, z, block in VEIN + KEEP))
    run(AIM, "replaceitem entity @a slot.hotbar 0 breakall:vein_pickaxe")
    time.sleep(1.0)
    client_drive.shot("ore_before")
    mine(1, 1.2, sneak)
    client_drive.shot("ore_after")
    gone = [v for v in VEIN if is_block(v[0], v[1], v[2], "air")]
    if sneak: print("sneaking, so only the block under the crosshair should go")
    kept = [k for k in KEEP if is_block(*k)]
    print(f"vein blocks mined: {len(gone)} of {len(VEIN)}; neighbours untouched: {len(kept)} of {len(KEEP)}")
    print("raw iron on the ground:", b.near("type=item,r=4"))
    print(b.tool("mc_player_get_inventory", player="Kirbycope"))


def tree():
    platform()
    # an oak: a five log trunk, a branch log off it through an edge, and grown leaves round the top
    run("fill 0 200 -2 0 204 -2 oak_log", "setblock 1 205 -2 oak_log", "fill -2 204 -4 2 206 0 oak_leaves [\"persistent_bit\"=false] keep",
        # a log wall with no leaves: a cabin, which must stay
        "fill -5 200 -2 -5 203 -2 oak_log")
    run("tp @a 0.5 200 0.5 180 20", "replaceitem entity @a slot.hotbar 1 breakall:timber_axe")
    time.sleep(1.0)
    client_drive.shot("tree_before")
    mine(2, 1.5)
    client_drive.shot("tree_after")
    logs = [(0, y, -2) for y in range(201, 205)] + [(1, 205, -2)]
    print("tree logs felled:", sum(is_block(*p, "air") for p in logs), "of", len(logs))
    print("crown leaves left:", count_leaves(-2, 204, -4, 2, 206, 0), "(want 0)")
    print("cabin logs standing:", sum(is_block(-5, y, -2, "oak_log") for y in range(200, 204)), "of 4")
    print(b.tool("mc_player_get_inventory", player="Kirbycope"))


def cabin():
    platform()
    run("fill 0 200 -2 0 203 -2 oak_log")
    run("tp @a 0.5 200 0.5 180 20", "replaceitem entity @a slot.hotbar 1 breakall:timber_axe")
    time.sleep(1.0)
    mine(2, 0.6)   # one log's worth: a held button keeps mining by hand once the first log is gone
    client_drive.shot("cabin_after")
    print("wall logs chopped:", sum(is_block(0, y, -2, "air") for y in range(200, 204)), "of 4 (want 1)")


def twotrees():
    """Two oaks five apart, crowns of radius two that meet between them; the left one is felled."""
    platform()
    run("fill -8 200 -8 8 215 8 air", "fill -8 199 -8 8 199 8 stone")
    for x in (0, 5):
        run(f"fill {x - 2} 204 -4 {x + 2} 206 0 oak_leaves [\"persistent_bit\"=false]", f"fill {x} 200 -2 {x} 205 -2 oak_log")
    right_before = count_leaves(3, 204, -4, 7, 206, 0)
    run("tp @a 0.5 200 0.5 180 20", "replaceitem entity @a slot.hotbar 1 breakall:timber_axe")
    time.sleep(1.0)
    client_drive.shot("twotrees_before")
    mine(2, 0.6)
    client_drive.shot("twotrees_after")
    print("left trunk felled:", sum(is_block(0, y, -2, "air") for y in range(200, 206)), "of 6")
    print("left crown leaves left:", count_leaves(-2, 204, -4, 2, 206, 0), "(want 0)")
    print("right crown leaves:", count_leaves(3, 204, -4, 7, 206, 0), "of", right_before, "(want all)")


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "ore"
    {"ore": ore, "sneak": lambda: ore(sneak=True), "tree": tree, "cabin": cabin, "twotrees": twotrees}[what]()
