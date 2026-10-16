"""Checks on the packs' files alone: no server needed. `python -m pytest tests`"""

import json
import os
import re
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BP = os.path.join(ROOT, "development_behavior_packs", "break_all_things")
RP = os.path.join(ROOT, "development_resource_packs", "break_all_things")
ITEMS = ["vein_pickaxe", "timber_axe"]

sys.path.insert(0, os.path.join(ROOT, "tools"))
import build_addon  # noqa: E402


def load(*parts: str) -> dict:
    with open(os.path.join(*parts), encoding="utf-8") as handle:
        return json.load(handle)


def test_the_behavior_pack_depends_on_the_resource_pack_and_a_stable_script_api():
    bp, rp = load(BP, "manifest.json"), load(RP, "manifest.json")
    deps = bp["dependencies"]
    assert {"uuid": rp["header"]["uuid"], "version": rp["header"]["version"]} in deps
    script = next(d for d in deps if d.get("module_name") == "@minecraft/server")
    assert re.fullmatch(r"\d+\.\d+\.\d+", script["version"]), "a beta script API would need the Beta APIs experiment"
    entry = next(m for m in bp["modules"] if m["type"] == "script")["entry"]
    assert os.path.isfile(os.path.join(BP, entry))


def test_every_uuid_is_unique():
    uuids = []
    for pack in (BP, RP):
        manifest = load(pack, "manifest.json")
        uuids += [manifest["header"]["uuid"], *(m["uuid"] for m in manifest["modules"])]
    assert len(uuids) == len(set(uuids))


def test_each_item_has_a_texture_a_name_and_a_recipe_that_makes_it():
    textures = load(RP, "textures", "item_texture.json")["texture_data"]
    with open(os.path.join(RP, "texts", "en_US.lang"), encoding="utf-8") as handle:
        names = dict(line.strip().split("=", 1) for line in handle if "=" in line)
    for item in ITEMS:
        components = load(BP, "items", f"{item}.json")["minecraft:item"]["components"]
        icon = components["minecraft:icon"]
        path = textures[icon]["textures"]
        image = Image.open(os.path.join(RP, path + ".png"))
        assert image.size == (16, 16) and image.mode == "RGBA"
        assert components["minecraft:display_name"]["value"] in names
        recipe = load(BP, "recipes", f"{item}.json")["minecraft:recipe_shaped"]
        assert recipe["result"]["item"] == f"breakall:{item}"
        used = set("".join(recipe["pattern"])) - {" "}
        assert used == set(recipe["key"]), f"{item}: pattern and key disagree"


def test_the_script_knows_both_items_by_their_identifiers():
    with open(os.path.join(BP, "scripts", "main.js"), encoding="utf-8") as handle:
        script = handle.read()
    for item in ITEMS:
        identifier = load(BP, "items", f"{item}.json")["minecraft:item"]["description"]["identifier"]
        assert f'"{identifier}"' in script


def test_the_built_addon_holds_both_packs():
    import io
    import zipfile

    names = zipfile.ZipFile(io.BytesIO(build_addon.build())).namelist()
    for folder in build_addon.PACKS:
        assert f"{folder}/manifest.json" in names
    assert "Break All the Things Behavior/scripts/main.js" in names
