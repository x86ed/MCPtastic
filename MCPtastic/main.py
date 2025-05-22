# Main entry point that initializes MCP and imports all tools
import sys
from mcp.server.fastmcp import FastMCP

# Import all tool functions from modules
from device import register_device_tools
from location import register_location_tools
from mesh import register_mesh_tools
from version import register_version
from ble import register_ble
from tcp import register_tcp
from srl import register_serial
from node import register_node_tools # Import for node tools
from interface_manager import InterfaceManager

# Initialize FastMCP server
mcp = FastMCP("MCPtastic")
interface_manager = InterfaceManager()

# Register all tools with MCP
register_device_tools(mcp, interface_manager)
register_location_tools(mcp, interface_manager)
register_mesh_tools(mcp, interface_manager)
register_ble(mcp, interface_manager)
register_tcp(mcp, interface_manager)
register_serial(mcp, interface_manager)
register_node_tools(mcp, interface_manager) # Register node tools
register_version(mcp)

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')
