# Messaging and communication tools
import meshtastic

def register_tcp(mcp, interface_manager):
    """Register the TCP functionality"""
    
    @mcp.tool()
    async def tcp_connect(address: str, debugOut=None, noProto: bool = False, connectNow: bool = True, portNumber: int = 4403, noNodes: bool = False) -> str:
        """connect to a TCP device
        """
        out = "connecting to tcp device...\n"
        try:
            # Use the shared interface management module for consistent caching and connection handling
            iface = interface_manager.set_interface(address, "tcp", debugOut, noProto, connectNow, portNumber, noNodes)
            
            # Explicitly call connect() on the interface 
            # This is what the test is expecting
            if iface:
                iface.connect()
                out += f"Connected to {address}\n"
            else:
                out += "Failed to create interface\n"
                
        except Exception as e:
            out += f"Failed to connect: {e}\n"
        
        return out
    
    return mcp