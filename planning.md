# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: search_listings

**What it does:**
Searches through the mock listings dataset to find secondhand fashion items matching the user's criteria. Returns a filtered list of relevant listings ranked by relevance.

**Input parameters:**
- `style_description` (str): Keywords describing the item style/type (e.g., "vintage graphic tee", "oversized flannel"). Pass empty string if not specified.
- `size` (str): Clothing size (e.g., "M", "S/M", "W30 L30"). Pass empty string to match any size.
- `max_price` (float): Maximum price in dollars. Pass `float('inf')` to ignore price.
- `category` (str, optional): Filter by category (tops, bottoms, outerwear, shoes, accessories). Pass empty string to search all categories.

**What it returns:**
A list of listing dictionaries (0 or more), each containing: `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, `platform`. Results are ordered by relevance to the search query.

**What happens if it fails or returns nothing:**
If no listings match, the agent should inform the user: "I couldn't find any items matching those criteria. Try broadening your search (e.g., different style, higher price limit, or different size)." Agent can retry with fewer/different filters.

---

### Tool 2: suggest_outfit

**What it does:**
Analyzes how a new item (from search_listings) would pair with pieces from the user's existing wardrobe. Returns one or more outfit combinations that style the new item with complementary wardrobe pieces based on color and style compatibility.

**Input parameters:**
- `new_item` (dict): A listing dictionary from `search_listings()` containing at minimum: `category`, `colors`, `style_tags`.
- `wardrobe` (dict): The user's wardrobe object with an `items` list. Each wardrobe item has: `id`, `name`, `category`, `colors`, `style_tags`, `notes`.

**What it returns:**
An outfit dictionary containing:
- `new_item`: The input listing (for reference)
- `outfit_items`: List of wardrobe item IDs that pair well with the new item
- `reasoning`: A brief explanation of why these items work together (color/style compatibility)
- `complete`: Boolean indicating whether a complete outfit (top, bottom, shoes/accessories) was possible

**What happens if it fails or returns nothing:**
If wardrobe is empty, return: `{"new_item": new_item, "outfit_items": [], "reasoning": "No wardrobe items to pair with yet. Add pieces to your closet first!", "complete": false}`. If no good pairings exist, return the outfit with empty `outfit_items` and explain the mismatch.

---

### Tool 3: create_fit_card

**What it does:**
Formats an outfit (new item + suggested wardrobe pairings) into a visually organized, human-readable "fit card" that shows the complete styling recommendation to the user.

**Input parameters:**
- `outfit` (dict): Output from `suggest_outfit()` containing `new_item`, `outfit_items`, `reasoning`, and `complete`.
- `wardrobe` (dict, optional): The full wardrobe object needed to look up wardrobe item details by ID.

**What it returns:**
A formatted string presenting:
- The recommended item (name, price, platform link, key details)
- The suggested outfit pieces (with names and how they pair)
- Styling tips (colors that work, style compatibility)
- A call-to-action ("Check it out on [platform]" or "Add to your wishlist")

Example format:
```
🎯 FIT CARD: Vintage Graphic Tee + Your Wardrobe
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
New Item: Y2K Baby Tee — Butterfly Print | $18 (Depop)
Pairs with: Baggy jeans + Chunky white sneakers
Why it works: Retro graphic + streetwear silhouette
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**What happens if it fails or returns nothing:**
If outfit data is incomplete (missing new_item or wardrobe), return a message: "Can't create fit card without both an item and wardrobe pieces. Try searching first, or make sure your wardrobe has items." If `complete` is false, still display the card but note: "(Incomplete outfit — you may need additional pieces)"

---

### Additional Tools (if any)

<!-- Copy the block above for any tools beyond the required three -->

---

## Planning Loop

**How does your agent decide which tool to call next?**

The agent follows a linear three-step flow for each user query:

1. **Parse and call search_listings**: Extract search criteria (style, size, price, category) from the user's query. If criteria are missing, use empty values to broaden the search. Check if any listings were returned. If yes, proceed to step 2. If no, ask the user to refine their search and stop.

2. **Call suggest_outfit**: Pass the most relevant listing from step 1 and the user's wardrobe to `suggest_outfit()`. Check the `complete` field in the response. If the outfit is complete or the wardrobe is non-empty, proceed to step 3. If wardrobe is empty, inform the user and stop here.

