# Messaging and communication tools
import meshtastic
import meshtastic.version

def register_version(mcp):
    """Register the version functionality"""
    
    @mcp.tool()
    async def get_version() -> str:
        """get the version of the meshtastic module
        """
        return meshtastic.version.get_active_version()
    
    return mcp