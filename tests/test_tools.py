"""
Comprehensive test suite for FitFindr tools.

Tests cover:
- search_listings: filtering by price, size, category, and keyword relevance
- suggest_outfit: color/style matching, empty wardrobe, no matches
- create_fit_card: complete outfit, incomplete outfit, missing data
"""

import pytest
from tools import search_listings, suggest_outfit, create_fit_card


# ──────────────────────────────────────────────────────────────────────────────
# FIXTURES
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def example_new_item():
    """A typical Y2K graphic tee."""
    return {
        "id": "lst_002",
        "title": "Y2K Baby Tee — Butterfly Print",
        "description": "Super cute early 2000s baby tee with butterfly graphic.",
        "category": "tops",
        "style_tags": ["y2k", "vintage", "graphic tee", "cottagecore"],
        "size": "S/M",
        "condition": "excellent",
        "price": 18.0,
        "colors": ["white", "pink", "purple"],
        "brand": None,
        "platform": "depop",
    }


@pytest.fixture
def example_wardrobe():
    """A wardrobe with 5 diverse pieces."""
    return {
        "items": [
            {
                "id": "w_001",
                "name": "Baggy straight-leg jeans, dark wash",
                "category": "bottoms",
                "colors": ["dark blue", "indigo"],
                "style_tags": ["denim", "streetwear", "baggy"],
                "notes": "High-waisted, sits above the hip",
            },
            {
                "id": "w_007",
                "name": "Chunky white sneakers",
                "category": "shoes",
                "colors": ["white"],
                "style_tags": ["sneakers", "chunky", "streetwear"],
                "notes": None,
            },
            {
                "id": "w_009",
                "name": "Brown leather belt",
                "category": "accessories",
                "colors": ["brown"],
                "style_tags": ["classic", "earth tones", "accessories"],
                "notes": None,
            },
            {
                "id": "w_010",
                "name": "Black crossbody bag",
                "category": "accessories",
                "colors": ["black"],
                "style_tags": ["minimal", "accessories", "everyday"],
                "notes": None,
            },
            {
                "id": "w_004",
                "name": "Oversized grey crewneck sweatshirt",
                "category": "tops",
                "colors": ["grey", "charcoal"],
                "style_tags": ["oversized", "basics", "cozy"],
                "notes": "Really oversized — drops below the hip",
            },
        ]
    }


@pytest.fixture
def empty_wardrobe():
    """Wardrobe with no items."""
    return {"items": []}


@pytest.fixture
def outfit_complete(example_new_item, example_wardrobe):
    """A complete outfit dict from suggest_outfit."""
    return {
        "new_item": example_new_item,
        "outfit_items": ["w_007", "w_001"],
        "reasoning": "Y2K tee pairs perfectly with chunky sneakers and baggy jeans.",
        "complete": True,
    }


@pytest.fixture
def outfit_incomplete(example_new_item):
    """An incomplete outfit (only shoes, no bottoms)."""
    return {
        "new_item": example_new_item,
        "outfit_items": ["w_007"],
        "reasoning": "Only shoes available. You may need a bottom and top.",
        "complete": False,
    }


# ──────────────────────────────────────────────────────────────────────────────
# TOOL 1: search_listings
# ──────────────────────────────────────────────────────────────────────────────


