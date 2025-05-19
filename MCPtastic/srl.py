# Messaging and communication tools
import meshtastic

def register_serial(mcp, interface_manager: meshtastic.mesh_interface.MeshInterface):
    """Register the serial functionality"""
    
    @mcp.tool()
    async def serial_connect(path: str, debugOut=None, noProto: bool = False, connectNow: bool = True, noNodes: bool = False) -> str:
        """connect to a TCP device
        """
        out = "connecting to tcp device...\n"
        try:
            # Use the shared interface management module for consistent caching and connection handling
            iface = interface_manager.set_interface(path, "serial", debugOut,noProto,connectNow,4403,noNodes)
            iface.connect()
            out += f"Connected to {path}\n"
        except Exception as e:
            out += f"Failed to connect: {e}\n"
        return out
    
    return mcp