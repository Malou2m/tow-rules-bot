"""
Unit tests for pipeline/army_data.py

We test:
- _unit_to_text: correct field extraction for known and unknown stat keys
- _spell_to_text: correct spell formatting
- _flatten_json: unit detection, spell detection, army containers, recursion, unknown shapes
- fetch_army_data: cache hit path, HTTP fetch path (httpx mocked), HTTP error handling
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pipeline.army_data import (
    _flatten_json,
    _spell_to_text,
    _unit_to_text,
    fetch_army_data,
)


# ── _unit_to_text ──────────────────────────────────────────────────────────────

class TestUnitToText:
    def test_basic_unit_includes_name_and_army(self):
        unit = {"name_en": "Swordsmen", "WS": 3, "S": 3, "T": 3, "W": 1, "points": 60}
        text = _unit_to_text(unit, "Empire of Man")
        assert "Swordsmen" in text
        assert "Empire of Man" in text

    def test_stats_are_included(self):
        unit = {"name": "Knight", "WS": 4, "BS": 3, "S": 4, "T": 4, "W": 1}
        text = _unit_to_text(unit, "Bretonnia")
        assert "WS" in text
        assert "4" in text

    def test_points_are_included(self):
        unit = {"name_en": "Spearmen", "points": 75, "T": 3}
        text = _unit_to_text(unit, "High Elves")
        assert "75" in text

    def test_special_rules_list_is_joined(self):
        unit = {"name_en": "Chaos Warriors", "special_rules": ["Chaos Armour", "Marching Fire"], "T": 4}
        text = _unit_to_text(unit, "Warriors of Chaos")
        assert "Chaos Armour" in text
        assert "Marching Fire" in text

    def test_special_rules_string_is_included(self):
        unit = {"name_en": "Skeleton", "special_rules_en": "Undead, Shambling", "T": 2}
        text = _unit_to_text(unit, "Tomb Kings")
        assert "Undead" in text

    def test_description_is_included(self):
        unit = {"name_en": "Goblin", "description_en": "Small and sneaky green creatures.", "T": 2}
        text = _unit_to_text(unit, "Orcs")
        assert "sneaky" in text

    def test_unknown_unit_name_falls_back(self):
        unit = {"T": 3, "W": 1}  # no name key
        text = _unit_to_text(unit, "Unknown Army")
        assert "Unknown Unit" in text

    def test_points_per_model_included(self):
        unit = {"name_en": "Clanrats", "points_per_model": 4, "T": 3}
        text = _unit_to_text(unit, "Skaven")
        assert "Points per model" in text
        assert "4" in text


# ── _spell_to_text ─────────────────────────────────────────────────────────────

class TestSpellToText:
    def test_basic_spell(self):
        spell = {"name_en": "Fireball", "casting_value": 7, "effect": "Deals D6 hits S4."}
        text = _spell_to_text(spell, "Fire")
        assert "Fireball" in text
        assert "Lore of Fire" in text
        assert "7" in text
        assert "D6 hits" in text

    def test_spell_with_cast_key(self):
        spell = {"name": "Frostbolt", "cast": 9, "description": "Freezes target."}
        text = _spell_to_text(spell, "Ice")
        assert "Casting Value" in text
        assert "9" in text

    def test_spell_range_and_duration(self):
        spell = {"name_en": "Shield", "range": "Self", "duration": "One turn",
                 "casting_value": 5, "effect": "Ward save 5+."}
        text = _spell_to_text(spell, "Life")
        assert "Range" in text
        assert "Duration" in text

    def test_unknown_spell_name_fallback(self):
        spell = {"casting_value": 6, "effect": "Does something."}
        text = _spell_to_text(spell, "Death")
        assert "Spell" in text


# ── _flatten_json ──────────────────────────────────────────────────────────────

class TestFlattenJson:
    def test_unit_dict_detected_by_ws(self):
        unit = {"name_en": "Halberdier", "WS": 3, "T": 3, "W": 1}
        docs = _flatten_json(unit, army_name="Empire")
        assert len(docs) == 1
        assert docs[0]["type"] == "unit"
        assert "Halberdier" in docs[0]["text"]

    def test_unit_dict_detected_by_points(self):
        unit = {"name_en": "Archer", "points": 8, "BS": 3}
        docs = _flatten_json(unit, army_name="Elves")
        assert len(docs) == 1

    def test_spell_dict_detected(self):
        spell = {"name_en": "Lightning", "casting_value": 7, "effect": "Strikes the target."}
        docs = _flatten_json(spell, army_name="Metal")
        assert len(docs) == 1
        assert docs[0]["type"] == "spell"

    def test_army_container_with_units_list(self):
        army = {
            "name_en": "Empire",
            "units": [
                {"name_en": "Swordsmen", "WS": 3, "T": 3},
                {"name_en": "Spearmen",  "WS": 3, "T": 3},
            ]
        }
        docs = _flatten_json(army)
        assert len(docs) == 2
        titles = [d["title"] for d in docs]
        assert "Swordsmen" in titles
        assert "Spearmen" in titles

    def test_lore_container_with_spells(self):
        lore = {
            "name_en": "Fire",
            "spells": [
                {"name_en": "Fireball", "casting_value": 7, "effect": "D6 hits."},
                {"name_en": "Inferno",  "casting_value": 10, "effect": "Hits all units."},
            ]
        }
        docs = _flatten_json(lore)
        assert len(docs) == 2
        assert all(d["type"] == "spell" for d in docs)

    def test_list_of_armies(self):
        data = [
            {"name_en": "Empire", "units": [{"name_en": "Knight", "WS": 4, "T": 4}]},
            {"name_en": "Dwarfs", "units": [{"name_en": "Warrior", "WS": 4, "T": 4}]},
        ]
        docs = _flatten_json(data)
        assert len(docs) == 2

    def test_empty_dict_returns_empty(self):
        assert _flatten_json({}) == []

    def test_empty_list_returns_empty(self):
        assert _flatten_json([]) == []

    def test_unknown_shape_recurses_without_crash(self):
        data = {"foo": {"bar": {"name_en": "Goblin", "WS": 2, "T": 2}}}
        docs = _flatten_json(data)
        assert len(docs) == 1


# ── fetch_army_data ────────────────────────────────────────────────────────────

class TestFetchArmyData:
    def test_returns_cached_data_when_cache_exists(self, tmp_path, monkeypatch):
        cached = [{"source": "old-world-builder", "type": "unit",
                   "title": "Knight", "army": "Bretonnia", "text": "Unit: Knight"}]
        cache_file = tmp_path / "army_data.json"
        cache_file.write_text(json.dumps(cached))

        monkeypatch.setattr("pipeline.army_data.CACHE_FILE", cache_file)

        result = fetch_army_data(force=False)
        assert result == cached

    def test_force_flag_bypasses_cache(self, tmp_path, monkeypatch):
        # Put stale data in cache
        stale = [{"stale": True}]
        cache_file = tmp_path / "army_data.json"
        cache_file.write_text(json.dumps(stale))

        monkeypatch.setattr("pipeline.army_data.CACHE_FILE", cache_file)

        fresh_data = {
            "name_en": "Skaven",
            "units": [{"name_en": "Clanrat", "WS": 3, "T": 3}]
        }

        with patch("pipeline.army_data.httpx.Client") as mock_client_cls:
            mock_resp = MagicMock()
            mock_resp.json.return_value = fresh_data
            mock_resp.raise_for_status = MagicMock()
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = mock_resp
            mock_client_cls.return_value = mock_client

            result = fetch_army_data(force=True)

        assert result != stale
        assert any("Clanrat" in d.get("text", "") for d in result)

    def test_http_error_is_handled_gracefully(self, tmp_path, monkeypatch):
        cache_file = tmp_path / "army_data.json"
        monkeypatch.setattr("pipeline.army_data.CACHE_FILE", cache_file)

        with patch("pipeline.army_data.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.side_effect = Exception("Network error")
            mock_client_cls.return_value = mock_client

            # Should not raise — errors are caught and warned
            result = fetch_army_data(force=True)

        assert result == []

    def test_result_is_cached_to_file(self, tmp_path, monkeypatch):
        cache_file = tmp_path / "army_data.json"
        monkeypatch.setattr("pipeline.army_data.CACHE_FILE", cache_file)

        fresh_data = {"name_en": "Empire", "units": [{"name_en": "Swordsman", "WS": 3, "T": 3}]}

        with patch("pipeline.army_data.httpx.Client") as mock_client_cls:
            mock_resp = MagicMock()
            mock_resp.json.return_value = fresh_data
            mock_resp.raise_for_status = MagicMock()
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = mock_resp
            mock_client_cls.return_value = mock_client

            fetch_army_data(force=True)

        assert cache_file.exists()
        saved = json.loads(cache_file.read_text())
        assert isinstance(saved, list)
