// Which blocks belong together, and the flood fill that finds them. Nothing here touches the game, so the tests
// can run it under Node against a pretend world.

export const ORE_LIMIT = 64;
export const LOG_LIMIT = 256;

// Every block touching another, edges and corners included: veins and branches often only meet diagonally
const NEIGHBOURS = [];
for (let x = -1; x <= 1; x++) for (let y = -1; y <= 1; y++) for (let z = -1; z <= 1; z++) if (x || y || z) NEIGHBOURS.push({ x, y, z });
export const FACES = [{ x: 1, y: 0, z: 0 }, { x: -1, y: 0, z: 0 }, { x: 0, y: 1, z: 0 }, { x: 0, y: -1, z: 0 }, { x: 0, y: 0, z: 1 }, { x: 0, y: 0, z: -1 }];

// Blocks that grow on Nether fungi in place of leaves; they have no persistence state to tell placed from grown
const WART = new Set(["minecraft:nether_wart_block", "minecraft:warped_wart_block", "minecraft:shroomlight"]);

/** The ore an ore block is, so deepslate and stone copies of a vein and lit redstone all count as one; undefined for anything else. */
export function oreFamily(typeId) {
	const name = typeId.replace(/^minecraft:/, "").replace(/^lit_/, "").replace(/^deepslate_/, "");
	return name.endsWith("_ore") || name === "ancient_debris" ? name : undefined;
}

/** A log or a Nether stem is its own family: an oak felled takes only oak with it. Stripped logs are never part of a tree. */
export function logFamily(typeId) {
	return /_(log|stem)$/.test(typeId) && !typeId.includes("stripped_") ? typeId : undefined;
}

/** Leaves that grew there rather than were placed, which is what tells a tree from a log cabin. */
export function isNaturalLeaf(typeId, persistent) {
	return WART.has(typeId) || (typeId.includes("leaves") && persistent === false);
}

export const offset = (a, b) => ({ x: a.x + b.x, y: a.y + b.y, z: a.z + b.z });
const key = ({ x, y, z }) => `${x},${y},${z}`;

/**
 * Every block connected to start, nearest first, whose type matches, up to limit of them. start itself is left out:
 * by the time this runs the player has already broken it. typeAt returns undefined where the world is not loaded.
 */
export function collect(start, matches, typeAt, limit) {
	const found = [];
	const seen = new Set([key(start)]);
	const queue = [start];
	while (queue.length && found.length < limit) {
		const here = queue.shift();
		for (const step of NEIGHBOURS) {
			const next = offset(here, step);
			const id = key(next);
			if (seen.has(id)) continue;
			seen.add(id);
			const typeId = typeAt(next);
			if (typeId === undefined || !matches(typeId)) continue;
			found.push(next);
			queue.push(next);
			if (found.length >= limit) break;
		}
	}
	return found;
}

export const LEAF_REACH = 6;

/**
 * The leaves a felled tree takes with it. Each grown leaf belongs to whichever log is fewest steps away through other
 * leaves; the felled tree takes those within LEAF_REACH steps that are strictly nearer its logs than any other log, of a
 * neighbouring tree or of any species, and a tie stays. So where two crowns touch they part down the middle, and every
 * leaf left is nearer a living log than any leaf taken, so none is left cut off. kindAt(location) says "leaf" for a
 * grown leaf, "log" for any log or stem, and anything else for the rest. Stops looking after budget leaves.
 */
export function treeLeaves(felled, kindAt, reach = LEAF_REACH, budget = 4096) {
	const felledKeys = new Set(felled.map(key));
	// Every leaf up to twice the reach from the felled logs: far enough to find any other log nearer one of ours
	const depth = new Map();
	const others = new Map();
	let frontier = felled;
	for (let step = 1; step <= 2 * reach && frontier.length && depth.size < budget; step++) {
		const next = [];
		for (const here of frontier) {
			for (const face of FACES) {
				const there = offset(here, face);
				const id = key(there);
				if (depth.has(id) || felledKeys.has(id) || others.has(id)) continue;
				const kind = kindAt(there);
				if (kind === "log") others.set(id, there);
				else if (kind === "leaf") {
					depth.set(id, { location: there, step });
					next.push(there);
				}
			}
		}
		frontier = next;
	}
	// How far each of those leaves is from the nearest other log; a leaf as near to one of them as to the felled tree stays
	const nearestOther = new Map();
	frontier = [...others.values()];
	for (let step = 1; frontier.length; step++) {
		const next = [];
		for (const here of frontier) {
			for (const face of FACES) {
				const id = key(offset(here, face));
				if (!depth.has(id) || nearestOther.has(id)) continue;
				nearestOther.set(id, step);
				next.push(depth.get(id).location);
			}
		}
		frontier = next;
	}
	return [...depth]
		.filter(([id, leaf]) => leaf.step <= reach && leaf.step < (nearestOther.get(id) ?? Infinity))
		.map(([, leaf]) => leaf.location);
}
