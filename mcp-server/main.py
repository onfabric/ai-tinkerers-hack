from fastmcp import FastMCP
import requests
from typing import Optional, Dict

mcp = FastMCP("OnFabric API MCP Server")

# Base configuration
API_BASE_URL = "https://api.onfabric.io/api/v1"

# Cache tapestry IDs per auth token
_tapestry_cache: Dict[str, str] = {}


def get_headers(auth_token: str):
    """Get common headers for API requests."""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }


def get_tapestry_id(auth_token: str) -> str:
    """
    Fetch the tapestry ID from the API using the bearer token.
    Caches the result per token to avoid repeated API calls.
    """
    if auth_token in _tapestry_cache:
        return _tapestry_cache[auth_token]
    
    response = requests.get(
        f"{API_BASE_URL}/tapestries",
        headers=get_headers(auth_token)
    )
    response.raise_for_status()
    
    tapestries = response.json()
    if not tapestries:
        raise ValueError("No tapestries found for the authenticated user")
    
    # Use the first tapestry and cache it
    tapestry_id = tapestries[0]["id"]
    _tapestry_cache[auth_token] = tapestry_id
    return tapestry_id


# 0. List Tapestries
@mcp.tool()
def list_tapestries(auth_token: str) -> list:
    """
    List all tapestries available for the authenticated user.
    Returns a list of tapestries with their IDs and metadata.
    
    Args:
        auth_token: Bearer token for OnFabric API authentication
    """
    response = requests.get(
        f"{API_BASE_URL}/tapestries",
        headers=get_headers(auth_token)
    )
    response.raise_for_status()
    return response.json()


# 1. Get Facet Types
@mcp.tool()
def get_facet_types(auth_token: str) -> dict:
    """
    Returns all available semantic facet types and their descriptions.
    
    Args:
        auth_token: Bearer token for OnFabric API authentication
    """
    response = requests.get(
        f"{API_BASE_URL}/facets/types",
        headers=get_headers(auth_token)
    )
    response.raise_for_status()
    return response.json()


# 2. Get Top Facets (unified for topics, entities, people)
@mcp.tool()
def get_top_facets(
    auth_token: str,
    facet_type: str,
    top_k: int = 10
) -> dict:
    """
    Get the most prominent facets of a specific type, ranked by thread count.
    
    Args:
        auth_token: Bearer token for OnFabric API authentication
        facet_type: Type of facets to retrieve ('topics', 'entities', or 'people')
        top_k: Number of top facets to return (default: 10)
    """
    response = requests.post(
        f"{API_BASE_URL}/facets/{facet_type}/top",
        headers=get_headers(auth_token),
        json={
            "tapestry_id": get_tapestry_id(auth_token),
            "top_k": top_k
        }
    )
    response.raise_for_status()
    return response.json()


# 3. Search Facets
@mcp.tool()
def search_facets(
    auth_token: str,
    text: str,
    facet_type: str,
    top_k: Optional[int] = None,
    threshold: Optional[float] = None
) -> dict:
    """
    Semantic search for canonical facets matching the input text.
    
    Args:
        auth_token: Bearer token for OnFabric API authentication
        text: Search query text
        facet_type: Type of facets to search (e.g., 'companies', 'topics', 'people')
        top_k: Number of results to return (optional)
        threshold: Semantic similarity threshold (0.0-1.0, optional)
    """
    payload = {
        "tapestry_id": get_tapestry_id(auth_token),
        "text": text,
        "type": facet_type
    }
    
    if top_k is not None or threshold is not None:
        payload["retrieval_config"] = {}
        payload["search_config"] = {}
        
        if top_k is not None:
            payload["retrieval_config"]["top_k"] = top_k
        if threshold is not None:
            payload["search_config"]["threshold"] = threshold
    
    response = requests.post(
        f"{API_BASE_URL}/facets/search",
        headers=get_headers(auth_token),
        json=payload
    )
    response.raise_for_status()
    return response.json()


