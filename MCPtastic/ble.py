# Messaging and communication tools
import meshtastic
from meshtastic.ble_interface import BLEInterface

def register_ble(mcp, interface_manager: meshtastic.mesh_interface.MeshInterface):
    """Register Bluetooth low energy functionality"""
    
    @mcp.tool()
    async def ble_scan() -> str:
        """run a ble scan for devices
        """
        out = "starting BLE scan...\n"
        for x in BLEInterface.scan():
            out += f"Found: name='{x.name}' address='{x.address}'\n"
        return out
    
    @mcp.tool()
    async def ble_connect(address: str) -> str:
        """connect to a BLE device
        """
        out = "connecting to BLE device...\n"
        try:
            # Use the shared interface management module for consistent caching and connection handling
            iface = interface_manager.set_interface(address, "ble")
            iface.connect()
            out += f"Connected to {address}\n"
        except Exception as e:
            out += f"Failed to connect: {e}\n"
        return out
    
    return mcp