from fastmcp import FastMCP, Image
from fastmcp.server.dependencies import get_http_headers
from fastmcp.utilities.types import Image
import requests
import os
from pathlib import Path
from typing import Optional, Dict, Literal
from google import genai
from dotenv import load_dotenv

# Load .env file from the mcp-server directory
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

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


@mcp.tool()
def generate_image(prompt: str) -> Image:
    """
    Generate an image using Google's Gemini 2.5 Flash Image model (Nano Banana) from a text prompt.
    
    Args:
        prompt: Text description of the image to generate
    
    Returns:
        An Image object that will be rendered in MCP clients like Cursor.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Missing GEMINI_API_KEY environment variable. Please set it to use image generation.")
    
    try:
        client = genai.Client(api_key=api_key)
        
        response = client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=[prompt],
        )
        
        # Extract image data from response
        image_data = None
        mime_type = None
        
        for part in response.parts:
            if part.inline_data is not None:
                image_data = part.inline_data.data
                mime_type = part.inline_data.mime_type
                break
        
        if image_data is None:
            raise ValueError("No image data returned from Gemini API. The response may not contain an image.")
        
        # Convert MIME type to format string (e.g., "image/png" -> "png")
        # Handle common MIME types
        format_map = {
            "image/png": "png",
            "image/jpeg": "jpeg",
            "image/jpg": "jpeg",
            "image/gif": "gif",
            "image/webp": "webp"
        }
        image_format = format_map.get(mime_type, "png")  # Default to png if unknown
        
        # Return Image object using FastMCP's Image class
        # This will be automatically converted to MCP ImageContent format
        return Image(data=image_data, format=image_format)
    
    except Exception as e:
        raise ValueError(f"Error generating image with Gemini API: {str(e)}")


@mcp.tool()
def get_instagram_stories_previews(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    limit: int = 20
) -> dict:
    """
    Get Instagram Stories the user has viewed, with their thread IDs and preview information.
    
    Use this tool to discover what Instagram Stories content the user has engaged with.
    Each story includes a thread_id that can be used with get_thread_image to retrieve the actual image.
    
    Args:
        from_date: Optional start date filter in ISO format (e.g., '2024-01-01T00:00:00Z')
        to_date: Optional end date filter in ISO format (e.g., '2024-12-31T23:59:59Z')
        limit: Maximum number of stories to return (default: 20)
    
    Returns:
        List of Instagram Stories threads with their IDs and preview data.
    """
    params = {
        "interaction_type": "instagram_stories",
        "limit": limit
    }
    
    if from_date:
        params["from_date"] = from_date
    if to_date:
        params["to_date"] = to_date
    
    response = requests.get(
        f"{API_BASE_URL}/tapestries/{get_tapestry_id()}/threads",
        headers=get_api_headers(),
        params=params
    )
    response.raise_for_status()
    return response.json()


@mcp.tool()
def get_thread_image(thread_id: str) -> Image:
    """
    Download and return the image associated with a thread.
    
    Use this tool to retrieve the actual image content from a thread (e.g., an Instagram Story).
    First use get_instagram_stories_previews to get thread IDs, then use this tool to fetch the images.
    
    Args:
        thread_id: The ID of the thread to get the image for
    
    Returns:
        The image content that can be displayed by MCP clients.
    """
    # Get the signed URL for the asset
    response = requests.get(
        f"{API_BASE_URL}/threads/{thread_id}/asset",
        headers=get_api_headers()
    )
    response.raise_for_status()
    signed_url = response.json().get("url")
    
    if not signed_url:
        raise ValueError(f"No asset URL found for thread {thread_id}")
    
    # Download the image from the signed URL
    image_response = requests.get(signed_url)
    image_response.raise_for_status()
    
    # Determine format from content-type header
    content_type = image_response.headers.get("content-type", "image/jpeg")
    if "png" in content_type:
        fmt = "png"
    elif "gif" in content_type:
        fmt = "gif"
    elif "webp" in content_type:
        fmt = "webp"
    else:
        fmt = "jpeg"
    
    return Image(data=image_response.content, format=fmt)


if __name__ == "__main__":
    import sys
    # Check if running in stdio mode (stdin is not a TTY, meaning it's being piped)
    if not sys.stdin.isatty():
        # Running in stdio mode (for MCP clients like Cursor)
        mcp.run()  # Default is stdio transport
    else:
        # Running interactively, use HTTP transport
        mcp.run(transport="http", port=8000)
