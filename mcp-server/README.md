# MCP Server

A FastMCP server for the OnFabric API, providing tools to interact with facets, threads, memories, and more.

## Setup

```bash
uv sync
source .venv/bin/activate
```

## Configuration

Copy the example environment file and add your authentication token:

```bash
cp .env.example .env
```

Then edit `.env` and replace `your_token_here` with your actual OnFabric API token. The `.env` file will be automatically loaded when you run the server.

Alternatively, you can set the environment variable directly:

```bash
export ONFABRIC_AUTH_TOKEN="your_token_here"
```

## Running the Server

### HTTP Transport (for remote access)

```bash
uv run main.py
```

The server will be available at `http://localhost:8000/mcp`

### Using the FastMCP CLI

```bash
# stdio transport (for local MCP clients)
fastmcp run main.py:mcp

# HTTP transport
fastmcp run main.py:mcp --transport http --port 8000
```

## Available Tools

### Facet Operations

- **get_facet_types**: Returns all available semantic facet types and their descriptions
  - Parameters: None
  - Returns: Dictionary of facet types

- **get_top_facets**: Get the most prominent facets of a specific type, ranked by thread count
  - Parameters:
    - `facet_type` (string): Type of facets ('topics', 'entities', or 'people')
    - `tapestry_id` (string): The tapestry ID to query
    - `top_k` (int, optional): Number of top facets to return (default: 10)
  - Returns: Dictionary with top facets

- **search_facets**: Semantic search for canonical facets matching the input text
  - Parameters:
    - `tapestry_id` (string): The tapestry ID to search within
    - `text` (string): Search query text
    - `facet_type` (string): Type of facets to search (e.g., 'companies', 'topics', 'people')
    - `top_k` (int, optional): Number of results to return
    - `threshold` (float, optional): Semantic similarity threshold (0.0-1.0)
  - Returns: Dictionary with search results

- **get_facet_threads**: Get threads linked to a specific facet, ordered by most recent first
  - Parameters:
    - `facet_id` (string): The facet ID to get threads for
    - `tapestry_id` (string): The tapestry ID
    - `limit` (int, optional): Maximum number of threads to return (default: 10)
    - `from_date` (string, optional): Start date filter in ISO format (e.g., '2024-01-01T00:00:00Z')
    - `to_date` (string, optional): End date filter in ISO format (e.g., '2024-12-31T23:59:59Z')
  - Returns: Dictionary with threads

- **get_facet_memories**: Get memories linked to a specific facet via shared threads
  - Parameters:
    - `facet_id` (string): The facet ID to get memories for
    - `tapestry_id` (string): The tapestry ID
    - `limit` (int, optional): Maximum number of memories to return (default: 10)
    - `from_date` (string, optional): Start date filter in ISO format
    - `to_date` (string, optional): End date filter in ISO format
  - Returns: Dictionary with memories

- **get_neighbour_facets**: Get facets that share threads with a given facet, ordered by shared thread count
  - Parameters:
    - `facet_id` (string): The facet ID to find neighbours for
    - `neighbour_type` (string): Type of neighbour facets ('things', 'locations', 'topics', etc.)
    - `tapestry_id` (string): The tapestry ID
    - `top_k` (int, optional): Number of neighbour facets to return (default: 10)
    - `from_date` (string, optional): Start date filter in ISO format
    - `to_date` (string, optional): End date filter in ISO format
  - Returns: Dictionary with neighbour facets

### Memory Operations

- **get_neighbour_memories**: Get memories that share facets with a given memory, ordered by shared facet count
  - Parameters:
    - `memory_id` (string): The memory ID to find neighbours for
    - `facet_type` (string): Type of facets to use for finding neighbours ('topics', 'people', etc.)
    - `top_k` (int, optional): Number of neighbour memories to return (default: 10)
  - Returns: Dictionary with neighbour memories

## Using the Client

### Using the Provided Client Script

A client script is available at the root of the project (`mcp-client.py`):

```bash
# Run example usage
python ../mcp-client.py

# Interactive mode
python ../mcp-client.py --interactive

# Custom server URL
MCP_SERVER_URL=http://localhost:8001/mcp python ../mcp-client.py
```

The client script will:
- Automatically load configuration from `.env` file
- Show pretty-printed JSON output
- Handle errors gracefully
- Support both example and interactive modes

### Using the Client Programmatically

```python
import asyncio
from fastmcp import Client

client = Client("http://localhost:8000/mcp")

async def example():
    async with client:
        # Get facet types
        types = await client.call_tool("get_facet_types", {})
        print(types)
        
        # Search for facets
        results = await client.call_tool("search_facets", {
            "tapestry_id": "your_tapestry_id",
            "text": "fashion",
            "facet_type": "companies"
        })
        print(results)

asyncio.run(example())
```
