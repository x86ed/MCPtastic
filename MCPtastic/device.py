# Device information and configuration tools
import json
import meshtastic
import meshtastic.tcp_interface
from meshtastic.util import (
    active_ports_on_supported_devices,
    detect_supported_devices,
    get_unique_vendor_ids,
    findPorts
)

def register_device_tools(mcp):
    """Register all device-related tools with MCP."""
    
    @mcp.tool()
    async def get_info() -> str:
        """Returns information about the connected device."""
        iface = meshtastic.tcp_interface.TCPInterface("meshtastic.local")
        try:
            return iface.showInfo()
        finally:
            iface.close()
    
    @mcp.tool()
    async def set_owner(long: str, short:str) -> None:
        """Set the owner of the device (device name).

        Args:
            long (str): The long name of the owner.
            short (str): The short name of the owner.
        """
        iface = meshtastic.tcp_interface.TCPInterface("meshtastic.local")
        try:
            iface.localNode.setOwner(long, short)
            return "Owner set successfully"
        finally:
            iface.close()
    
    # You can uncomment and add more device-related functions here
    
    return mcp