3. **Call create_fit_card**: Format the outfit into a presentable card and display it to the user. This is the final step — the agent has finished.

**Decision checkpoints:**
- If search returns nothing → ask user to broaden criteria, stop
- If wardrobe is empty → tell user to add items first, stop
- If outfit is incomplete → still create fit card but flag it, proceed to display
- Success path → all three tools execute in sequence

---

## State Management

**How does information from one tool get passed to the next?**

The agent maintains state in memory during a single session:

- **User context**: The original user query (stored at session start)
- **Search results**: The full list of listings returned by `search_listings()` — the agent selects the most relevant one and passes it to step 2
- **Wardrobe**: Loaded once at the start of a session (either from a saved file or from user input). This same wardrobe object is passed to `suggest_outfit()` and later to `create_fit_card()` for reference
- **Outfit object**: Returned by `suggest_outfit()` and passed directly to `create_fit_card()`

**Data flow:**
```
User Query
    ↓
search_listings(style, size, price, category)
    → Returns: listings[]
    ↓
[Select best result from listings]
    ↓
suggest_outfit(best_listing, wardrobe)
    → Returns: outfit{}
    ↓
create_fit_card(outfit, wardrobe)
    → Returns: formatted card string
    ↓
Display to user
```

All state is ephemeral per session — it's not persisted unless explicitly saved by a user action.

---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | Ask user to try different keywords, higher price limit, different size, or broader category. Offer to search again. |
| suggest_outfit | Wardrobe is empty | Return outfit with empty `outfit_items` and message: "No wardrobe to pair with yet. Add pieces to your closet and try again!" Stop the flow here. |
| create_fit_card | Outfit input is missing or incomplete | Check if outfit has a valid `new_item`. If missing, return error. If complete=false, still display card but add note: "(Incomplete outfit — you may need shoes or accessories)" |
| suggest_outfit | No compatible items in wardrobe | Return outfit with `complete=false` and explain which items didn't match well (color/style mismatch). Still display to user with suggestion to add complementary pieces. |

---

## Architecture

```
                          ┌─────────────────────┐
                          │   User Query        │
                          │ "Vintage tee, <$30" │
                          └──────────┬──────────┘
                                     │
                                     ▼
                    ┌────────────────────────────────┐
                    │   Parse Query → Extract        │
                    │   - Style: "vintage graphic"   │
                    │   - Price: 30.0                │
                    │   - Size: (empty)              │
                    └──────────┬─────────────────────┘
                               │
                               ▼
          ┌────────────────────────────────────────────┐
          │  Tool 1: search_listings()                  │
          │  Returns: listings[] or empty list          │
          └────────────┬─────────────────────┬──────────┘
                       │                     │
              [Listings found]      [No results]
                       │                     │
                       ▼                     ▼
      ┌──────────────────────────┐  ┌─────────────────┐
      │ Load wardrobe (session)  │  │ Ask user to     │
      │                          │  │ refine search   │
      └──────────────┬───────────┘  │ STOP            │
                     │              └─────────────────┘
                     ▼
      ┌──────────────────────────────────────────┐
      │  Tool 2: suggest_outfit()                │
      │  Input: best_listing + wardrobe          │
      │  Returns: outfit{} (complete/incomplete) │
      └──────────────┬───────────────────────────┘
                     │
        ┌────────────┴────────────┐
   [Wardrobe empty]          [Wardrobe exists]
        │                         │
        ▼                         ▼
   Return message          Check outfit.complete
   "Add items first"        (may be partial)
   STOP                          │
                                 ▼
                    ┌────────────────────────────┐
                    │ Tool 3: create_fit_card()  │
                    │ Input: outfit + wardrobe   │
                    │ Returns: formatted card    │
                    └────────────┬───────────────┘
                                 │
                                 ▼
                    ┌────────────────────────────┐
                    │  Display Fit Card to User  │
                    │  (Complete or Incomplete)  │
                    │  DONE                      │
                    └────────────────────────────┘
```

**State in memory throughout session:**
- User's wardrobe (loaded once, reused across tools)
- Current search results (used to pick best listing)
- Outfit object (passed from suggest_outfit → create_fit_card)