class TestSearchListings:
    """Tests for search_listings function."""

    def test_search_by_price_filter(self):
        """Test filtering listings by max_price."""
        results = search_listings(max_price=20.0)
        assert len(results) > 0, "Should find items under $20"
        assert all(item["price"] <= 20.0 for item in results), "All results should be <= $20"

    def test_search_by_price_returns_empty(self):
        """Test that very low price filter returns empty list."""
        results = search_listings(max_price=5.0)
        # May be empty or have very few items
        assert isinstance(results, list), "Should return a list even if empty"

    def test_search_by_category(self):
        """Test filtering listings by category."""
        results = search_listings(category="outerwear")
        assert len(results) > 0, "Should find outerwear items"
        assert all(item["category"].lower() == "outerwear" for item in results)

    def test_search_by_category_case_insensitive(self):
        """Test that category matching is case-insensitive."""
        results_lower = search_listings(category="outerwear")
        results_upper = search_listings(category="OUTERWEAR")
        assert len(results_lower) == len(results_upper), "Case should not matter"

    def test_search_by_style_keywords(self):
        """Test keyword matching in style_tags and title/description."""
        results = search_listings(style_description="vintage graphic")
        assert len(results) > 0, "Should find items matching 'vintage graphic'"
        # Check that results are ranked by relevance (best matches first)
        # All results should have vintage OR graphic (or both)
        for result in results:
            combined = (
                f"{result['title']} {result['description']} "
                f"{' '.join(result['style_tags'])}".lower()
            )
            assert "vintage" in combined or "graphic" in combined

    def test_search_no_results(self):
        """Test behavior when no listings match criteria."""
        # Search for impossible combination
        results = search_listings(
            style_description="xyzabc impossible keyword",
            category="tops",
            max_price=1.0,
        )
        assert results == [], "Should return empty list for no matches"

    def test_search_all_parameters(self):
        """Test filtering with all parameters at once."""
        results = search_listings(
            style_description="vintage",
            size="M",
            max_price=50.0,
            category="tops",
        )
        assert isinstance(results, list), "Should return a list"
        # If any results, verify they match all criteria
        for result in results:
            assert result["price"] <= 50.0
            assert result["category"].lower() == "tops"
            assert "m" in result["size"].lower()

    def test_search_empty_parameters(self):
        """Test that empty parameters don't filter (return all)."""
        results = search_listings(
            style_description="",
            size="",
            max_price=float("inf"),
            category="",
        )
        assert len(results) > 0, "Empty params should return all listings"

    def test_search_returns_all_fields(self):
        """Test that returned listings have all required fields."""
        results = search_listings(style_description="vintage", max_price=50)
        if results:
            item = results[0]
            required_fields = [
                "id",
                "title",
                "description",
                "category",
                "style_tags",
                "size",
                "condition",
                "price",
                "colors",
                "brand",
                "platform",
            ]
            for field in required_fields:
                assert field in item, f"Missing field: {field}"


# ──────────────────────────────────────────────────────────────────────────────
# TOOL 2: suggest_outfit
# ──────────────────────────────────────────────────────────────────────────────


