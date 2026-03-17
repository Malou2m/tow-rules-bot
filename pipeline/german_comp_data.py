"""
GermanComp rules data for Warhammer: The Old World.

GermanComp (v1.6.1, REV 2025-02-13) is a complete restriction, balance and
tournament system developed by the LD3 Community.  The three pillars are:
  • Restriction Pack  – improves external balance by capping top-end spam
  • Gamechanger Pack  – fixes rules abuse and broken unit interactions
  • Pointed Pack      – adjusts point costs and internal balance

Source: https://www.tinyurl.com/germancompfiles
This module returns a flat list of documents ready for embedding/ingestion.
"""

from __future__ import annotations

GC_URL = "https://www.tinyurl.com/germancompfiles"

# ---------------------------------------------------------------------------
# Each entry is one logical "section" of the GermanComp PDF.
# Fields mirror the army_data.py format so they flow through the same
# chunker/embedder/ingest pipeline.
# ---------------------------------------------------------------------------

_DOCS: list[dict] = [

    # ── Introduction ────────────────────────────────────────────────────────
    {
        "source": "german-comp",
        "type": "rule",
        "section": "Introduction",
        "army": "",
        "title": "GermanComp — Introduction and Overview",
        "text": (
            "GermanComp Overview (Version 1.6.1, REV 2025-02-13)\n\n"
            "GermanComp is a complete restriction, balance and tournament system for "
            "Warhammer: The Old World, including Scenarios, Missions and more. "
            "It is developed by the LD3 Community (Discord/Patreon).\n\n"
            "GermanComp has 3 Pillars that can be used stand-alone or in combination:\n"
            "1. The Restriction Pack – Aims at improving external balance by cutting "
            "top-end builds and spam.\n"
            "2. The Gamechanger Pack – Disables rules abuse and fixes unit rules.\n"
            "3. The Pointed Pack – Adjusts points values and allows different builds "
            "by altering army composition rules.\n\n"
            "Army lists can be built on old-world-builder.com with GermanComp enabled. "
            "Files: https://www.tinyurl.com/germancompfiles\n"
            "Tournaments are held online on Warhall; check New Recruit for details."
        ),
        "url": GC_URL,
    },

    # ── Restriction Pack — General ──────────────────────────────────────────
    {
        "source": "german-comp",
        "type": "rule",
        "section": "Restriction Pack",
        "army": "",
        "title": "GermanComp Restriction Pack — General Listbuilding Rules",
        "text": (
            "GermanComp Restriction Pack — General Listbuilding Rules\n\n"
            "At 2500 pts the standard GW restrictions apply (max 1000 pts characters "
            "total, max 500 pts per unit).\n\n"
            "At 2000 pts: no allies; Mercenaries are allowed (Rule of 3 for Merc units).\n\n"
            "GW Grand Melee format: max 500 pts per unit or character; max 0-1 Level 4 "
            "and 0-2 Level 3 Wizards.\n\n"
            "GW Combined Arms format: 0-3 per Character profile, 0-4 per Core unit, "
            "0-3 per Special unit, 0-2 per Rare unit.\n\n"
            "If a unit already has other restrictions, the strictest limit applies for the total. "
            "If a unit can be taken in multiple categories, the strictest category limit applies.\n\n"
            "Special characters are allowed and count towards the unit entry of the "
            "corresponding mundane character."
        ),
        "url": GC_URL,
    },

    {
        "source": "german-comp",
        "type": "rule",
        "section": "Restriction Pack",
        "army": "",
        "title": "GermanComp Restriction Pack — Unit Type, Size and Character Restrictions",
        "text": (
            "GermanComp Restriction Pack — Unit Type, Size and Character Restrictions\n\n"
            "• For models with a base cost of 5+ pts, max Unit Strength 40 per unit.\n"
            "• Regular & heavy Infantry units can be at most US12 wide (including all "
            "characters); all other units max US18 wide.\n"
            "• Per unit: 0-4 Characters (of any points), Monster Hunters Tapestry, "
            "Totem of Wrath.\n"
            "• Per unit: 0-2 Characters over 110 pts. Monster Hunters Tapestry included "
            "(Cavalry units 130 pts threshold).\n"
            "  – Minotaur Blood Herd, Royal Clan: only count characters over 135 pts.\n"
            "  – Ogre Kingdoms & Slayer Host are excluded from this restriction.\n"
            "• 0-4 units with the Fly (X) Special Rule.\n"
            "  – Chaos Furies (Daemons), Skink Heroes with Fly (X), and Monstrous "
            "Creatures below 100 pts count only as 0.5 towards this limit.\n"
            "  – Chaos Furies in Core can score even if they have Fly (X).\n"
            "• 0-4 War Machines or models with War Machine shooting rules. Bolt throwers "
            "do not count. Skaven Weapon Teams count as 0.5.\n"
            "• 0-5 Magic Missiles (except spells that come with units). Discard first "
            "rolled surplus, then choose if possible."
        ),
        "url": GC_URL,
    },

    # ── Restriction Pack — Army-specific ────────────────────────────────────
    {
        "source": "german-comp",
        "type": "rule",
        "section": "Restriction Pack",
        "army": "Beastmen Brayherds",
        "title": "GermanComp Restriction Pack — Beastmen Brayherds",
        "text": (
            "GermanComp Restriction Pack — Beastmen Brayherds\n\n"
            "• Dark Coven may only be used once per player turn per shaman.\n"
            "• Scourge of the Burdened and Hagtree Fetish each count as 1 towards "
            "the 0-5 Magic Missile restriction.\n"
            "• Slugskin and Vitriolic Totem count as a character for the 0-4 "
            "Characters-per-unit restriction.\n"
            "• Herdstone in Special counts towards Character points."
        ),
        "url": GC_URL,
    },

    {
        "source": "german-comp",
        "type": "rule",
        "section": "Restriction Pack",
        "army": "Kingdom of Bretonnia",
        "title": "GermanComp Restriction Pack — Kingdom of Bretonnia",
        "text": (
            "GermanComp Restriction Pack — Kingdom of Bretonnia\n\n"
            "Towards the 0-4 Fly (X) restriction the following count as additional units:\n"
            "• Lady Duchard counts as 0.5.\n"
            "• Virtue of Knightly Temper on a Cavalry Troop Type Duke or Baron: 0.5.\n"
            "• Each Pegasus Knight unit over 4 models: 0.5.\n"
            "• Every full 6 Pegasus Knights (in Special): 0.5.\n"
            "• Green Knight: counts as 1."
        ),
        "url": GC_URL,
    },

    {
        "source": "german-comp",
        "type": "rule",
        "section": "Restriction Pack",
        "army": "Grand Cathay",
        "title": "GermanComp Restriction Pack — Grand Cathay (incl. Jade Fleet)",
        "text": (
            "GermanComp Restriction Pack — Grand Cathay (Jade Fleet: see also Empire restrictions)\n\n"
            "• Miao Ying, Characters on Sky Lanterns, and Shugengan Lords above 340 pts "
            "each count as an additional 0.5 Fly (X) unit.\n"
            "• Army composition changed to require 33% Core (instead of standard 25%).\n"
            "• Ogre Loader and Ring of Jet each count as a unit towards the 0-4 War "
            "Machine restriction."
        ),
        "url": GC_URL,
    },

    {
        "source": "german-comp",
        "type": "rule",
        "section": "Restriction Pack",
        "army": "Empire of Man",
        "title": "GermanComp Restriction Pack — Empire of Man",
        "text": (
            "GermanComp Restriction Pack — Empire of Man\n\n"
            "• Each unit of Outriders in Special or Mercenaries counts as one War Machine "
            "towards the 0-4 War Machine restriction."
        ),
        "url": GC_URL,
    },

    {
        "source": "german-comp",
        "type": "rule",
        "section": "Restriction Pack",
        "army": "Tomb Kings of Khemri",
        "title": "GermanComp Restriction Pack — Tomb Kings of Khemri",
        "text": (
            "GermanComp Restriction Pack — Tomb Kings of Khemri\n\n"
            "• 0-3 of each: Necrolith Bone Dragon, Necrosphinx, Warding Splint, "
            "Talisman of Protection.\n"
            "• High Priests with Necromancy count as an additional unit for the 0-4 "
            "War Machine restriction.\n"
            "• Each started group of 3 Ushabti with Greatbow counts as an additional "
            "unit for the 0-4 War Machine restriction."
        ),
        "url": GC_URL,
    },

    {
        "source": "german-comp",
        "type": "rule",
        "section": "Restriction Pack",
        "army": "Orc & Goblin Tribes",
        "title": "GermanComp Restriction Pack — Orcs & Goblins",
        "text": (
            "GermanComp Restriction Pack — Orcs & Goblins\n\n"
            "• 0-1 Fanatic per unit of: Night Goblins, Night Goblin Characters, "
            "Squig Herd / Squig Hoppaz.\n"
            "• Arachnarok Spider counts as 3 towards the Fanatic limit."
        ),
        "url": GC_URL,
    },

    {
        "source": "german-comp",
        "type": "rule",
        "section": "Restriction Pack",
        "army": "Vampire Counts",
        "title": "GermanComp Restriction Pack — Vampire Counts",
        "text": (
            "GermanComp Restriction Pack — Vampire Counts\n\n"
            "• 0-2 Master Necromancers.\n"
            "• 0-2 of: Master Necromancer + Mortis Engine combined.\n"
            "• 0-2 of: Master Necromancer + Sceptre De Noirot + Dark Acolyte combined.\n"
            "• Zombies do not count towards the 25% Core minimum.\n"
            "• Units with the Wailing Dirge special rule count towards the 0-5 Magic "
            "Missile restriction.\n"
            "• Max 400 pts on Grave Guard in Core.\n"
            "• Drakenhof Banner & Helm of Commandment count as a character over 110 pts "
            "for both the 0-2 and 0-4 Character-per-unit restrictions."
        ),
        "url": GC_URL,
    },

    # ── Gamechanger Pack — Universal ────────────────────────────────────────
    {
        "source": "german-comp",
        "type": "rule",
        "section": "Gamechanger Pack",
        "army": "",
        "title": "GermanComp Gamechanger Pack — Universal Rule Changes",
        "text": (
            "GermanComp Gamechanger Pack — Universal Rule Changes\n\n"
            "The following factions use the Renegade Pack rules as a base: "
            "Chaos Dwarfs, Daemons of Chaos, Dark Elves, Lizardmen, Ogre Kingdoms, "
            "Skaven, Vampire Counts.\n\n"
            "Universal changes applying to all armies:\n"
            "• Characters may choose to use mundane weapons even if equipped with a "
            "Dragon Slayer Sword or Burning Blade.\n"
            "• Movement cap: at the end of a normal move or march, no model may have "
            "moved further than 3× its Movement (in marching column) or 2× its Movement "
            "(in any other case), measured from absolute start to end point of the base. "
            "This prevents excessive wheeling by the back rank.\n"
            "• Units that Vanguard may charge in the first battle round but NOT in the "
            "first (beginning) player turn.\n"
            "• Monstrous Infantry (except Ushabti) may use Press of Battle.\n"
            "• Infantry may use Press of Battle when charging.\n"
            "• Thrusting Spears improve their Strength by 1 in the front arc if the "
            "unit was charged.\n"
            "• Additional Hand Weapons gain any Special Rules that Hand Weapons have "
            "on that model (e.g. Ensorcelled Weapons).\n"
            "• All Trolls gain Extra Attack (1) and Stubborn.\n"
            "• The +1 Attack from Frenzy always applies, not only when charging.\n"
            "• 'Serrated Maw' has AP1.\n"
            "• All Ogres gain MR(1) and Regeneration (6+). 'Ogres' for this rule: "
            "Badland Ogres, Chaos Ogres, Imperial Ogres, Ogre Bulls, Ironguts, "
            "Maneaters, Mournfang Cavalry, Leadbelchers, Gorgers, all Ogre Kingdom "
            "Characters, Stonehorn Riders, Thundertusk Riders.\n"
            "• Add Warband to Chaos Ogres, Badland Ogres, Imperial Ogres and Ogre Bulls."
        ),
        "url": GC_URL,
    },

    # ── Gamechanger Pack — Army-specific ────────────────────────────────────
    {
        "source": "german-comp",
        "type": "rule",
        "section": "Gamechanger Pack",
        "army": "Beastmen Brayherds",
        "title": "GermanComp Gamechanger Pack — Beastmen Brayherds",
        "text": (
            "GermanComp Gamechanger Pack — Beastmen Brayherds\n\n"
            "• Dragon Ogre Shaggoth and Cygor: set Toughness to 6 and Troop Type to Behemoth.\n"
            "• Cockatrice gains Wicked Claws (AP2).\n"
            "• Warped Gors gain Bestial Charge and Chaos Armour (5+ Ward Save) special rules.\n"
            "• Minotaur units in Blood Herd get Counter Charge, including Characters joining them."
        ),
        "url": GC_URL,
    },

    {
        "source": "german-comp",
        "type": "rule",
        "section": "Gamechanger Pack",
        "army": "Kingdom of Bretonnia",
        "title": "GermanComp Gamechanger Pack — Kingdom of Bretonnia",
        "text": (
            "GermanComp Gamechanger Pack — Kingdom of Bretonnia\n\n"
            "• Grail Reliquae has US6; if the unit contains a Grail Reliquae, the whole "
            "unit has Blessings of the Lady.\n"
            "• If the Green Knight is slain at least once, he gives up half his VPs (full "
            "VPs if finally defeated or absent at game end); he may charge in the 1st battle "
            "round but NOT in the 1st (beginning) player turn.\n"
            "• Questing Knights: set Attacks to 2; Paragon set to 3."
        ),
        "url": GC_URL,
    },

    {
        "source": "german-comp",
        "type": "rule",
        "section": "Gamechanger Pack",
        "army": "Chaos Dwarfs",
        "title": "GermanComp Gamechanger Pack — Chaos Dwarfs",
        "text": (
            "GermanComp Gamechanger Pack — Chaos Dwarfs\n\n"
            "• K'daai Fireborn gain a 5+ Ward Save against non-magical attacks "
            "(from the 'Dark Runes' special rule)."
        ),
        "url": GC_URL,
    },

    {
        "source": "german-comp",
        "type": "rule",
        "section": "Gamechanger Pack",
        "army": "Dark Elves",
        "title": "GermanComp Gamechanger Pack — Dark Elves",
        "text": (
            "GermanComp Gamechanger Pack — Dark Elves\n\n"
            "• Medusa: add the Terror special rule and Halberd.\n"
            "• Witch Elves and Sisters of Slaughter: add Warband.\n"
            "• Black Ark Corsairs: add Ambush and Vanguard special rules.\n"
            "• Hydra and Kharybdis: set Toughness to 6.\n"
            "• Cold One Knights, Mounts and Chariots gain Counter Charge."
        ),
        "url": GC_URL,
    },

    {
        "source": "german-comp",
        "type": "rule",
        "section": "Gamechanger Pack",
        "army": "Dwarfen Mountain Holds",
        "title": "GermanComp Gamechanger Pack — Dwarfen Mountain Holds",
        "text": (
            "GermanComp Gamechanger Pack — Dwarfen Mountain Holds\n\n"
            "• Models on Shieldbearers have US4.\n"
            "• Slayer Host: may take up to 6 Doomseekers.\n"
            "• Slayer Host: the army inherits the special rules of Royal Clan.\n"
            "• Royal Clan Warriors keep their Shields when purchasing Great Axes."
        ),
        "url": GC_URL,
    },

    {
        "source": "german-comp",
        "type": "rule",
        "section": "Gamechanger Pack",
        "army": "Daemons of Chaos",
        "title": "GermanComp Gamechanger Pack — Daemons of Chaos",
        "text": (
            "GermanComp Gamechanger Pack — Daemons of Chaos\n\n"
            "• Core regular and heavy Infantry gain the Warband special rule.\n"
            "• Bloodletters: set Toughness to 4."
        ),
        "url": GC_URL,
    },

    {
        "source": "german-comp",
        "type": "rule",
        "section": "Gamechanger Pack",
        "army": "Empire of Man",
        "title": "GermanComp Gamechanger Pack — Empire of Man",
        "text": (
            "GermanComp Gamechanger Pack — Empire of Man\n\n"
            "• Demigryph Mount: set Toughness to +1 (i.e. one higher than the rider's).\n"
            "• High Priests of Ulric and Archlector of Sigmar may attempt to cast two "
            "different prayers per turn."
        ),
        "url": GC_URL,
    },

    {
        "source": "german-comp",
        "type": "rule",
        "section": "Gamechanger Pack",
        "army": "High Elf Realms",
        "title": "GermanComp Gamechanger Pack — High Elf Realms",
        "text": (
            "GermanComp Gamechanger Pack — High Elf Realms\n\n"
            "• Storm Weavers gain Lileath's Blessing.\n"
            "• Sea Garrison — Commander: change Wounds to 3. Storm Weavers gain Naval Discipline.\n"
            "• Sea Garrison and Chracian Warhost: change army composition to require 25% Core."
        ),
        "url": GC_URL,
    },

    {
        "source": "german-comp",
        "type": "rule",
        "section": "Gamechanger Pack",
        "army": "Tomb Kings of Khemri",
        "title": "GermanComp Gamechanger Pack — Tomb Kings of Khemri",
        "text": (
            "GermanComp Gamechanger Pack — Tomb Kings of Khemri\n\n"
            "• Icon of Rakaph cannot be used to pursue into a fresh enemy unit.\n"
            "• For Arise!: Tomb Guard count as heavy cavalry (healed with wizard level +1)."
        ),
        "url": GC_URL,
    },

    {
        "source": "german-comp",
        "type": "rule",
        "section": "Gamechanger Pack",
        "army": "Lizardmen",
        "title": "GermanComp Gamechanger Pack — Lizardmen",
        "text": (
            "GermanComp Gamechanger Pack — Lizardmen\n\n"
            "• All Saurus Heroes switch their Scaly Skin for a suit of Light Armour "
            "and the Armoured Hide (1) special rule.\n"
            "• The Apotheosis spell can target units of the Monster troop type, but "
            "will only restore 1 wound.\n"
            "• For each Saurus Hero, 0-1 Saurus Warriors unit and/or Carnosaur gain "
            "+1 Weapon Skill and +1 Initiative.\n"
            "• Ripperdactyls and Terradons can score if they have US10.\n"
            "• Kroxigors: change Heavy Armour to Full Plate Armour.\n"
            "• Cold One Riders: add Counter Charge."
        ),
        "url": GC_URL,
    },

    {
        "source": "german-comp",
        "type": "rule",
        "section": "Gamechanger Pack",
        "army": "Ogre Kingdoms",
        "title": "GermanComp Gamechanger Pack — Ogre Kingdoms",
        "text": (
            "GermanComp Gamechanger Pack — Ogre Kingdoms\n\n"
            "• Scraplauncher: set Toughness to 6.\n"
            "• Clarification on Ironfists:\n"
            "  – Models with Ironfists can use Parry (if Infantry wielding an ordinary "
            "Hand Weapon alongside the Ironfist).\n"
            "  – Models with Magic Weapons can use Ironfists alongside them "
            "(gaining +1 Save and +1 Attack with the Ironfist).\n"
            "  – Models with access to Magic Items can buy Magic Shields if they "
            "have access to Ironfists."
        ),
        "url": GC_URL,
    },

    {
        "source": "german-comp",
        "type": "rule",
        "section": "Gamechanger Pack",
        "army": "Orc & Goblin Tribes",
        "title": "GermanComp Gamechanger Pack — Orcs & Goblins Nomadic Waaagh",
        "text": (
            "GermanComp Gamechanger Pack — Orcs & Goblins (Nomadic Waaagh)\n\n"
            "• Strength Modifiers on models (Big 'Unz, Charge bonuses) influence "
            "the Strength of Impact Hits."
        ),
        "url": GC_URL,
    },

    {
        "source": "german-comp",
        "type": "rule",
        "section": "Gamechanger Pack",
        "army": "Skaven",
        "title": "GermanComp Gamechanger Pack — Skaven",
        "text": (
            "GermanComp Gamechanger Pack — Skaven\n\n"
            "• The Bearer of the Fellblade loses a wound on a roll of a D6 instead of a D3.\n"
            "• Doomwheel — Zzzap! special rule cannot hit the Doomwheel itself; "
            "templates stop when they hit it.\n"
            "• Poisoned Wind Globadiers and Jezzails: change Ballistic Skill to 4 and "
            "add Poisoned Attacks ('Skryre Experts').\n"
            "• Plagueclaw Catapult: D3+1 Damage (under the hole; only vs one model that was hit).\n"
            "• Rat Ogres gain Warpstone Claws (same as Abomination)."
        ),
        "url": GC_URL,
    },

    {
        "source": "german-comp",
        "type": "rule",
        "section": "Gamechanger Pack",
        "army": "Vampire Counts",
        "title": "GermanComp Gamechanger Pack — Vampire Counts",
        "text": (
            "GermanComp Gamechanger Pack — Vampire Counts\n\n"
            "• For Invocation of Nehek: Grave Guard count as heavy cavalry "
            "(healed with wizard level bonus)."
        ),
        "url": GC_URL,
    },

    {
        "source": "german-comp",
        "type": "rule",
        "section": "Gamechanger Pack",
        "army": "Warriors of Chaos",
        "title": "GermanComp Gamechanger Pack — Warriors of Chaos",
        "text": (
            "GermanComp Gamechanger Pack — Warriors of Chaos\n\n"
            "• Chaos Lord: add Veteran special rule."
        ),
        "url": GC_URL,
    },

    {
        "source": "german-comp",
        "type": "rule",
        "section": "Gamechanger Pack",
        "army": "Wood Elf Realms",
        "title": "GermanComp Gamechanger Pack — Wood Elves",
        "text": (
            "GermanComp Gamechanger Pack — Wood Elves\n\n"
            "• Sisters of the Thorn may choose their spells from their chosen lore "
            "or the Lore of Athel Loren.\n"
            "• Glade Riders: add Move Through Cover.\n"
            "• Units in Close Order do not become disrupted by Woods.\n"
            "• Warhawk Riders: add Reserve Move; they are scoring units if above US10 "
            "despite having Fly (X).\n"
            "• All Tree Spirits gain a 5+ Ward Save against non-magical attacks "
            "('Dark Runes' special rule).\n"
            "• Wildwood Rangers: set Strength to 4."
        ),
        "url": GC_URL,
    },
]


def fetch_german_comp_data() -> list[dict]:
    """
    Return all GermanComp rule documents as a flat list.

    No network calls — data is hardcoded from the official GermanComp PDF
    (v1.6.1, REV 2025-02-13).  Returns immediately.
    """
    print(f"GermanComp data: {len(_DOCS)} documents loaded (v1.6.1)")
    return _DOCS


if __name__ == "__main__":
    docs = fetch_german_comp_data()
    print(f"\nTotal German Comp docs: {len(docs)}")
    for d in docs:
        army = f" [{d['army']}]" if d["army"] else ""
        print(f"  [{d['section']}]{army} {d['title']}")
