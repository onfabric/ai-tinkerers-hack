# MCP Server

A FastMCP server for the AI Tinkerers project.

## Setup

```bash
cd mcp-server
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Running the Server

### HTTP Transport (for remote access)

```bash
python server.py
```

The server will be available at `http://localhost:8000/mcp`

### Using the FastMCP CLI

```bash
# stdio transport (for local MCP clients)
fastmcp run server.py:mcp

# HTTP transport
fastmcp run server.py:mcp --transport http --port 8000
```

## Available Tools

- **greet**: Greet someone by name
  - Parameters: `name` (string)
  - Returns: A greeting message

## Connecting with a Client

```python
import asyncio
from fastmcp import Client

client = Client("http://localhost:8000/mcp")

async def call_tool(name: str):
    async with client:
        result = await client.call_tool("greet", {"name": name})
        print(result)

asyncio.run(call_tool("World"))
```

