# Location and position-related tools
import json
import meshtastic
import meshtastic.tcp_interface
from utils import get_location_from_ip

def register_location_tools(mcp):
    """Register all location-related tools with MCP."""
    
    @mcp.tool()
    async def tcp_gps() -> str:
        """Looks up the location of the device via its LAN connection and sets the device's location if none is present."""
        try:
            # First try to get position from Meshtastic device
            iface = meshtastic.tcp_interface.TCPInterface("meshtastic.local")
            my_node_num = iface.myInfo.my_node_num
            position = iface.nodesByNum[my_node_num].get("position")
            
            # If position not available or incomplete from radio, use IP geolocation
            if position.gps_mode != "ENABLED":
                ip_location = await get_location_from_ip()
                return json.dumps(ip_location, indent=4)
            else:
                return json.dumps(position, indent=4)
        except Exception as e:
            # If anything fails, fall back to IP-based location
            ip_location = await get_location_from_ip()
            iface.localNode.localConfig.position.gps_mode = "ENABLED"
            iface.localNode.localConfig.position.fixed_position = True
            iface.localNode.setFixedPosition(ip_location["lat"], ip_location["lon"], ip_location.get("altitude", 0))
            iface.localNode.writeConfig("position")
            return json.dumps(ip_location, indent=4)
        finally:
            if 'iface' in locals():
                iface.close()
    
    @mcp.tool()
    async def set_fixed_position(lat: float, lon: float, alt: float = 0) -> str:
        """Set the fixed position of the device.
        
        Args:
            lat (float): Latitude
            lon (float): Longitude
            alt (float, optional): Altitude. Defaults to 0.
        """
        iface = meshtastic.tcp_interface.TCPInterface("meshtastic.local")
        try:
            iface.localNode.setFixedPosition(lat, lon, alt)
            return "Fixed position set successfully"
        finally:
            iface.close()
    
    return mcp