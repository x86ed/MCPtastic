import datetime
from typing import Any
import httpx
# from torsimany import torsimany
from mcp.server.fastmcp import FastMCP
import json
import sys

import meshtastic
import meshtastic.serial_interface
from meshtastic.util import (
    active_ports_on_supported_devices,
    detect_supported_devices,
    get_unique_vendor_ids,
    findPorts
)

# Initialize FastMCP server
mcp = FastMCP("MCPtastic")

@mcp.tool()
async def get_hardware() -> str:
    """Returns the hardware model of the device.
    """
    iface = meshtastic.serial_interface.SerialInterface()
    result = ""
    try:
        if iface.nodes:
            for n in iface.nodes.values():
                if n["num"] == iface.myInfo.my_node_num:
                    result += n["user"]["hwModel"]
        return result
    finally:
        iface.close()

@mcp.tool()
async def send_text(text: str) -> None:
    """Returns the hardware model of the device.
    
    Args:
        text (str): The text to send.
    """
    iface = meshtastic.serial_interface.SerialInterface()
    iface.sendText(text)
    iface.close()

@mcp.tool()
async def get_info() -> str:
    """Returns the hardware model of the device.
    """
    iface = meshtastic.serial_interface.SerialInterface()
    try:
        # call showInfo() just to ensure values are populated
        info = iface.showInfo()
        return json.dumps(info, indent=4)
    finally:
        iface.close()

@mcp.tool()
async def get_() -> str:
    """Returns the hardware model of the device.
    """
    iface = meshtastic.serial_interface.SerialInterface()
    try:
        # call showInfo() just to ensure values are populated
        nodes = iface.nodes
        return json.dumps(nodes, indent=4)
    finally:
        iface.close()

@mcp.tool()
async def scan_for_devices() -> str:
    """Detect which device we might have.
    """
    result = []
    vids = get_unique_vendor_ids()
    result.append(f"Searching for all devices with these vendor ids {vids}")

    sds = detect_supported_devices()
    if len(sds) > 0:
        result.append("Detected possible devices:")
    for d in sds:
        result.append(f" name:{d.name}{d.version} firmware:{d.for_firmware}")

    ports = active_ports_on_supported_devices(sds)
    result.append(f"ports:{ports}")
    
    return "\n".join(result)

@mcp.tool()
async def set_owner(long: str, short:str) -> str:
    """Set the owner of the device. (device name)

    Args:
        long (str): The long name of the owner.
        short (str): The short name of the owner.
    """
    iface = meshtastic.serial_interface.SerialInterface()
    iface.localNode.setOwner(long, short)
    iface.close()

@mcp.tool()
async def find_ports() -> str:
    """Find all serial ports.

    Returns:
        str: A JSON string of the serial ports.
    """
    result = findPorts()
    return json.dumps(result, indent=4)

@mcp.tool()
async def tcp_gps() -> str:
    """Demonstration of how to look up a radio's location via its LAN connection.
    Before running, connect your machine to the same WiFi network as the radio.
    """
    iface = meshtastic.serial_interface.SerialInterface()
    try:
        radio_hostname = "meshtastic.local"  # Can also be an IP
        iface = meshtastic.tcp_interface.TCPInterface(radio_hostname)
        my_node_num = iface.myInfo.my_node_num
        return iface.nodesByNum[my_node_num]["position"]
    finally:
        iface.close()

@mcp.tool()
async def create_waypoint(
    lat: float,
    lon: float,
    name: str = "",
    expire: str = "2023-10-01T00:00:00",
    description: str = "",
    id: int = 0,
) -> str:
    """Create a waypoint on the device.

    Args:
        lat (float): Latitude of the waypoint.
        lon (float): Longitude of the waypoint.
        alt (float): Altitude of the waypoint.
        name (str, optional): Name of the waypoint. Defaults to "".
        description (str, optional): Description of the waypoint. Defaults to "".
        icon (str, optional): Icon for the waypoint. Defaults to "default".
    """
    iface = meshtastic.serial_interface.SerialInterface()
    try:
        return iface.sendWaypoint(
            waypoint_id=int(id),
            name=name,
            description=description,
            expire=int(datetime.datetime.fromisoformat(expire).timestamp()),
            latitude=lat,
            longitude=lon,
        )
    finally:
        iface.close()

@mcp.tool()
async def delete_waypoint(id: int) -> str:
    """Delete a waypoint on the device.

    Args:
        id (int): ID of the waypoint to delete.
    """
    iface = meshtastic.serial_interface.SerialInterface()
    try:
        return iface.deleteWaypoint(id)
    finally:
        iface.close()


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')