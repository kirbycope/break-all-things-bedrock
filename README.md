![Break All the Things!](/development_resource_packs/break_all_things/pack_icon.png)

# Break All the Things!
A Minecraft Bedrock add-on with two tools: a pickaxe that mines a whole ore vein in one break, and an axe that fells a
whole tree, crown and all.

## Installation
1. Download the [mcaddon](https://github.com/kirbycope/break-all-things-bedrock/releases/latest/download/break-all-things-bedrock.mcaddon) from the latest release
1. Double-click the mcaddon file
1. Turn on both the behavior pack and the resource pack for your world

No experiments are needed.

## The tools

### ![Vein Pickaxe](/development_resource_packs/break_all_things/textures/items/vein_pickaxe.png) Vein Pickaxe
Break one ore block and every block of the same ore touching it goes too, through faces, edges and corners, up to 64
blocks. Stone and deepslate copies of an ore count as one vein (iron ore and deepslate iron ore together), and lit
redstone ore counts as redstone ore. Anything else, stone included, breaks one block at a time as usual.

Crafted at a crafting table: a diamond pickaxe in the middle, diamonds on the four sides, redstone in the four corners.

```
R D R
D P D      P  Diamond Pickaxe
R D R      D  Diamond      R  Redstone Dust
```

### ![Timber Axe](/development_resource_packs/break_all_things/textures/items/timber_axe.png) Timber Axe
Chop one log and every log of that tree comes down with it, up to 256, branches included. The tree's own leaves go
too, dropping their saplings, sticks and apples.

It only fells something that is plainly a tree: the logs must touch leaves that grew there. Logs with no leaves, or
only leaves a player placed, are a building, and the axe takes them one log at a time. Each kind of wood is its own
tree, so an oak never takes a birch beside it, and stripped logs are never felled. Crimson and warped stems with
their wart blocks count as trees too.

Leaves are shared out the way leaf decay sees them. Each leaf belongs to whichever log is the fewest leaf-to-leaf steps
away, and the axe takes the leaves within six steps that are strictly nearer the felled tree than any other log, of
any species. So where two crowns touch they part down the middle, a leaf exactly halfway stays, and the tree left
standing keeps every leaf of its own.

Crafted at a crafting table: a diamond axe in the middle, iron ingots on the four sides, logs of any wood in the four
corners.

```
L I L
I A I      A  Diamond Axe
L I L      I  Iron Ingot   L  any Log
```

### Both tools
- **Sneak** while breaking to take only the one block, for when you want part of a vein or a single log.
- Everything mined comes out as though the tool in your hand had mined it, so **Fortune** and **Silk Touch** work on the
  whole vein and the whole tree. The drops land in one pile where you made the first break.
- Each block costs one use, just as breaking it by hand would, and **Unbreaking** works as usual. Leaves cost nothing.
  When the tool runs out partway, it breaks and the rest of the vein or tree is left standing.
- Diamond tier: 1561 uses, diamond mining speed, enchantable like a vanilla pickaxe or axe, and repaired with diamonds
  on an anvil.
- Extra ore blocks give no experience orbs; only the block you broke yourself does.

## Development
The packs live in `development_behavior_packs/break_all_things` and `development_resource_packs/break_all_things`.
The scripting is in `scripts/`: `harvest.js` decides which blocks belong together and touches nothing in the game,
and `main.js` listens for a block broken with either tool and does the breaking.

```bash
npm test                          # the vein, tree and leaf logic, under Node against a pretend world
python -m pytest tests            # the pack files: manifests, items, recipes, textures, names, the built add-on
python tools/build_addon.py       # writes break-all-things-bedrock.mcaddon
python tools/make_textures.py     # redraws both item textures and the pack icon
```

Pushing a `v*` tag builds the `.mcaddon` and publishes it as a release (`.github/workflows/release.yml`).

### Checking in the game
`tools/client_check.py` checks the tools the way a player uses them, with real mouse input in the Minecraft client and
the world read back through the [minecraft-bedrock MCP bridge](https://github.com/chapmanjw/minecraft-bedrock-mcp-server).
It needs a local Bedrock Dedicated Server running a world with both packs and the bridge pack, the client joined to
it, and `cobblemon-bedrock` cloned beside this repository for its client driver. Each case builds what it needs on a
stone platform at y 200:

```bash
python tools/client_check.py ore        # a mixed stone and deepslate vein, coal and a stray iron ore beside it
python tools/client_check.py tree       # an oak, its crown, and a leafless log wall nearby that must stand
python tools/client_check.py twotrees   # two oaks whose crowns touch: one falls, the other keeps every leaf
python tools/client_check.py cabin      # a leafless log wall chopped: only the one log goes
python tools/client_check.py sneak      # the vein mined while sneaking: only the one block goes
```
