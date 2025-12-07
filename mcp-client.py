#!/usr/bin/env python3
"""
Fabric User Data Navigator MCP Client

A client script for interacting with the Fabric MCP server to explore user data.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from fastmcp import Client

# Load .env file from the root directory (same directory as this script)
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

# Configuration
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8000/mcp")
AUTH_TOKEN = os.getenv("ONFABRIC_AUTH_TOKEN", "")


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
    """Example usage demonstrating how to navigate user data."""
    if not AUTH_TOKEN:
        print("Error: ONFABRIC_AUTH_TOKEN environment variable is required", file=sys.stderr)
        sys.exit(1)
    
    print(f"Connecting to MCP server at {MCP_SERVER_URL}...\n")
    
    # Pass auth token as header for the MCP server to forward to Fabric API
    client = Client(MCP_SERVER_URL, auth=AUTH_TOKEN)
    
    async with client:
        # Example 1: Discover user's top interests
        print("=" * 60)
        print("Example 1: Discovering user's top topics")
        print("=" * 60)
        top_topics = await call_tool(client, "get_top_facets", {
            "facet_type": "topics",
            "top_k": 5
        })
        if top_topics:
            print_json(top_topics)
        
        print("\n")
        
        # Example 2: Search for fashion-related companies (explore mode)
        print("=" * 60)
        print("Example 2: Finding fashion-related brands (explore mode)")
        print("=" * 60)
        fashion_brands = await call_tool(client, "search_facets", {
            "query": "fashion",
            "facet_type": "companies",
            "search_mode": "explore"
        })
        if fashion_brands:
            print_json(fashion_brands)
        
        print("\n")
        
        # Example 3: Check if user has interacted with a specific brand (precise mode)
        print("=" * 60)
        print("Example 3: Checking for specific brand interaction (precise mode)")
        print("=" * 60)
        specific_brand = await call_tool(client, "search_facets", {
            "query": "Nike",
            "facet_type": "companies",
            "search_mode": "precise"
        })
        if specific_brand:
            print_json(specific_brand)
        
        print("\n")
        
        # Example 4: Get memories for a facet (if we found one)
        if top_topics and isinstance(top_topics, list) and len(top_topics) > 0:
            facet_id = top_topics[0].get("id") or top_topics[0].get("facet_id")
            if facet_id:
                print("=" * 60)
                print(f"Example 4: Getting memories for top topic")
                print("=" * 60)
                memories = await call_tool(client, "get_facet_memories", {
                    "facet_id": facet_id,
                    "limit": 5
                })
                if memories:
                    print_json(memories)
                
                print("\n")
                
                # Example 5: Find related people for the top topic
                print("=" * 60)
                print(f"Example 5: Finding people related to top topic")
                print("=" * 60)
                related_people = await call_tool(client, "find_related_facets", {
                    "facet_id": facet_id,
                    "related_type": "people",
                    "search_mode": "explore"
                })
                if related_people:
                    print_json(related_people)


async def interactive_mode():
    """Interactive mode for exploring the API."""
    if not AUTH_TOKEN:
        print("Error: ONFABRIC_AUTH_TOKEN environment variable is required", file=sys.stderr)
        sys.exit(1)
    
    print(f"Connecting to MCP server at {MCP_SERVER_URL}...\n")
    
    # Pass auth token as header for the MCP server to forward to Fabric API
    client = Client(MCP_SERVER_URL, auth=AUTH_TOKEN)
    
    async with client:
        # Show available tools
        print("Available tools:")
        print("  1. get_top_facets      - Discover most frequent facets by type")
        print("  2. search_facets       - Search facets semantically (precise/explore mode)")
        print("  3. get_facet_memories  - Get context for why user is interested in a facet")
        print("  4. find_related_facets - Find co-occurring facets")
        print("\n")
        
        print("Facet types: topics, entities, people, companies, locations, products, things")
        print("\n")
        
        # Quick demo: get top topics
        print("Fetching top 5 topics...")
        topics = await call_tool(client, "get_top_facets", {
            "facet_type": "topics",
            "top_k": 5
        })
        if topics:
            print_json(topics)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Fabric User Data Navigator MCP Client",
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
  MCP_SERVER_URL        - MCP server URL (default: http://localhost:8000/mcp)
  ONFABRIC_AUTH_TOKEN   - Bearer token for API authentication (required)

Available Tools:
  get_top_facets       - Get most frequent facets by type
  search_facets        - Search facets (precise or explore mode)
  get_facet_memories   - Get memories linked to a facet
  find_related_facets  - Find co-occurring facets
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
