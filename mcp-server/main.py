from fastmcp import FastMCP
from fastmcp.server.dependencies import get_http_headers
import requests
from typing import Optional, Dict, Literal

mcp = FastMCP("Fabric User Data Navigator")

# Base configuration
API_BASE_URL = "https://api.onfabric.io/api/v1"

# Cache tapestry IDs per auth token
_tapestry_cache: Dict[str, str] = {}

# Search mode configurations
SEARCH_MODES = {
    "precise": {"threshold": 0.75, "top_k": 5},
    "explore": {"threshold": 0.5, "top_k": 50}
}


def get_auth_token() -> str:
    """Extract bearer token from incoming MCP request headers."""
    headers = get_http_headers()
    auth_header = headers.get("authorization", "")
    if not auth_header:
        raise ValueError("Missing Authorization header. Please provide a Bearer token.")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]
    return auth_header


def get_api_headers() -> dict:
    """Get headers for Fabric API requests using the token from MCP request."""
    return {
        "Authorization": f"Bearer {get_auth_token()}",
        "Content-Type": "application/json"
    }


def get_tapestry_id() -> str:
    """
    Fetch the tapestry ID from the API using the bearer token from headers.
    Caches the result per token to avoid repeated API calls.
    """
    auth_token = get_auth_token()
    if auth_token in _tapestry_cache:
        return _tapestry_cache[auth_token]
    
    response = requests.get(
        f"{API_BASE_URL}/tapestries",
        headers=get_api_headers()
    )
    response.raise_for_status()
    
    tapestries = response.json()
    if not tapestries:
        raise ValueError("No tapestries found for the authenticated user")
    
    # Use the first tapestry and cache it
    tapestry_id = tapestries[0]["id"]
    _tapestry_cache[auth_token] = tapestry_id
    return tapestry_id


@mcp.tool()
def get_top_facets(
    facet_type: str,
    top_k: int = 10,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None
) -> dict:
    """
    Get the user's most frequently occurring facets of a given type, ranked by how often they appear in the user's interactions.
    
    Use this tool to discover what the user is most interested in or engaged with.
    
    Args:
        facet_type: Type of facets to retrieve. One of:
            - 'topics': General subjects or categories (e.g., fashion, cooking, investing)
            - 'entities': Specific named things like technologies (e.g., iPhone 15, React)
            - 'people': Named individuals (e.g., Elon Musk, Taylor Swift)
            - 'companies': Organizations and brands (e.g., Nike, Google, Prada)
            - 'locations': Geographic places (e.g., Paris, California)
            - 'products': Digital products and apps (e.g., Spotify, TikTok)
            - 'things': Physical objects (e.g., coffee table, sneakers, handbag)
        top_k: Number of top facets to return (default: 10)
        from_date: Optional start date filter in ISO format (e.g., '2024-01-01T00:00:00Z')
        to_date: Optional end date filter in ISO format (e.g., '2024-12-31T23:59:59Z')
    
    Returns:
        List of facets with their IDs, names, and occurrence counts, sorted by frequency.
    """
    payload = {
        "tapestry_id": get_tapestry_id(),
        "top_k": top_k
    }
    
    if from_date:
        payload["from_date"] = from_date
    if to_date:
        payload["to_date"] = to_date
    
    response = requests.post(
        f"{API_BASE_URL}/facets/{facet_type}/top",
        headers=get_api_headers(),
        json=payload
    )
    response.raise_for_status()
    return response.json()


@mcp.tool()
def search_facets(
    query: str,
    facet_type: Optional[str] = None,
    search_mode: Literal["precise", "explore"] = "explore",
    from_date: Optional[str] = None,
    to_date: Optional[str] = None
) -> dict:
    """
    Search for facets semantically related to a query in the user's interaction history.
    
    Use this tool to find specific facets or explore related concepts the user has engaged with.
    
    Args:
        query: The search text to find semantically similar facets
        facet_type: Optional filter by facet type. One of: 'topics', 'entities', 'people', 'companies', 'locations', 'products', 'things'
        search_mode: Controls search precision:
            - 'precise': Find exact or very close matches (returns top 5). 
              Use when looking for a specific thing.
              Example: query='Prada', facet_type='companies' checks if user has interacted with Prada specifically.
            - 'explore': Find semantically related facets (returns top 50). 
              Use for broader discovery.
              Example: query='fashion', facet_type='companies' finds all fashion-related brands the user likes.
        from_date: Optional start date filter in ISO format (e.g., '2024-01-01T00:00:00Z')
        to_date: Optional end date filter in ISO format (e.g., '2024-12-31T23:59:59Z')
    
    Returns:
        List of matching facets with their IDs, names, and similarity scores.
    """
    mode_config = SEARCH_MODES[search_mode]
    
    payload = {
        "tapestry_id": get_tapestry_id(),
        "text": query,
        "retrieval_config": {"top_k": mode_config["top_k"]},
        "search_config": {"threshold": mode_config["threshold"]}
    }
    
    if facet_type:
        payload["type"] = facet_type
    if from_date:
        payload["from_date"] = from_date
    if to_date:
        payload["to_date"] = to_date
    
    response = requests.post(
        f"{API_BASE_URL}/facets/search",
        headers=get_api_headers(),
        json=payload
    )
    response.raise_for_status()
    return response.json()


