from fastmcp import FastMCP

mcp = FastMCP("AI Tinkerers MCP Server")


@mcp.tool
def greet(name: str) -> str:
    """Greet someone by name."""
    return f"Hello, {name}!"


if __name__ == "__main__":
    mcp.run(transport="http", port=8000)

