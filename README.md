![Break All the Things!](/development_resource_packs/break_all_things/pack_icon.png)

# Break All the Things!
Mine a whole ore vein or fell a whole tree in one swing.

## Installation
1. Download the [mcaddon](https://github.com/kirbycope/break-all-things-bedrock/releases/latest/download/break-all-things-bedrock.mcaddon) from the latest release
1. Double-click the mcaddon file
1. Turn on the Behavior and Resource packs for your world

## Tools
 - ![Vein Pickaxe](/development_resource_packs/break_all_things/textures/items/vein_pickaxe.png) Vein Pickaxe: Mines every connected block of the same ore, stone and deepslate alike.
 - ![Timber Axe](/development_resource_packs/break_all_things/textures/items/timber_axe.png) Timber Axe: Fells the whole tree and its leaves. A neighbouring tree keeps its own leaves, and log builds without leaves are left alone.

Sneak to break just one block. Fortune, Silk Touch and Unbreaking work on every block, and each block costs one use.

## Recipes
```
Vein Pickaxe        Timber Axe
R D R               L I L
D P D               I A I
R D R               L I L

P Diamond Pickaxe   A Diamond Axe
D Diamond           I Iron Ingot
R Redstone Dust     L Any Log
```

## Development
```bash
npm test                         # vein, tree and leaf logic
python -m pytest tests           # pack files
python tools/build_addon.py      # builds the .mcaddon
```
Pushing a `v*` tag publishes a release. Credits are in [CREDITS.md](CREDITS.md).
