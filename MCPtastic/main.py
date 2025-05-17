# Main entry point that initializes MCP and imports all tools
import sys
from mcp.server.fastmcp import FastMCP

# Import all tool functions from modules
from device import register_device_tools
from location import register_location_tools
from mesh import register_mesh_tools
from version import register_version
from ble import register_ble

# Initialize FastMCP server
mcp = FastMCP("MCPtastic")

# Register all tools with MCP
register_device_tools(mcp)
register_location_tools(mcp)
register_mesh_tools(mcp)
register_ble(mcp)
register_version(mcp)

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')
