"""
Fetches army/unit data from the old-world-builder GitHub repo.

Data lives in two locations in the repo:
  public/games/the-old-world/<army-slug>.json  — one file per army, with units
  src/assets/lores-of-magic-with-spells.json   — all spell lores

Results cached to pipeline/cache/army_data.json.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx

CACHE_FILE = Path("pipeline/cache/army_data.json")

GITHUB_RAW = "https://raw.githubusercontent.com/nthiebes/old-world-builder/main"

ARMY_SLUGS = [
    "beastmen-brayherds", "chaos-dwarfs", "daemons-of-chaos", "dark-elves",
    "dwarfen-mountain-holds", "empire-of-man", "grand-cathay", "high-elf-realms",
    "kingdom-of-bretonnia", "lizardmen", "magic-items", "ogre-kingdoms",
    "orc-and-goblin-tribes", "renegade-crowns", "skaven", "tomb-kings-of-khemri",
    "vampire-counts", "warriors-of-chaos", "wood-elf-realms",
]

UNIT_CATEGORIES = ["characters", "core", "special", "rare", "mercenaries"]


def _army_name(slug: str) -> str:
    return slug.replace("-", " ").title()


def _list_to_str(items: list, key: str = "name_en") -> str:
    return ", ".join(i.get(key, "") for i in items if i.get(key))


def _unit_to_text(unit: dict, army_name: str, category: str) -> str:
    lines = []
    name = unit.get("name_en") or unit.get("id") or "Unknown Unit"
    lines.append(f"Unit: {name} ({army_name}) — {category.title()}")

    if "points" in unit:
        suffix = " per model" if unit.get("perModel") else ""
        lines.append(f"Points: {unit['points']}{suffix}")

    if "minimum" in unit and unit["minimum"]:
        lines.append(f"Min size: {unit['minimum']}")
    if "maximum" in unit and unit["maximum"]:
        lines.append(f"Max size: {unit['maximum']}")

    # Command (champion, standard bearer, musician)
    command = unit.get("command", [])
    if command:
        lines.append(f"Command: {_list_to_str(command)}")

    # Equipment
    equipment = unit.get("equipment", [])
    if equipment:
        lines.append(f"Equipment: {_list_to_str(equipment)}")

    # Armour
    armor = unit.get("armor", [])
    if armor:
        lines.append(f"Armour: {_list_to_str(armor)}")

    # Options
    options = unit.get("options", [])
    if options:
        lines.append(f"Options: {_list_to_str(options)}")

    # Special rules
    for key in ["specialRules", "special_rules", "abilities"]:
        val = unit.get(key)
        if val:
            if isinstance(val, list):
                lines.append(f"Special Rules: {_list_to_str(val)}")
            elif isinstance(val, str):
                lines.append(f"Special Rules: {val}")
            break

    # Magic allowance
    magic = unit.get("magic")
    if magic and isinstance(magic, dict):
        types = ", ".join(magic.get("types", []))
        pts = magic.get("maxPoints", 0)
        if types:
            lines.append(f"Magic items: {types} (max {pts} pts)")

    return "\n".join(lines)


def _spell_to_text(spell: dict, lore_name: str) -> str:
    lines = []
    name = spell.get("name_en") or spell.get("name") or "Unknown Spell"
    lines.append(f"Spell: {name} (Lore of {lore_name})")

    for key in ["castingValue", "casting_value", "cast"]:
        if key in spell:
            lines.append(f"Casting Value: {spell[key]}")
            break

    for key in ["range", "duration", "type"]:
        if key in spell:
            lines.append(f"{key.title()}: {spell[key]}")

    for key in ["effect", "description", "description_en", "text"]:
        val = spell.get(key)
        if val and isinstance(val, str):
            lines.append(f"Effect: {val}")
            break

    return "\n".join(lines)


def fetch_army_data(force: bool = False) -> list[dict]:
    """
    Fetch all army/unit/spell data from the old-world-builder GitHub repo.
    Returns a flat list of text documents ready for chunking/embedding.
    """
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)

    if CACHE_FILE.exists() and not force:
        print(f"Loading army data from cache ({CACHE_FILE})")
        return json.loads(CACHE_FILE.read_text())

    print("Fetching army data from old-world-builder GitHub...")
    all_docs = []

    with httpx.Client(timeout=60.0, follow_redirects=True) as client:
        # ── Per-army unit files ───────────────────────────────────────────────
        for slug in ARMY_SLUGS:
            url = f"{GITHUB_RAW}/public/games/the-old-world/{slug}.json"
            try:
                resp = client.get(url)
                resp.raise_for_status()
                data = resp.json()
                army = _army_name(slug)

                for category in UNIT_CATEGORIES:
                    for unit in data.get(category, []):
                        if not isinstance(unit, dict):
                            continue
                        text = _unit_to_text(unit, army, category)
                        name = unit.get("name_en") or unit.get("id") or ""
                        all_docs.append({
                            "source": "old-world-builder",
                            "type": "unit",
                            "army": army,
                            "category": category,
                            "title": name,
                            "text": text,
                            "url": "https://old-world-builder.com",
                        })

                print(f"  {army}: {sum(len(data.get(c, [])) for c in UNIT_CATEGORIES)} units")
            except Exception as e:
                print(f"  Warning: failed to fetch {slug}: {e}")

        # Note: lores-of-magic-with-spells.json only contains spell names and
        # indices — no casting values or effect text. Full spell rules are
        # already covered by the tow.whfb.app scrape, so we skip this file.

    CACHE_FILE.write_text(json.dumps(all_docs, indent=2, ensure_ascii=False))
    print(f"Army data: {len(all_docs)} documents → cached to {CACHE_FILE}")
    return all_docs


if __name__ == "__main__":
    docs = fetch_army_data(force=True)
    print(f"\nDone. Total army docs: {len(docs)}")
    if docs:
        print("\nSample unit:")
        print(docs[0]["text"])
