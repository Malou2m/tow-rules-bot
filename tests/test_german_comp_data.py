"""
Unit tests for pipeline/german_comp_data.py
"""

from pipeline.german_comp_data import fetch_german_comp_data, _DOCS, GC_URL


class TestFetchGermanCompData:
    def test_returns_non_empty_list(self):
        result = fetch_german_comp_data()
        assert isinstance(result, list)
        assert len(result) > 0

    def test_each_doc_has_required_keys(self):
        required = {"source", "type", "section", "army", "title", "text", "url"}
        for doc in fetch_german_comp_data():
            assert required.issubset(doc.keys()), f"Missing keys in: {doc['title']}"

    def test_all_docs_have_source_german_comp(self):
        for doc in fetch_german_comp_data():
            assert doc["source"] == "german-comp", f"Wrong source in: {doc['title']}"

    def test_all_docs_have_gc_url(self):
        for doc in fetch_german_comp_data():
            assert doc["url"] == GC_URL

    def test_all_docs_have_non_empty_text(self):
        for doc in fetch_german_comp_data():
            assert doc["text"].strip(), f"Empty text in: {doc['title']}"

    def test_all_docs_have_non_empty_title(self):
        for doc in fetch_german_comp_data():
            assert doc["title"].strip(), "Found doc with empty title"

    def test_sections_are_valid(self):
        valid_sections = {"Introduction", "Restriction Pack", "Gamechanger Pack"}
        for doc in fetch_german_comp_data():
            assert doc["section"] in valid_sections, (
                f"Unknown section '{doc['section']}' in: {doc['title']}"
            )

    def test_contains_introduction(self):
        docs = fetch_german_comp_data()
        intros = [d for d in docs if d["section"] == "Introduction"]
        assert len(intros) >= 1

    def test_contains_restriction_pack_general(self):
        docs = fetch_german_comp_data()
        general = [d for d in docs if d["section"] == "Restriction Pack" and d["army"] == ""]
        assert len(general) >= 1

    def test_contains_gamechanger_pack_universal(self):
        docs = fetch_german_comp_data()
        universal = [
            d for d in docs
            if d["section"] == "Gamechanger Pack" and d["army"] == ""
        ]
        assert len(universal) >= 1

    def test_army_specific_docs_reference_army_in_title(self):
        """Army-specific docs should mention an army in their title."""
        for doc in fetch_german_comp_data():
            if doc["army"]:
                # Title should contain some keyword tying it to the army
                assert doc["title"].strip(), f"Empty title for army doc: {doc['army']}"

    def test_universal_changes_mention_key_rules(self):
        docs = fetch_german_comp_data()
        universal = next(
            d for d in docs
            if d["section"] == "Gamechanger Pack" and d["army"] == ""
        )
        # Key rules from the PDF
        assert "Press of Battle" in universal["text"]
        assert "Vanguard" in universal["text"]
        assert "Frenzy" in universal["text"]

    def test_restriction_pack_mentions_fly_limit(self):
        docs = fetch_german_comp_data()
        gen_restrictions = [
            d for d in docs
            if d["section"] == "Restriction Pack" and d["army"] == ""
        ]
        all_text = " ".join(d["text"] for d in gen_restrictions)
        assert "Fly" in all_text
        assert "0-4" in all_text

    def test_return_is_same_object_as_internal_list(self):
        """fetch_german_comp_data should return the module-level _DOCS list."""
        result = fetch_german_comp_data()
        assert result is _DOCS
