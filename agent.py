"""
agent.py

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via a session dict.

Complete tools.py and test each tool in isolation before implementing this file.

Usage (once implemented):
    from agent import run_agent
    from utils.data_loader import get_example_wardrobe

    result = run_agent(
        query="vintage graphic tee under $30, size M",
        wardrobe=get_example_wardrobe(),
    )
    print(result["fit_card"])
    print(result["error"])   # None on success
"""

import re
from tools import (
    search_listings,
    search_listings_with_retry,
    suggest_outfit,
    create_fit_card,
    compare_price,
    analyze_trends,
)


# ── query parsing ────────────────────────────────────────────────────────────

def _parse_query(query: str) -> dict:
    """
    Extract style_description, size, max_price, and category from natural language query.

    Returns a dict with keys: style_description, size, max_price, category
    (all may be empty strings if not found).

    Example:
        "vintage graphic tee under $30, size M"
        → {style_description: "vintage graphic tee", size: "M", max_price: 30.0, category: ""}
    """
    parsed = {
        "style_description": "",
        "size": "",
        "max_price": float("inf"),
        "category": "",
    }

    # Extract price (patterns: "under $30", "$30 max", "$30")
    price_match = re.search(r"\$(\d+(?:\.\d{2})?)", query)
    if price_match:
        parsed["max_price"] = float(price_match.group(1))

    # Extract size (patterns: "size M", "size W30 L30", "size S/M")
    size_match = re.search(r"size\s+([A-Za-z0-9\s/]+?)(?:,|$)", query, re.IGNORECASE)
    if size_match:
        parsed["size"] = size_match.group(1).strip()

    # Extract category if explicitly mentioned
    categories = ["tops", "bottoms", "outerwear", "shoes", "accessories"]
    for category in categories:
        if category in query.lower():
            parsed["category"] = category
            break

    # Extract style_description (everything not captured above)
    # Remove price, size, and category patterns to get the description
    description = query.lower()
    description = re.sub(r"\$\d+(?:\.\d{2})?", "", description)
    description = re.sub(r"size\s+[a-z0-9\s/]+", "", description, flags=re.IGNORECASE)
    description = re.sub(r"\b(" + "|".join(categories) + r")\b", "", description)
    # Clean up whitespace and punctuation
    description = re.sub(r"[,\s]+", " ", description).strip()
    parsed["style_description"] = description

    return parsed


# ── session state ─────────────────────────────────────────────────────────────

def _new_session(query: str, wardrobe: dict) -> dict:
    """
    Initialize and return a fresh session dict for one user interaction.

    The session dict is the single source of truth for everything that happens
    during a run — it stores the original query, parsed parameters, tool results,
    and any error that caused early termination.

    You may add fields to this dict as needed for your implementation.
    """
    return {
        "query": query,              # original user query
        "parsed": {},                # extracted description / size / max_price
        "search_results": [],        # list of matching listing dicts
        "selected_item": None,       # top result, passed into suggest_outfit
        "wardrobe": wardrobe,        # user's wardrobe dict
        "outfit_suggestion": None,   # dict returned by suggest_outfit
        "fit_card": None,            # string returned by create_fit_card
        "error": None,               # set if the interaction ended early
        "trends": None,              # STRETCH: trending styles/colors (analyze_trends result)
        "price_comparison": None,    # STRETCH: price assessment (compare_price result)
        "retry_explanation": "",     # STRETCH: what constraints were loosened in search
    }


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Main agent entry point. Runs the FitFindr planning loop for a single
    user interaction and returns the completed session dict.

    Args:
        query:    Natural language user request
                  (e.g., "vintage graphic tee under $30, size M")
        wardrobe: User's wardrobe dict — use get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py

    Returns:
        The session dict after the interaction completes. Check session["error"]
        first — if it is not None, the interaction ended early and the other
        output fields (outfit_suggestion, fit_card) will be None.

    TODO — implement this function using the planning loop you designed in planning.md:

        Step 1: Initialize the session with _new_session().

        Step 2: Parse the user's query to extract a description, size, and
                max_price. You can use regex, string splitting, or ask the LLM
                to parse it — document your choice in planning.md.
                Store the result in session["parsed"].

        Step 3: Call search_listings() with the parsed parameters.
                Store results in session["search_results"].
                If no results: set session["error"] to a helpful message and
                return the session early. Do NOT proceed to suggest_outfit
                with empty input.

        Step 4: Select the item to use (e.g., the top result).
                Store it in session["selected_item"].

        Step 5: Call suggest_outfit() with the selected item and wardrobe.
                Store the result in session["outfit_suggestion"].

        Step 6: Call create_fit_card() with the outfit suggestion and selected item.
                Store the result in session["fit_card"].

        Step 7: Return the session.

    Before writing code, complete the Planning Loop and State Management sections
    of planning.md — your implementation should match what you described there.
    """
    # Step 1: Initialize the session
    session = _new_session(query, wardrobe)

    # Step 2: Parse the user's query to extract parameters
    parsed = _parse_query(query)
    session["parsed"] = parsed

    # STRETCH: Analyze trends early to influence outfit suggestions
    from utils.data_loader import load_listings
    trends = analyze_trends(load_listings())
    session["trends"] = trends

    # Step 3: Call search_listings_with_retry() with parsed parameters (STRETCH: now with retry logic)
    search_result = search_listings_with_retry(
        style_description=parsed["style_description"],
        size=parsed["size"],
        max_price=parsed["max_price"],
        category=parsed["category"],
    )
    search_results = search_result["results"]
    session["search_results"] = search_results
    session["retry_explanation"] = search_result["retry_explanation"]

    # If no results found, set error and return early
    if not search_results:
        session["error"] = (
            "I couldn't find any items matching those criteria. "
            "Try broadening your search (e.g., different style, higher price limit, or different size)."
        )
        return session

    # Step 4: Select the top result
    selected_item = search_results[0]
    session["selected_item"] = selected_item

    # STRETCH: Compare price of selected item
    price_comparison = compare_price(selected_item)
    session["price_comparison"] = price_comparison

    # Step 5: Call suggest_outfit() with selected item, wardrobe, and trends (STRETCH: pass trends)
    outfit_suggestion = suggest_outfit(selected_item, wardrobe, trends)
    session["outfit_suggestion"] = outfit_suggestion

    # Check if wardrobe was empty (outfit_suggestion will have empty outfit_items)
    if not outfit_suggestion["outfit_items"]:
        session["error"] = outfit_suggestion["reasoning"]
        return session

    # Step 6: Call create_fit_card() with outfit and wardrobe
    fit_card = create_fit_card(outfit_suggestion, wardrobe)
    session["fit_card"] = fit_card

    # Step 7: Return the completed session
    return session


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

    print("=== Happy path: graphic tee ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        print(f"Found: {session['selected_item']['title']}")
        print(f"\nOutfit: {session['outfit_suggestion']}")
        print(f"\nFit card: {session['fit_card']}")

    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Error message: {session2['error']}")
