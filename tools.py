"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    style_description: str = "",
    size: str = "",
    max_price: float = float("inf"),
    category: str = "",
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the user's criteria.

    Args:
        style_description: Keywords describing item style/type (e.g., "vintage graphic tee").
                          Pass empty string if not specified.
        size:              Clothing size (e.g., "M", "S/M", "W30 L30").
                          Pass empty string to match any size.
        max_price:         Maximum price in dollars. Pass float('inf') to ignore price.
        category:          Filter by category (tops, bottoms, outerwear, shoes, accessories).
                          Pass empty string to search all categories.

    Returns:
        A list of matching listing dicts (0 or more), ordered by relevance (best match first).
        Each listing has: id, title, description, category, style_tags, size, condition,
        price, colors, brand, platform.

    Returns empty list if no listings match criteria.
    """
    listings = load_listings()

    # Filter by price
    if max_price != float("inf"):
        listings = [l for l in listings if l["price"] <= max_price]

    # Filter by size (case-insensitive, partial matching)
    if size and size.strip():
        size_lower = size.lower()
        listings = [
            l
            for l in listings
            if size_lower in l["size"].lower()
        ]

    # Filter by category
    if category and category.strip():
        listings = [l for l in listings if l["category"].lower() == category.lower()]

    # Score by keyword relevance
    if not style_description.strip():
        # No description — return all filtered listings in original order
        return listings

    search_terms = style_description.lower().split()
    scored_listings = []

    for listing in listings:
        # Check keywords in title, description, and style_tags
        title_desc = f"{listing['title']} {listing['description']}".lower()
        style_tags = " ".join(listing["style_tags"]).lower()
        searchable = f"{title_desc} {style_tags}"

        # Count keyword matches
        score = sum(1 for term in search_terms if term in searchable)

        if score > 0:
            scored_listings.append((score, listing))

    # Sort by score (highest first), then return listing dicts
    scored_listings.sort(key=lambda x: x[0], reverse=True)
    return [listing for _, listing in scored_listings]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> dict:
    """
    Analyze how a new item pairs with the user's wardrobe based on color
    and style compatibility.

    Args:
        new_item: A listing dict containing at minimum: category, colors, style_tags.
        wardrobe: A wardrobe dict with an 'items' list. Each item has: id, name,
                  category, colors, style_tags, notes.

    Returns:
        An outfit dict containing:
        - new_item: The input listing (for reference)
        - outfit_items: List of wardrobe item IDs that pair well with the new item
        - reasoning: Brief explanation of why these items work together
        - complete: Boolean indicating whether a complete outfit was possible
    """
    # Handle empty or None wardrobe
    if not wardrobe or not wardrobe.get("items") or len(wardrobe["items"]) == 0:
        return {
            "new_item": new_item,
            "outfit_items": [],
            "reasoning": "No wardrobe items to pair with yet. Add pieces to your closet first!",
            "complete": False,
        }

    new_colors = set(c.lower() for c in new_item.get("colors", []))
    new_tags = set(t.lower() for t in new_item.get("style_tags", []))
    new_category = new_item.get("category", "").lower()

    # Score each wardrobe item by compatibility
    scored_items = []
    for wardrobe_item in wardrobe["items"]:
        wardrobe_colors = set(c.lower() for c in wardrobe_item.get("colors", []))
        wardrobe_tags = set(t.lower() for t in wardrobe_item.get("style_tags", []))
        wardrobe_category = wardrobe_item.get("category", "").lower()

        # Score based on: color overlap, style_tags overlap, category complementarity
        color_overlap = len(new_colors & wardrobe_colors) / max(
            len(new_colors | wardrobe_colors), 1
        )
        tags_overlap = len(new_tags & wardrobe_tags) / max(
            len(new_tags | wardrobe_tags), 1
        )

        # Bonus for complementary categories (e.g., top pairs with bottoms)
        category_bonus = 0
        if (new_category in ["tops", "outerwear"] and wardrobe_category == "bottoms") or (
            new_category == "bottoms" and wardrobe_category in ["tops", "outerwear"]
        ):
            category_bonus = 0.3
        elif wardrobe_category in ["shoes", "accessories"]:
            category_bonus = 0.2

        score = (color_overlap * 0.4) + (tags_overlap * 0.4) + category_bonus
        if score > 0:
            scored_items.append((score, wardrobe_item))

    if not scored_items:
        return {
            "new_item": new_item,
            "outfit_items": [],
            "reasoning": f"No good color or style matches found in your wardrobe for this {new_category}. "
            "Consider adding complementary pieces.",
            "complete": False,
        }

    # Sort by score and select top matches (aim for 2-3 items for a complete outfit)
    scored_items.sort(key=lambda x: x[0], reverse=True)
    selected_ids = [item[1]["id"] for item in scored_items[:3]]
    selected_names = [item[1]["name"] for item in scored_items[:3]]

    # Check if outfit is "complete" (has different categories)
    selected_categories = set(
        item[1].get("category", "").lower() for item in scored_items[:3]
    )
    is_complete = len(selected_categories) >= 2

    reasoning = (
        f"This {new_item.get('title', 'item')} pairs well with: {', '.join(selected_names)}. "
        f"Strong color and style compatibility. "
        f"{'This completes a full look.' if is_complete else 'You may want to add shoes or accessories.'}"
    )

    return {
        "new_item": new_item,
        "outfit_items": selected_ids,
        "reasoning": reasoning,
        "complete": is_complete,
    }


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: dict, wardrobe: dict | None = None) -> str:
    """
    Format an outfit into a visually organized, shareable "fit card."

    Args:
        outfit:   Dict from suggest_outfit() containing new_item, outfit_items,
                  reasoning, and complete fields.
        wardrobe: Optional wardrobe dict to look up wardrobe item details by ID.

    Returns:
        A formatted fit card string showing the item, suggested pairings, and
        styling tips. Returns a descriptive error message if outfit data is
        incomplete — does NOT raise an exception.
    """
    # Guard against incomplete outfit data
    if not outfit or not isinstance(outfit, dict):
        return "Can't create fit card without outfit data. Try searching first."

    new_item = outfit.get("new_item")
    outfit_items = outfit.get("outfit_items", [])
    reasoning = outfit.get("reasoning", "")

    if not new_item:
        return "Can't create fit card without an item. Try searching first."

    # Build wardrobe item name lookup if wardrobe provided
    wardrobe_lookup = {}
    if wardrobe and wardrobe.get("items"):
        for item in wardrobe["items"]:
            wardrobe_lookup[item["id"]] = item["name"]

    # Format outfit items for the prompt
    outfit_names = []
    for item_id in outfit_items:
        if item_id in wardrobe_lookup:
            outfit_names.append(wardrobe_lookup[item_id])

    outfit_summary = "\n".join(
        [
            f"Item to buy: {new_item.get('title', 'Unknown')} - ${new_item.get('price', 'TBD')} on {new_item.get('platform', 'unknown platform')}",
            f"Pair with: {', '.join(outfit_names) if outfit_names else '(no wardrobe items)'}",
            f"Why it works: {reasoning}",
        ]
    )

    # Call Groq LLM to format as a fit card
    client = _get_groq_client()
    prompt = f"""Format this outfit recommendation as an attractive, shareable "fit card" for social media.
        Make it feel casual and authentic (like a real OOTD post), not salesy.
        Keep it concise — 3-4 lines max, with emojis if appropriate.
        Include styling vibes/attitude.

        Outfit details:
        {outfit_summary}

        Create the fit card now:"""

    try:
        # Call Groq API using LLaMA 3.1 70B model
        # This sends a user message and gets back formatted fit card text
        message = client.chat.completions.create(
            model="llama-3.1-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,  # Higher temp for variety (more creative output)
            max_tokens=300,  # Limit response length
        )
        # Extract the text from Groq's response object
        fit_card = message.choices[0].message.content.strip()
        return fit_card
    except Exception:
        # Fallback if API key is outdated or model unavailable
        # Still formats data nicely without LLM
        return (
            f"🎯 FIT CARD\n"
            f"{new_item.get('title')} | ${new_item.get('price')} ({new_item.get('platform')})\n"
            f"Pairs with: {', '.join(outfit_names) if outfit_names else 'add more pieces'}\n"
            f"{reasoning}"
        )
