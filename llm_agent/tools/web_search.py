from .base import Tool

# Deliberately fabricated facts: a live answer that contains them proves the
# model grounded on the tool, not on its own memory.
_DEFAULT_RESULTS = {
    "zephyrium": [
        "Zephyrium is a silvery alloy with a melting point of 412 °C "
        "(Journal of Imaginary Metallurgy, 2024).",
    ],
    "veloria": [
        "Aurelia (population 214,000) is the capital and largest city of the Republic of Veloria.",
    ],
}


def web_search_tool(results: dict[str, list[str]] | None = None) -> Tool:
    """Keyword -> canned snippets. A query returns every snippet whose keyword
    appears in it (case-insensitive), deduplicated. Tests inject conflicting
    info by mapping one keyword to contradictory snippets. No match returns
    "No results found." as a normal observation, not an error - an empty
    result set is not an API failure."""
    index = _DEFAULT_RESULTS if results is None else results

    async def web_search(query: str) -> str:
        q = query.lower()
        hits = [s for keyword, snippets in index.items() if keyword in q for s in snippets]
        unique = list(dict.fromkeys(hits))
        if not unique:
            return "No results found."
        return "\n".join(f"[{i}] {snippet}" for i, snippet in enumerate(unique, 1))

    return Tool(
        name="web_search",
        description="Search the web and return a list of result snippets.",
        parameters={
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Search query"}},
            "required": ["query"],
        },
        handler=web_search,
    )


WEB_SEARCH = web_search_tool()