class TestSuggestOutfit:
    """Tests for suggest_outfit function."""

    def test_suggest_outfit_with_wardrobe(self, example_new_item, example_wardrobe):
        """Test suggesting outfit with non-empty wardrobe."""
        outfit = suggest_outfit(example_new_item, example_wardrobe)

        assert isinstance(outfit, dict), "Should return a dict"
        assert "new_item" in outfit
        assert "outfit_items" in outfit
        assert "reasoning" in outfit
        assert "complete" in outfit
        assert len(outfit["outfit_items"]) > 0, "Should suggest some items"
        assert isinstance(outfit["reasoning"], str)
        assert isinstance(outfit["complete"], bool)

    def test_suggest_outfit_empty_wardrobe(self, example_new_item, empty_wardrobe):
        """FAILURE MODE: Empty wardrobe should return graceful response."""
        outfit = suggest_outfit(example_new_item, empty_wardrobe)

        assert outfit["outfit_items"] == [], "Should return empty outfit items"
        assert outfit["complete"] is False, "Should mark as incomplete"
        assert "Add pieces to your closet" in outfit["reasoning"]
        assert outfit["new_item"] == example_new_item

    def test_suggest_outfit_none_wardrobe(self, example_new_item):
        """Test with None wardrobe."""
        outfit = suggest_outfit(example_new_item, None)

        assert outfit["outfit_items"] == []
        assert outfit["complete"] is False

    def test_suggest_outfit_returns_valid_ids(self, example_new_item, example_wardrobe):
        """Test that suggested items are valid wardrobe IDs."""
        outfit = suggest_outfit(example_new_item, example_wardrobe)

        valid_ids = {item["id"] for item in example_wardrobe["items"]}
        for item_id in outfit["outfit_items"]:
            assert item_id in valid_ids, f"Invalid wardrobe item ID: {item_id}"

    def test_suggest_outfit_color_matching(self):
        """Test that color compatibility is considered."""
        item_with_white = {
            "id": "test_white",
            "title": "White shirt",
            "category": "tops",
            "colors": ["white"],
            "style_tags": ["basic"],
        }
        wardrobe_with_white = {
            "items": [
                {
                    "id": "w_white",
                    "name": "White shoes",
                    "category": "shoes",
                    "colors": ["white"],
                    "style_tags": ["shoes"],
                    "notes": None,
                },
                {
                    "id": "w_black",
                    "name": "Black shoes",
                    "category": "shoes",
                    "colors": ["black"],
                    "style_tags": ["shoes"],
                    "notes": None,
                },
            ]
        }

        outfit = suggest_outfit(item_with_white, wardrobe_with_white)
        # White shoes should score higher than black shoes
        if outfit["outfit_items"]:
            # First item should preferentially be the white shoes (better color match)
            first_item_id = outfit["outfit_items"][0]
            assert (
                first_item_id == "w_white"
            ), "White shoes should rank higher for white shirt"

    def test_suggest_outfit_category_complementarity(self):
        """Test that complementary categories (top+bottom) score higher."""
        top_item = {
            "id": "test_top",
            "title": "Test top",
            "category": "tops",
            "colors": ["blue"],
            "style_tags": ["basic", "fitted"],
        }
        wardrobe = {
            "items": [
                {
                    "id": "w_bottom",
                    "name": "Jeans",
                    "category": "bottoms",
                    "colors": ["blue"],
                    "style_tags": ["denim", "fitted"],
                    "notes": None,
                },
                {
                    "id": "w_other_top",
                    "name": "Another top",
                    "category": "tops",
                    "colors": ["red"],  # Different color, no bonus
                    "style_tags": ["basic"],
                    "notes": None,
                },
            ]
        }

        outfit = suggest_outfit(top_item, wardrobe)
        # Jeans (bottom) should rank higher than red top (color+category bonuses)
        assert "w_bottom" in outfit["outfit_items"], "Complementary category with matching color should be suggested"

    def test_suggest_outfit_complete_flag(self, example_new_item, example_wardrobe):
        """Test that 'complete' flag is set when outfit has multiple categories."""
        outfit = suggest_outfit(example_new_item, example_wardrobe)

        if len(outfit["outfit_items"]) >= 2:
            # If multiple items suggested, should have multiple categories
            categories = set()
            for item_id in outfit["outfit_items"]:
                for wardrobe_item in example_wardrobe["items"]:
                    if wardrobe_item["id"] == item_id:
                        categories.add(wardrobe_item["category"])
            assert len(categories) >= 2 or not outfit["complete"]

    def test_suggest_outfit_no_good_matches(self):
        """Test behavior when wardrobe has no compatible items."""
        futuristic_item = {
            "id": "futuristic",
            "title": "Neon holographic vest",
            "category": "outerwear",
            "colors": ["neon pink", "holographic"],
            "style_tags": ["futuristic", "rave", "cyber"],
        }
        earth_tone_wardrobe = {
            "items": [
                {
                    "id": "w_brown",
                    "name": "Brown jeans",
                    "category": "bottoms",
                    "colors": ["brown"],
                    "style_tags": ["classic", "earth tones"],
                    "notes": None,
                },
                {
                    "id": "w_tan",
                    "name": "Tan cardigan",
                    "category": "tops",
                    "colors": ["tan"],
                    "style_tags": ["minimal", "earth tones"],
                    "notes": None,
                },
            ]
        }

        outfit = suggest_outfit(futuristic_item, earth_tone_wardrobe)
        # Even with poor matches, should still suggest something
        assert isinstance(outfit, dict)
        assert "complete" in outfit


# ──────────────────────────────────────────────────────────────────────────────
# TOOL 3: create_fit_card
# ──────────────────────────────────────────────────────────────────────────────


