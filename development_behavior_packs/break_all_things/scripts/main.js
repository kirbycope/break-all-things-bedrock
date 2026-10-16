import { world, EquipmentSlot, GameMode } from "@minecraft/server";
import { FACES, LOG_LIMIT, ORE_LIMIT, collect, isNaturalLeaf, logFamily, offset, oreFamily, treeLeaves } from "./harvest.js";

// The tools: what each one takes the rest of, whether it needs to see leaves first so a house is not felled, and the
// block tag its digger component mines quickly, which is also what wears it, the way a vanilla tool is not worn by grass
const TOOLS = {
	"breakall:vein_pickaxe": { family: oreFamily, limit: ORE_LIMIT, tree: false, wornBy: "minecraft:is_pickaxe_item_destructible" },
	"breakall:timber_axe": { family: logFamily, limit: LOG_LIMIT, tree: true, wornBy: "minecraft:is_axe_item_destructible" },
};

/** The block at a location, or undefined where the chunk is not loaded or the location is outside the world. */
function blockAt(dimension, location) {
	try {
		return dimension.getBlock(location);
	} catch {
		return undefined;
	}
}

/** True when grown leaves touch any of the logs, the start included. */
function hasLeaves(dimension, logs) {
	for (const log of logs) {
		for (const face of FACES) {
			const block = blockAt(dimension, offset(log, face));
			if (block && isNaturalLeaf(block.typeId, block.permutation.getState("persistent_bit"))) return true;
		}
	}
	return false;
}

/** Adds a stack to the pile, topping up a matching stack before starting a new one. */
function addTo(drops, stack) {
	for (const held of drops) {
		if (!held.isStackableWith(stack) || held.amount >= held.maxAmount) continue;
		const room = held.maxAmount - held.amount;
		if (stack.amount <= room) {
			held.amount += stack.amount;
			return;
		}
		held.amount = held.maxAmount;
		stack.amount -= room; // never down to zero, which an ItemStack refuses
	}
	drops.push(stack);
}

/** What a block is to a tree: "leaf" for a grown leaf, "log" for any log or stem, stripped or not, else undefined. */
function treeKind(dimension, location) {
	const block = blockAt(dimension, location);
	if (!block) return undefined;
	if (/_(log|stem)$/.test(block.typeId)) return "log";
	return isNaturalLeaf(block.typeId, block.permutation.getState("persistent_bit")) ? "leaf" : undefined;
}

/**
 * Wears the tool for the block the player broke, then breaks every found block as though the tool in hand had mined
 * it, Fortune and Silk Touch included, dropping what they give where the first block was. Each block costs a use, as a
 * normal break does; when the tool runs out it breaks and the rest of the blocks stay. Leaves come last and cost
 * nothing, as they would have rotted away anyway, and only when the tool lasted through the logs.
 */
function harvest(player, dimension, origin, found, firstBlockUnpaid, leaves = []) {
	const equippable = player.getComponent("minecraft:equippable");
	const item = equippable?.getEquipment(EquipmentSlot.Mainhand);
	if (!item) return;
	const durability = item.getComponent("minecraft:durability");
	const unbreaking = item.getComponent("minecraft:enchantable")?.getEnchantment("unbreaking")?.level ?? 0;
	const wears = durability !== undefined && player.getGameMode() !== GameMode.Creative;
	const loot = world.getLootTableManager();
	const drop = { x: origin.x + 0.5, y: origin.y + 0.5, z: origin.z + 0.5 };

	/** Takes one use off the tool, false when it has none left to give. */
	const wear = () => {
		if (!wears || Math.random() * 100 >= durability.getDamageChance(unbreaking)) return true;
		if (durability.damage >= durability.maxDurability) return false;
		durability.damage += 1;
		return true;
	};

	let intact = !firstBlockUnpaid || wear();
	const drops = [];
	for (const location of found) {
		if (!intact) break;
		const block = blockAt(dimension, location);
		if (!block) continue;
		if (!wear()) {
			intact = false;
			break;
		}
		for (const stack of loot.generateLootFromBlock(block, item) ?? []) addTo(drops, stack);
		block.setType("minecraft:air");
	}
	for (const location of intact ? leaves : []) {
		const block = blockAt(dimension, location);
		if (!block || !isNaturalLeaf(block.typeId, block.permutation.getState("persistent_bit"))) continue;
		for (const stack of loot.generateLootFromBlock(block, item) ?? []) addTo(drops, stack);
		block.setType("minecraft:air");
	}
	// Full stacks, dropped dead still, so a whole vein lands as one pile in the hole rather than spraying down the tunnel
	for (const stack of drops) dimension.spawnItem(stack, drop).clearVelocity();

	if (intact) {
		equippable.setEquipment(EquipmentSlot.Mainhand, item);
	} else {
		equippable.setEquipment(EquipmentSlot.Mainhand, undefined);
		player.playSound("random.break");
	}
}

world.afterEvents.playerBreakBlock.subscribe(({ player, block, dimension, brokenBlockPermutation, itemStackBeforeBreak, itemStackAfterBreak }) => {
	const tool = TOOLS[itemStackBeforeBreak?.typeId];
	if (!tool) return;
	// The game does not wear a custom tool for the block the player broke; pay for it here, unless a version that does already has
	const before = itemStackBeforeBreak.getComponent("minecraft:durability")?.damage;
	const after = itemStackAfterBreak?.getComponent("minecraft:durability")?.damage;
	const unpaid = before === after && brokenBlockPermutation.hasTag(tool.wornBy);

	const origin = block.location;
	const family = tool.family(brokenBlockPermutation.type.id);
	// Sneaking breaks just the one block, for when only part of a vein or a log wall is wanted
	let found = [];
	let leaves = [];
	if (family !== undefined && !player.isSneaking) {
		found = collect(origin, (typeId) => tool.family(typeId) === family, (location) => blockAt(dimension, location)?.typeId, tool.limit);
		if (tool.tree) {
			if (!hasLeaves(dimension, [origin, ...found])) found = [];
			else leaves = treeLeaves([origin, ...found], (location) => treeKind(dimension, location));
		}
	}
	if (unpaid || found.length || leaves.length) harvest(player, dimension, origin, found, unpaid, leaves);
});