@mcp.tool()
def get_facet_memories(
    facet_id: str,
    limit: int = 10,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None
) -> dict:
    """
    Get memories (summaries of user interactions) linked to a specific facet.
    
    Use this tool to understand the CONTEXT of why a user is interested in a facet.
    Memories are LLM-generated summaries of interactions that occurred close together in time.
    A memory is linked to a facet if at least one of its underlying interactions contains that facet.
    
    Example use cases:
    - User is interested in 'Prada': memories reveal if they work there, shop there, or just browsed once
    - User has 'cooking' as a top topic: memories show what kind of cooking (recipes, restaurants, equipment)
    
    Args:
        facet_id: The ID of the facet to get memories for (obtained from get_top_facets or search_facets)
        limit: Maximum number of memories to return (default: 10)
        from_date: Optional start date filter in ISO format (e.g., '2024-01-01T00:00:00Z')
        to_date: Optional end date filter in ISO format (e.g., '2024-12-31T23:59:59Z')
    
    Returns:
        List of memories with their summaries and timestamps, showing what the user was doing related to this facet.
    """
    payload = {
        "tapestry_id": get_tapestry_id(),
        "limit": limit
    }
    
    if from_date:
        payload["from_date"] = from_date
    if to_date:
        payload["to_date"] = to_date
    
    response = requests.post(
        f"{API_BASE_URL}/facets/{facet_id}/memories",
        headers=get_api_headers(),
        json=payload
    )
    response.raise_for_status()
    return response.json()


@mcp.tool()
def find_related_facets(
    facet_id: str,
    related_type: str,
    search_mode: Literal["precise", "explore"] = "explore",
    from_date: Optional[str] = None,
    to_date: Optional[str] = None
) -> dict:
    """
    Find facets that frequently co-occur with a given facet in the user's interactions.
    
    Use this tool to discover connections and relationships between concepts in the user's data.
    Facets co-occur when they are extracted from the same interaction.
    
    Example use cases:
    - Find musicians (people) the user likes: first find 'music' topic, then find related 'people' facets
    - Find locations associated with 'work' topic: discover where the user's work-related interactions happen
    - Find brands (companies) related to 'fitness' topic: discover the user's preferred fitness brands
    
    Args:
        facet_id: The ID of the facet to find related facets for
        related_type: Type of related facets to find. One of: 'topics', 'entities', 'people', 'companies', 'locations', 'products', 'things'
        search_mode: Controls how many results to return:
            - 'precise': Returns top 5 most strongly co-occurring facets
            - 'explore': Returns top 50 co-occurring facets for broader discovery
        from_date: Optional start date filter in ISO format (e.g., '2024-01-01T00:00:00Z')
        to_date: Optional end date filter in ISO format (e.g., '2024-12-31T23:59:59Z')
    
    Returns:
        List of related facets with their IDs, names, and co-occurrence counts.
    """
    top_k = 5 if search_mode == "precise" else 50
    
    payload = {
        "tapestry_id": get_tapestry_id(),
        "top_k": top_k
    }
    
    if from_date:
        payload["from_date"] = from_date
    if to_date:
        payload["to_date"] = to_date
    
    response = requests.post(
        f"{API_BASE_URL}/facets/{facet_id}/neighbours/{related_type}",
        headers=get_api_headers(),
        json=payload
    )
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    import sys
    # Check if running in stdio mode (stdin is not a TTY, meaning it's being piped)
    if not sys.stdin.isatty():
        # Running in stdio mode (for MCP clients like Cursor)
        mcp.run()  # Default is stdio transport
    else:
        # Running interactively, use HTTP transport
        mcp.run(transport="http", port=8000)
