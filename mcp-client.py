#!/usr/bin/env python3
"""
OnFabric API MCP Client

A client script for interacting with the OnFabric API MCP server.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Optional

from fastmcp import Client

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    # Try root directory first, then mcp-server directory
    root_env = Path(__file__).parent / ".env"
    server_env = Path(__file__).parent / "mcp-server" / ".env"
    if root_env.exists():
        load_dotenv(root_env)
    elif server_env.exists():
        load_dotenv(server_env)
except ImportError:
    pass  # python-dotenv is optional

# Configuration
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8000/mcp")


def print_json(data, indent=2):
    """Pretty print JSON data."""
    try:
        print(json.dumps(data, indent=indent, ensure_ascii=False))
    except (TypeError, ValueError) as e:
        # Fallback if data is not JSON serializable
        print(f"Warning: Could not serialize as JSON: {e}")
        print(f"Data type: {type(data)}")
        print(f"Data: {data}")


async def call_tool(client: Client, tool_name: str, params: dict):
    """Call a tool and handle errors gracefully."""
    try:
        result = await client.call_tool(tool_name, params)
        # Extract content from CallToolResult object
        # FastMCP returns CallToolResult which has a content attribute
        if hasattr(result, 'content'):
            content = result.content
            # Content is usually a list of content blocks
            if isinstance(content, list) and len(content) > 0:
                # Get the first content item
                first_item = content[0]
                # If it has text attribute, parse it as JSON
                if hasattr(first_item, 'text'):
                    try:
                        return json.loads(first_item.text)
                    except (json.JSONDecodeError, TypeError):
                        return first_item.text
                # If it's already a dict, return it
                if isinstance(first_item, dict):
                    return first_item
                return first_item
            # If content is directly a dict or other type
            if isinstance(content, dict):
                return content
            return content
        # If result is already a dict (shouldn't happen but be safe)
        if isinstance(result, dict):
            return result
        # Try to convert to dict if possible
        if hasattr(result, '__dict__'):
            return result.__dict__
        return result
    except Exception as e:
        print(f"Error calling {tool_name}: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return None


async def example_usage():
    """Example usage of the OnFabric API MCP client."""
    print(f"Connecting to MCP server at {MCP_SERVER_URL}...\n")
    
    client = Client(MCP_SERVER_URL)
    
    async with client:
        # Example 1: Get facet types
        print("=" * 60)
        print("Example 1: Getting facet types")
        print("=" * 60)
        types = await call_tool(client, "get_facet_types", {})
        if types:
            print_json(types)
        
        print("\n")
        
        # Example 2: Get top facets (topics)
        print("=" * 60)
        print("Example 2: Getting top topics (requires tapestry_id)")
        print("=" * 60)
        tapestry_id = os.getenv("TAPESTRY_ID")
        if tapestry_id:
            top_facets = await call_tool(client, "get_top_facets", {
                "facet_type": "topics",
                "tapestry_id": tapestry_id,
                "top_k": 5
            })
            if top_facets:
                print_json(top_facets)
        else:
            print("Skipped: Set TAPESTRY_ID environment variable to run this example")
        
        print("\n")
        
        # Example 3: Search facets
        print("=" * 60)
        print("Example 3: Searching for facets")
        print("=" * 60)
        tapestry_id = os.getenv("TAPESTRY_ID")
        if tapestry_id:
            search_results = await call_tool(client, "search_facets", {
                "tapestry_id": tapestry_id,
                "text": "fashion",
                "facet_type": "companies",
                "top_k": 5
            })
            if search_results:
                print_json(search_results)
        else:
            print("Skipped: Set TAPESTRY_ID environment variable to run this example")


async def interactive_mode():
    """Interactive mode for exploring the API."""
    print(f"Connecting to MCP server at {MCP_SERVER_URL}...\n")
    
    client = Client(MCP_SERVER_URL)
    
    async with client:
        # Get available tools
        print("Available tools:")
        print("  1. get_facet_types")
        print("  2. get_top_facets")
        print("  3. search_facets")
        print("  4. get_facet_threads")
        print("  5. get_facet_memories")
        print("  6. get_neighbour_facets")
        print("  7. get_neighbour_memories")
        print("\n")
        
        # Simple example: get facet types
        print("Fetching facet types...")
        types = await call_tool(client, "get_facet_types", {})
        if types:
            print_json(types)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="OnFabric API MCP Client",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run example usage
  python mcp-client.py

  # Interactive mode
  python mcp-client.py --interactive

  # Custom server URL
  MCP_SERVER_URL=http://localhost:8001/mcp python mcp-client.py

Environment Variables:
  MCP_SERVER_URL    - MCP server URL (default: http://localhost:8000/mcp)
  TAPESTRY_ID       - Default tapestry ID for examples
        """
    )
    
    parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Run in interactive mode"
    )
    
    parser.add_argument(
        "--server-url",
        default=None,
        help="MCP server URL (overrides MCP_SERVER_URL env var)"
    )
    
    args = parser.parse_args()
    
    # Override server URL if provided
    global MCP_SERVER_URL
    if args.server_url:
        MCP_SERVER_URL = args.server_url
    
    try:
        if args.interactive:
            asyncio.run(interactive_mode())
        else:
            asyncio.run(example_usage())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()