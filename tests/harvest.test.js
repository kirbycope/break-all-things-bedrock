// The flood fill and the block families, run under Node against a pretend world: `npm test`
import assert from "node:assert/strict";
import { test } from "node:test";
import { LOG_LIMIT, ORE_LIMIT, collect, isNaturalLeaf, logFamily, oreFamily, treeLeaves } from "../development_behavior_packs/break_all_things/scripts/harvest.js";

/** A world made of the listed blocks, stone everywhere else. */
function world(blocks) {
	const map = new Map(Object.entries(blocks));
	return ({ x, y, z }) => map.get(`${x},${y},${z}`) ?? "minecraft:stone";
}

const sameOre = (family) => (typeId) => oreFamily(typeId) === family;

test("deepslate, stone and lit copies of an ore are one vein", () => {
	assert.equal(oreFamily("minecraft:iron_ore"), "iron_ore");
	assert.equal(oreFamily("minecraft:deepslate_iron_ore"), "iron_ore");
	assert.equal(oreFamily("minecraft:lit_deepslate_redstone_ore"), "redstone_ore");
	assert.equal(oreFamily("minecraft:redstone_ore"), "redstone_ore");
	assert.equal(oreFamily("minecraft:nether_gold_ore"), "nether_gold_ore");
	assert.equal(oreFamily("minecraft:ancient_debris"), "ancient_debris");
});

test("stone, raw ore blocks and logs are not ore", () => {
	for (const typeId of ["minecraft:stone", "minecraft:raw_iron_block", "minecraft:iron_block", "minecraft:oak_log", "minecraft:deepslate"]) {
		assert.equal(oreFamily(typeId), undefined, typeId);
	}
});

test("logs and stems are trees, stripped logs and planks are not", () => {
	assert.equal(logFamily("minecraft:oak_log"), "minecraft:oak_log");
	assert.equal(logFamily("minecraft:cherry_log"), "minecraft:cherry_log");
	assert.equal(logFamily("minecraft:crimson_stem"), "minecraft:crimson_stem");
	assert.equal(logFamily("minecraft:stripped_oak_log"), undefined);
	assert.equal(logFamily("minecraft:oak_planks"), undefined);
	assert.equal(logFamily("minecraft:iron_ore"), undefined);
});

test("only grown leaves mark a tree", () => {
	assert.equal(isNaturalLeaf("minecraft:oak_leaves", false), true);
	assert.equal(isNaturalLeaf("minecraft:oak_leaves", true), false);
	assert.equal(isNaturalLeaf("minecraft:azalea_leaves_flowered", false), true);
	assert.equal(isNaturalLeaf("minecraft:nether_wart_block", undefined), true);
	assert.equal(isNaturalLeaf("minecraft:oak_log", undefined), false);
});

test("a vein is followed through faces, edges and corners, and the broken block is left out", () => {
	const typeAt = world({
		"1,0,0": "minecraft:iron_ore",
		"2,1,0": "minecraft:deepslate_iron_ore", // edge of 1,0,0
		"3,2,1": "minecraft:iron_ore", // corner of 2,1,0
		"5,2,1": "minecraft:iron_ore", // two blocks away: a different vein
		"0,1,0": "minecraft:coal_ore", // touching, but another ore
	});
	const found = collect({ x: 0, y: 0, z: 0 }, sameOre("iron_ore"), typeAt, ORE_LIMIT);
	assert.deepEqual(found, [{ x: 1, y: 0, z: 0 }, { x: 2, y: 1, z: 0 }, { x: 3, y: 2, z: 1 }]);
});

test("a lone ore block finds nothing more", () => {
	assert.deepEqual(collect({ x: 0, y: 0, z: 0 }, sameOre("diamond_ore"), world({}), ORE_LIMIT), []);
});

