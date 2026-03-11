"""
Fetches army/unit data from the old-world-builder GitHub repo.
Data is stored as JSON files in the repo, so no browser scraping needed.
Results cached to pipeline/cache/army_data.json.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx

CACHE_FILE = Path("pipeline/cache/army_data.json")

GITHUB_RAW = "https://raw.githubusercontent.com/nthiebes/old-world-builder/main/src/assets"
DATA_FILES = {
    "the-old-world": f"{GITHUB_RAW}/the-old-world.json",
    "lores-of-magic": f"{GITHUB_RAW}/lores-of-magic-with-spells.json",
}


def _unit_to_text(unit: dict, army_name: str) -> str:
    """Convert a unit dict to a readable text description."""
    lines = []
    name = unit.get("name_en") or unit.get("name") or "Unknown Unit"
    lines.append(f"Unit: {name} ({army_name})")

    # Stats profile
    stats_keys = ["move", "weapon_skill", "ballistic_skill", "strength", "toughness",
                  "wounds", "initiative", "attacks", "leadership",
                  "M", "WS", "BS", "S", "T", "W", "I", "A", "Ld"]
    stats = {k: unit[k] for k in stats_keys if k in unit}
    if stats:
        stat_str = " | ".join(f"{k}: {v}" for k, v in stats.items())
        lines.append(f"Stats: {stat_str}")

    # Points
    if "points" in unit:
        lines.append(f"Points: {unit['points']}")
    if "points_per_model" in unit:
        lines.append(f"Points per model: {unit['points_per_model']}")

    # Troop type
    for key in ["type", "troop_type", "unit_type", "category"]:
        if key in unit:
            lines.append(f"Type: {unit[key]}")
            break

    # Special rules
    for key in ["special_rules", "special_rules_en", "rules", "abilities"]:
        val = unit.get(key)
        if val:
            if isinstance(val, list):
                lines.append(f"Special Rules: {', '.join(str(v) for v in val)}")
            elif isinstance(val, str):
                lines.append(f"Special Rules: {val}")
            break

    # Equipment / options
    for key in ["equipment", "options", "magic_items", "weapons"]:
        val = unit.get(key)
        if val:
            if isinstance(val, list):
                lines.append(f"{key.title()}: {', '.join(str(v) for v in val)}")
            elif isinstance(val, str):
                lines.append(f"{key.title()}: {val}")

    # Description
    for key in ["description", "description_en", "lore", "notes"]:
        val = unit.get(key)
        if val and isinstance(val, str):
            lines.append(f"Description: {val}")
            break

    return "\n".join(lines)


def _spell_to_text(spell: dict, lore_name: str) -> str:
    """Convert a spell dict to readable text."""
    lines = []
    name = spell.get("name_en") or spell.get("name") or "Unknown Spell"
    lines.append(f"Spell: {name} (Lore of {lore_name})")

    for key in ["casting_value", "cast", "difficulty"]:
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


def _flatten_json(data: dict | list, parent_key: str = "", army_name: str = "") -> list[dict]:
    """
    Recursively walk the JSON and produce a flat list of text documents.
    Handles unknown JSON shapes gracefully.
    """
    docs = []

    if isinstance(data, list):
        for item in data:
            docs.extend(_flatten_json(item, parent_key, army_name))

    elif isinstance(data, dict):
        # Detect if this looks like a unit
        unit_signals = {"weapon_skill", "WS", "ballistic_skill", "BS", "wounds", "W",
                        "points", "points_per_model", "troop_type", "unit_type"}
        if unit_signals & set(data.keys()):
            army = army_name or data.get("army", parent_key)
            text = _unit_to_text(data, army)
            name = data.get("name_en") or data.get("name") or parent_key
            docs.append({
                "source": "old-world-builder",
                "type": "unit",
                "army": army,
                "title": name,
                "text": text,
            })
        # Detect if this looks like an army container
        elif "units" in data or "troops" in data or "regiments" in data:
            army = data.get("name_en") or data.get("name") or parent_key
            for key in ["units", "troops", "regiments", "characters", "war_machines", "mounts"]:
                if key in data and isinstance(data[key], list):
                    for item in data[key]:
                        docs.extend(_flatten_json(item, key, army))
        # Detect spell
        elif ("casting_value" in data or "cast" in data) and ("effect" in data or "description" in data):
            lore = army_name or parent_key
            text = _spell_to_text(data, lore)
            name = data.get("name_en") or data.get("name") or "Spell"
            docs.append({
                "source": "old-world-builder",
                "type": "spell",
                "army": lore,
                "title": name,
                "text": text,
            })
        # Detect lore container
        elif "spells" in data:
            lore_name = data.get("name_en") or data.get("name") or parent_key
            for spell in data.get("spells", []):
                docs.extend(_flatten_json(spell, lore_name, lore_name))
        # Generic: recurse into values
        else:
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    child_army = army_name or (key if isinstance(value, dict) else "")
                    docs.extend(_flatten_json(value, key, child_army))

    return docs


def fetch_army_data(force: bool = False) -> list[dict]:
    """
    Fetch army data from old-world-builder GitHub repo.
    Returns list of text documents ready for chunking/embedding.
    """
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)

    if CACHE_FILE.exists() and not force:
        print(f"Loading army data from cache ({CACHE_FILE})")
        return json.loads(CACHE_FILE.read_text())

    print("Fetching army data from old-world-builder GitHub...")
    all_docs = []

    with httpx.Client(timeout=60.0, follow_redirects=True) as client:
        for name, url in DATA_FILES.items():
            print(f"  Fetching {name}...")
            try:
                resp = client.get(url)
                resp.raise_for_status()
                data = resp.json()
                docs = _flatten_json(data, parent_key=name)
                print(f"  → {len(docs)} documents extracted from {name}")
                all_docs.extend(docs)
            except Exception as e:
                print(f"  Warning: failed to fetch {name}: {e}")

    CACHE_FILE.write_text(json.dumps(all_docs, indent=2, ensure_ascii=False))
    print(f"Army data: {len(all_docs)} documents → cached to {CACHE_FILE}")
    return all_docs


if __name__ == "__main__":
    docs = fetch_army_data(force=True)
    print(f"Done. Total army docs: {len(docs)}")
    if docs:
        print("Sample:", docs[0]["text"][:300])
