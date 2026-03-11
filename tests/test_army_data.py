"""
Unit tests for pipeline/army_data.py

Tests cover:
- _army_name: slug-to-display-name conversion
- _list_to_str: list of dicts to comma-separated string
- _unit_to_text: correct field extraction from the real JSON structure
- fetch_army_data: cache hit, HTTP fetch (mocked), HTTP error handling, caching
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pipeline.army_data import (
    _army_name,
    _list_to_str,
    _unit_to_text,
    fetch_army_data,
)


# ── _army_name ────────────────────────────────────────────────────────────────

class TestArmyName:
    def test_converts_slug_to_title_case(self):
        assert _army_name("empire-of-man") == "Empire Of Man"

    def test_single_word(self):
        assert _army_name("skaven") == "Skaven"

    def test_multiple_hyphens(self):
        assert _army_name("tomb-kings-of-khemri") == "Tomb Kings Of Khemri"


# ── _list_to_str ──────────────────────────────────────────────────────────────

class TestListToStr:
    def test_joins_name_en_fields(self):
        items = [{"name_en": "Sword"}, {"name_en": "Shield"}]
        assert _list_to_str(items) == "Sword, Shield"

    def test_skips_items_without_key(self):
        items = [{"name_en": "Sword"}, {"points": 5}, {"name_en": "Shield"}]
        assert _list_to_str(items) == "Sword, Shield"

    def test_empty_list_returns_empty_string(self):
        assert _list_to_str([]) == ""

    def test_custom_key(self):
        items = [{"id": "swords"}, {"id": "shields"}]
        assert _list_to_str(items, key="id") == "swords, shields"


# ── _unit_to_text ──────────────────────────────────────────────────────────────

class TestUnitToText:
    def _make_unit(self, **kwargs):
        base = {
            "name_en": "Swordsmen",
            "id": "swordsmen",
            "points": 6,
            "minimum": 10,
            "maximum": 40,
        }
        base.update(kwargs)
        return base

    def test_includes_name_army_and_category(self):
        unit = self._make_unit()
        text = _unit_to_text(unit, "Empire Of Man", "core")
        assert "Swordsmen" in text
        assert "Empire Of Man" in text
        assert "Core" in text

    def test_includes_points(self):
        unit = self._make_unit(points=11)
        text = _unit_to_text(unit, "Empire Of Man", "special")
        assert "11" in text

    def test_includes_min_max_size(self):
        unit = self._make_unit(minimum=5, maximum=20)
        text = _unit_to_text(unit, "Empire Of Man", "core")
        assert "5" in text
        assert "20" in text

    def test_includes_equipment(self):
        unit = self._make_unit(equipment=[
            {"name_en": "Hand weapon"}, {"name_en": "Shield"}
        ])
        text = _unit_to_text(unit, "Empire Of Man", "core")
        assert "Hand weapon" in text
        assert "Shield" in text

    def test_includes_command(self):
        unit = self._make_unit(command=[
            {"name_en": "Champion", "points": 8},
            {"name_en": "Standard bearer", "points": 6},
        ])
        text = _unit_to_text(unit, "Empire Of Man", "core")
        assert "Champion" in text
        assert "Standard bearer" in text

    def test_includes_options(self):
        unit = self._make_unit(options=[{"name_en": "Full plate armour"}])
        text = _unit_to_text(unit, "Empire Of Man", "special")
        assert "Full plate armour" in text

    def test_includes_magic_allowance(self):
        unit = self._make_unit(magic={"types": ["weapon", "armor"], "maxPoints": 50})
        text = _unit_to_text(unit, "Empire Of Man", "characters")
        assert "weapon" in text
        assert "50" in text

    def test_falls_back_to_id_when_no_name_en(self):
        unit = {"id": "greatswords", "points": 11}
        text = _unit_to_text(unit, "Empire Of Man", "special")
        assert "greatswords" in text

    def test_skips_zero_maximum(self):
        unit = self._make_unit(maximum=0)
        text = _unit_to_text(unit, "Empire Of Man", "core")
        # maximum=0 means unlimited, should not appear
        assert "Max size" not in text


# ── fetch_army_data ────────────────────────────────────────────────────────────

class TestFetchArmyData:
    def _mock_army_response(self):
        return {
            "characters": [
                {"name_en": "General", "id": "general", "points": 90,
                 "equipment": [{"name_en": "Hand weapon"}]}
            ],
            "core": [
                {"name_en": "Swordsmen", "id": "swordsmen", "points": 6,
                 "minimum": 10, "maximum": 40}
            ],
            "special": [],
            "rare": [],
            "mercenaries": [],
        }

    def test_returns_cached_data_when_cache_exists(self, tmp_path, monkeypatch):
        cached = [{"source": "old-world-builder", "type": "unit",
                   "title": "Swordsmen", "army": "Empire Of Man", "text": "Unit: Swordsmen"}]
        cache_file = tmp_path / "army_data.json"
        cache_file.write_text(json.dumps(cached))
        monkeypatch.setattr("pipeline.army_data.CACHE_FILE", cache_file)

        result = fetch_army_data(force=False)
        assert result == cached

    def test_force_bypasses_cache(self, tmp_path, monkeypatch):
        stale = [{"stale": True}]
        cache_file = tmp_path / "army_data.json"
        cache_file.write_text(json.dumps(stale))
        monkeypatch.setattr("pipeline.army_data.CACHE_FILE", cache_file)

        mock_resp = MagicMock()
        mock_resp.json.return_value = self._mock_army_response()
        mock_resp.raise_for_status = MagicMock()
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp

        with patch("pipeline.army_data.httpx.Client", return_value=mock_client):
            result = fetch_army_data(force=True)

        assert result != stale
        assert any("General" in d.get("text", "") or "Swordsmen" in d.get("text", "") for d in result)

    def test_http_error_is_handled_gracefully(self, tmp_path, monkeypatch):
        cache_file = tmp_path / "army_data.json"
        monkeypatch.setattr("pipeline.army_data.CACHE_FILE", cache_file)

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.side_effect = Exception("Network error")

        with patch("pipeline.army_data.httpx.Client", return_value=mock_client):
            result = fetch_army_data(force=True)

        assert result == []

    def test_result_is_written_to_cache(self, tmp_path, monkeypatch):
        cache_file = tmp_path / "army_data.json"
        monkeypatch.setattr("pipeline.army_data.CACHE_FILE", cache_file)

        mock_resp = MagicMock()
        mock_resp.json.return_value = self._mock_army_response()
        mock_resp.raise_for_status = MagicMock()
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp

        with patch("pipeline.army_data.httpx.Client", return_value=mock_client):
            fetch_army_data(force=True)

        assert cache_file.exists()
        saved = json.loads(cache_file.read_text())
        assert isinstance(saved, list)

    def test_each_doc_has_required_keys(self, tmp_path, monkeypatch):
        cache_file = tmp_path / "army_data.json"
        monkeypatch.setattr("pipeline.army_data.CACHE_FILE", cache_file)

        mock_resp = MagicMock()
        mock_resp.json.return_value = self._mock_army_response()
        mock_resp.raise_for_status = MagicMock()
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp

        with patch("pipeline.army_data.httpx.Client", return_value=mock_client):
            result = fetch_army_data(force=True)

        for doc in result:
            assert "source" in doc
            assert "type" in doc
            assert "army" in doc
            assert "title" in doc
            assert "text" in doc
            assert "url" in doc