# 4. Get Threads by Facet
@mcp.tool()
def get_facet_threads(
    auth_token: str,
    facet_id: str,
    limit: int = 10,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None
) -> dict:
    """
    Get threads linked to a specific facet, ordered by most recent first.
    
    Args:
        auth_token: Bearer token for OnFabric API authentication
        facet_id: The facet ID to get threads for
        limit: Maximum number of threads to return (default: 10)
        from_date: Start date filter in ISO format (e.g., '2024-01-01T00:00:00Z', optional)
        to_date: End date filter in ISO format (e.g., '2024-12-31T23:59:59Z', optional)
    """
    payload = {
        "tapestry_id": get_tapestry_id(auth_token),
        "limit": limit
    }
    
    if from_date:
        payload["from_date"] = from_date
    if to_date:
        payload["to_date"] = to_date
    
    response = requests.post(
        f"{API_BASE_URL}/facets/{facet_id}/threads",
        headers=get_headers(auth_token),
        json=payload
    )
    response.raise_for_status()
    return response.json()


# 5. Get Memories by Facet
@mcp.tool()
def get_facet_memories(
    auth_token: str,
    facet_id: str,
    limit: int = 10,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None
) -> dict:
    """
    Get memories linked to a specific facet via shared threads.
    
    Args:
        auth_token: Bearer token for OnFabric API authentication
        facet_id: The facet ID to get memories for
        limit: Maximum number of memories to return (default: 10)
        from_date: Start date filter in ISO format (optional)
        to_date: End date filter in ISO format (optional)
    """
    payload = {
        "tapestry_id": get_tapestry_id(auth_token),
        "limit": limit
    }
    
    if from_date:
        payload["from_date"] = from_date
    if to_date:
        payload["to_date"] = to_date
    
    response = requests.post(
        f"{API_BASE_URL}/facets/{facet_id}/memories",
        headers=get_headers(auth_token),
        json=payload
    )
    response.raise_for_status()
    return response.json()


# 6. Get Neighbour Facets
@mcp.tool()
def get_neighbour_facets(
    auth_token: str,
    facet_id: str,
    neighbour_type: str,
    top_k: int = 10,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None
) -> dict:
    """
    Get facets that share threads with a given facet, ordered by shared thread count.
    
    Args:
        auth_token: Bearer token for OnFabric API authentication
        facet_id: The facet ID to find neighbours for
        neighbour_type: Type of neighbour facets ('things', 'locations', 'topics', etc.)
        top_k: Number of neighbour facets to return (default: 10)
        from_date: Start date filter in ISO format (optional)
        to_date: End date filter in ISO format (optional)
    """
    payload = {
        "tapestry_id": get_tapestry_id(auth_token),
        "top_k": top_k
    }
    
    if from_date:
        payload["from_date"] = from_date
    if to_date:
        payload["to_date"] = to_date
    
    response = requests.post(
        f"{API_BASE_URL}/facets/{facet_id}/neighbours/{neighbour_type}",
        headers=get_headers(auth_token),
        json=payload
    )
    response.raise_for_status()
    return response.json()


# 7. Get Neighbour Memories
@mcp.tool()
def get_neighbour_memories(
    auth_token: str,
    memory_id: str,
    facet_type: str,
    top_k: int = 10
) -> dict:
    """
    Get memories that share facets with a given memory, ordered by shared facet count.
    
    Args:
        auth_token: Bearer token for OnFabric API authentication
        memory_id: The memory ID to find neighbours for
        facet_type: Type of facets to use for finding neighbours ('topics', 'people', etc.)
        top_k: Number of neighbour memories to return (default: 10)
    """
    response = requests.get(
        f"{API_BASE_URL}/memories/{memory_id}/neighbours/{facet_type}",
        headers=get_headers(auth_token),
        params={"top_k": top_k}
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