---

## AI Tool Plan

**Milestone 3 — Individual tool implementations:**

**Tool 1: search_listings()**
- AI tool: Claude (via Claude Code)
- Input: The "Tool 1" spec from this planning.md (What it does, Input parameters, Return value), plus the structure of listings.json
- Expected output: Python function that takes style_description, size, max_price, category and returns filtered listings matching all non-empty criteria
- Verification: Test the function with 3 queries:
  1. Query for price < $30 to verify price filtering works
  2. Query for specific category (e.g., "outerwear") to verify category filtering
  3. Query with style keywords to verify matching against style_tags

**Tool 2: suggest_outfit()**
- AI tool: Claude (via Claude Code)
- Input: The "Tool 2" spec, the wardrobe schema from planning.md, the structure of wardrobe items
- Expected output: Python function that analyzes color/style compatibility and returns an outfit dict with outfit_items, reasoning, and complete flag
- Verification: Test with:
  1. A new item and non-empty wardrobe → verify it returns a reasonable outfit combination
  2. Empty wardrobe → verify it returns the "no items" response
  3. An item with no color/style matches → verify complete=false and reasoning explains the issue

**Tool 3: create_fit_card()**
- AI tool: Claude (via Claude Code)
- Input: The "Tool 3" spec, example outfit data, formatting requirements
- Expected output: Python function that formats an outfit into a readable, attractive string presentation
- Verification: Test with:
  1. A complete outfit → verify all details are shown nicely
  2. An incomplete outfit (complete=false) → verify the "incomplete" note appears
  3. An empty wardrobe case → verify error message is clear

**Milestone 4 — Planning loop and state management:**

- AI tool: Claude (via Claude Code)
- Input: This entire planning.md, the Architecture diagram, the tool implementations from Milestone 3
- Expected output: Main agent function that orchestrates the three tools in sequence, handles all decision points and error cases as defined in the Planning Loop section
- Verification:
  1. Run the full agent with the example query: "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"
  2. Verify each step executes in order and state flows correctly
  3. Test error path: try with a user that has no wardrobe → verify it stops after step 2
  4. Test with search that returns no results → verify it prompts for refinement

---

## A Complete Interaction (Step by Step)

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1: Search for items**

The agent parses the user query to extract: style type ("vintage graphic tee"), price limit ($30), and any style context mentioned ("baggy jeans, chunky sneakers"). It calls `search_listings(style_description="vintage graphic tee", max_price=30.0, size="", category="tops")`. The function returns 2–3 matching listings. If no results are found, the agent stops and asks: "No items found under $30 in that style. Try a higher price, different style, or different size?"

**Step 2: Suggest outfit pairing**

The agent takes the most relevant listing from Step 1 (say, "Y2K Baby Tee — Butterfly Print" at $18) and calls `suggest_outfit(new_item=listing, wardrobe=user_wardrobe)`. The user's wardrobe already has baggy jeans and chunky white sneakers stored. The function analyzes the white/pink/purple tee against the wardrobe and returns an outfit dict with the tee paired to those items, complete=true, and reasoning about the Y2K aesthetic matching. If the wardrobe were empty, the function would return outfit_items=[] and the agent would stop here with: "Found this tee, but no wardrobe to style it with yet. Add some pieces to your closet first!"

**Step 3: Create and display the fit card**

The agent calls `create_fit_card(outfit=outfit_object, wardrobe=user_wardrobe)` which formats everything into a presentable card showing: the tee (price, platform), the suggested wardrobe pairing (baggy jeans + chunky sneakers), and styling reasoning (why Y2K aesthetic works with oversized silhouettes). The card is printed to the user.

**Final output to user:**

```
🎯 FIT CARD: Y2K Baby Tee + Your Wardrobe
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
New Item: Y2K Baby Tee — Butterfly Print | $18 (Depop)
Pairs with: Baggy straight-leg jeans + Chunky white sneakers
Why it works: Y2K fashion thrives in oversized silhouettes. The white in the 
sneakers echoes the white base of the tee. Pink/purple accents pop against 
the dark denim.
Style match: ✓ Excellent — Streetwear/Y2K
Check it out: [Depop link]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

The user now has a complete styling recommendation with the item, where to buy it, and how to wear it.