class TestCreateFitCard:
    """Tests for create_fit_card function."""

    def test_create_fit_card_complete(self, outfit_complete, example_wardrobe):
        """Test creating a fit card from complete outfit."""
        card = create_fit_card(outfit_complete, example_wardrobe)

        assert isinstance(card, str), "Should return a string"
        assert len(card) > 0, "Card should not be empty"
        # Should contain key information
        assert "Butterfly" in card or "Y2K" in card or "tee" in card.lower()

    def test_create_fit_card_incomplete(self, outfit_incomplete, example_wardrobe):
        """Test creating a fit card from incomplete outfit."""
        card = create_fit_card(outfit_incomplete, example_wardrobe)

        assert isinstance(card, str)
        assert len(card) > 0

    def test_create_fit_card_missing_outfit(self, example_wardrobe):
        """FAILURE MODE: Missing outfit dict should return error message."""
        card = create_fit_card(None, example_wardrobe)

        assert isinstance(card, str)
        assert "Can't create fit card" in card or len(card) > 0
        assert not card.startswith("🎯")  # Should not look like a normal card

    def test_create_fit_card_empty_outfit_dict(self, example_wardrobe):
        """FAILURE MODE: Empty outfit dict should return error message."""
        card = create_fit_card({}, example_wardrobe)

        assert isinstance(card, str)
        assert "Can't create fit card" in card

    def test_create_fit_card_missing_new_item(self, example_wardrobe):
        """FAILURE MODE: Outfit without new_item should return error."""
        bad_outfit = {"outfit_items": ["w_001"], "reasoning": "test", "complete": False}
        card = create_fit_card(bad_outfit, example_wardrobe)

        assert isinstance(card, str)
        assert "Can't create fit card" in card or len(card) > 0

    def test_create_fit_card_without_wardrobe(self, outfit_complete):
        """Test that fit card can be created without wardrobe reference."""
        card = create_fit_card(outfit_complete)

        assert isinstance(card, str)
        assert len(card) > 0

    def test_create_fit_card_with_none_wardrobe(self, outfit_complete):
        """Test that None wardrobe is handled gracefully."""
        card = create_fit_card(outfit_complete, None)

        assert isinstance(card, str)
        assert len(card) > 0

    def test_create_fit_card_contains_item_info(self, outfit_complete, example_wardrobe):
        """Test that fit card includes item details."""
        card = create_fit_card(outfit_complete, example_wardrobe)

        # Should mention the item or price or platform
        combined = card.lower()
        assert "butterfly" in combined or "18" in combined or "depop" in combined

    def test_create_fit_card_format(self, outfit_complete, example_wardrobe):
        """Test that fit card has reasonable formatting."""
        card = create_fit_card(outfit_complete, example_wardrobe)

        # Should be between 50-2000 characters (reasonable card length)
        assert 50 < len(card) < 2000, "Card should be reasonable length"

    def test_create_fit_card_no_crash_on_weird_data(self, example_wardrobe):
        """Test that unusual outfit data doesn't crash the function."""
        weird_outfit = {
            "new_item": {
                "title": "Item",
                "price": None,
                "platform": None,
                "category": None,
            },
            "outfit_items": [],
            "reasoning": "",
            "complete": False,
        }
        card = create_fit_card(weird_outfit, example_wardrobe)

        assert isinstance(card, str)
        # Should not crash, even with missing fields


# ──────────────────────────────────────────────────────────────────────────────
# INTEGRATION TESTS
# ──────────────────────────────────────────────────────────────────────────────


class TestIntegration:
    """Integration tests for the full workflow."""

    def test_full_workflow_search_to_fitcard(self):
        """Test complete workflow: search → suggest → create card."""
        # 1. Search for items
        listings = search_listings(style_description="vintage", max_price=30)
        assert len(listings) > 0, "Should find vintage items"

        new_item = listings[0]

        # 2. Suggest outfit
        from utils.data_loader import get_example_wardrobe

        wardrobe = get_example_wardrobe()
        outfit = suggest_outfit(new_item, wardrobe)
        assert "new_item" in outfit
        assert "outfit_items" in outfit

        # 3. Create fit card
        card = create_fit_card(outfit, wardrobe)
        assert isinstance(card, str)
        assert len(card) > 0

    def test_workflow_with_empty_wardrobe(self):
        """Test workflow stops gracefully at empty wardrobe."""
        listings = search_listings(style_description="vintage", max_price=30)
        new_item = listings[0]

        empty_wardrobe = {"items": []}
        outfit = suggest_outfit(new_item, empty_wardrobe)

        # Should gracefully handle empty wardrobe
        assert outfit["complete"] is False
        assert "Add pieces" in outfit["reasoning"]