test("the fill stops at its limit", () => {
	const blocks = {};
	for (let y = 1; y <= 400; y++) blocks[`0,${y},0`] = "minecraft:oak_log";
	const found = collect({ x: 0, y: 0, z: 0 }, (typeId) => typeId === "minecraft:oak_log", world(blocks), LOG_LIMIT);
	assert.equal(found.length, LOG_LIMIT);
	assert.deepEqual(found[0], { x: 0, y: 1, z: 0 }, "nearest first");
});

test("an unloaded block ends the vein there", () => {
	// Ore runs from x=1 to x=5, but past x=2 the chunk is not loaded
	const typeAt = ({ x, y, z }) => (x > 2 ? undefined : y === 0 && z === 0 && x >= 1 && x <= 5 ? "minecraft:gold_ore" : "minecraft:stone");
	assert.deepEqual(collect({ x: 0, y: 0, z: 0 }, sameOre("gold_ore"), typeAt, ORE_LIMIT), [{ x: 1, y: 0, z: 0 }, { x: 2, y: 0, z: 0 }]);
});

/** A pretend world of kinds: "log" and "leaf" where listed, nothing elsewhere. */
function kinds(logs, leaves) {
	const map = new Map();
	for (const p of leaves) map.set(`${p.x},${p.y},${p.z}`, "leaf");
	for (const p of logs) map.set(`${p.x},${p.y},${p.z}`, "log");
	return ({ x, y, z }) => map.get(`${x},${y},${z}`);
}

/** A trunk of height h at x, z and a crown: a box of leaves of the given radius round its top. */
function oak(x, z, h, radius) {
	const logs = [];
	for (let y = 0; y < h; y++) logs.push({ x, y, z });
	const leaves = [];
	for (let dx = -radius; dx <= radius; dx++) for (let dz = -radius; dz <= radius; dz++) for (let y = h - 2; y <= h; y++) {
		if (!(dx === 0 && dz === 0 && y < h)) leaves.push({ x: x + dx, y, z: z + dz });
	}
	return { logs, leaves };
}

test("a lone tree's whole crown goes with it", () => {
	const tree = oak(0, 0, 5, 2);
	const leaves = treeLeaves(tree.logs, kinds(tree.logs, tree.leaves));
	assert.equal(leaves.length, tree.leaves.length);
});

test("where two crowns touch, each keeps its own side", () => {
	const a = oak(0, 0, 5, 2);
	const b = oak(5, 0, 5, 2); // its crown runs x 3..7, touching a's at x 2 and 3
	const kindAt = kinds([...a.logs, ...b.logs], [...a.leaves, ...b.leaves]);
	const taken = new Set(treeLeaves(a.logs, kindAt).map(({ x, y, z }) => `${x},${y},${z}`));
	for (const p of b.leaves) assert.ok(!taken.has(`${p.x},${p.y},${p.z}`), `took the neighbour's leaf at ${p.x},${p.y},${p.z}`);
	// and a loses its whole crown, the side facing b included, though b is within reach of most of it
	assert.equal(taken.size, a.leaves.length);
});

test("one shared canopy parts down the middle, a tie staying", () => {
	// Trunks at x 0 and x 6, one row of leaves joining their tops: x 1..2 are a's, x 3 is a tie, x 4..5 are b's
	const logs = [{ x: 0, y: 0, z: 0 }, { x: 6, y: 0, z: 0 }];
	const leaves = [1, 2, 3, 4, 5].map((x) => ({ x, y: 0, z: 0 }));
	const taken = treeLeaves([logs[0]], kinds(logs, leaves));
	assert.deepEqual(taken.map((p) => p.x).sort(), [1, 2]);
});

test("leaves too far from the felled logs to have hung on them stay", () => {
	const logs = [{ x: 0, y: 0, z: 0 }];
	const leaves = [];
	for (let x = 1; x <= 9; x++) leaves.push({ x, y: 0, z: 0 });
	const taken = treeLeaves(logs, kinds(logs, leaves));
	assert.deepEqual(taken.map((p) => p.x).sort((a, b) => a - b), [1, 2, 3, 4, 5, 6]);
});
