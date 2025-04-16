# Waypoint management tools
import datetime
import json
import sys
from typing import Any, Callable, List, Optional, Union
import meshtastic
import meshtastic.tcp_interface
from meshtastic import Node
from meshtastic import BROADCAST_ADDR

def register_mesh_tools(mcp):
    """Register all mesh-related tools with MCP."""

    @mcp.tool()
    async def get_long_name() -> str:
        """Get the long name of the device.
        """
        iface = meshtastic.tcp_interface.TCPInterface("meshtastic.local")
        try:
            return iface.getLongName()
        finally:
            iface.close()

    @mcp.tool()
    async def get_short_name() -> str:
        """Get the short name of the device.
        """
        iface = meshtastic.tcp_interface.TCPInterface("meshtastic.local")
        try:
            return iface.getShortName()
        finally:
            iface.close()


    @mcp.tool()
    async def get_my_node_info() -> str:
        """Get the information about the current node connected to MCP
        """
        iface = meshtastic.tcp_interface.TCPInterface("meshtastic.local")
        try:
            node_info = iface.getMyNodeInfo()
            return json.dumps(node_info, indent=4)
        finally:
            iface.close()
    
    @mcp.tool()
    async def get_my_user() -> str:
        """Get the information about the current node's user connected to MCP
        """
        iface = meshtastic.tcp_interface.TCPInterface("meshtastic.local")
        try:
            node_info = iface.getMyUser()
            return json.dumps(node_info, indent=4)
        finally:
            iface.close()

    # @mcp.tool()
    # async def get_node(id: str, req_chan: bool, att: int, timeout: int ) -> Node:
    #     """Remote admin functionality returns a node object that can be used to administer that node
    #     Args:
    #         id (str): ID of the node.
    #         req_chan (bool): Request channel.
    #         att (int): Attribute.
    #         timeout (int): Timeout in seconds.
    #     """
    #     iface = meshtastic.tcp_interface.TCPInterface("meshtastic.local")
    #     try:
    #         node = iface.getNode(id,req_chan,att,timeout)
    #         return node
    #     finally:
    #         iface.close()

    @mcp.tool()
    async def get_public_key() -> str:
        """Get My Public Key for remote admin
        """
        iface = meshtastic.tcp_interface.TCPInterface("meshtastic.local")
        try:
            key = iface.getPublicKey()
            return json.dumps(key, indent=4)
        finally:
            iface.close()

    @mcp.tool()
    async def send_alert(text: str, destinationId: int | str = BROADCAST_ADDR, channelIndex: int =0) -> str:
        """Send an alert text to some other node. This is similar to a text message, but carries a higher priority and is capable of generating special notifications on certain clients.
        
        Args:
            text (str): The text to send.
            destinationId (int | str, optional): The destination ID. Defaults to BROADCAST_ADDR.
            channelIndex (int, optional): The channel index. Defaults to 0.
        """
        iface = meshtastic.tcp_interface.TCPInterface("meshtastic.local")
        try:
            packet = iface.sendAlert(text, destinationId, None, channelIndex)
            return json.dumps(packet, indent=4)
        finally:
            iface.close()
    

    @mcp.tool()
    async def send_data(data, destinationId: Union[int, str] = '^all', portNum: int = 256, wantAck: bool = False, wantResponse: bool = False, onResponse: Optional[Callable[[dict], Any]] = None, onResponseAckPermitted: bool = False, channelIndex: int = 0, hopLimit: Optional[int] = None, pkiEncrypted: Optional[bool] = False, publicKey: Optional[bytes] = None, priority: int = 70) -> str:
        """Send a data packet to some other node

        Args:
            data (bytes | protobuf): The data to send, either as an array of bytes or as a protobuf (which will be automatically serialized to bytes).
            destinationId (int | str, optional): Where to send this message (default: BROADCAST_ADDR).
            portNum (int, optional): The application portnum (similar to IP port numbers) of the destination, see portnums.proto for a list.
            wantAck (bool, optional): True if you want the message sent in a reliable manner (with retries and ack/nak provided for delivery). Defaults to False.
            wantResponse (bool, optional): True if you want the service on the other side to send an application layer response. Defaults to False.
            onResponse (Callable[[dict], Any], optional): A closure of the form funct(packet), that will be called when a response packet arrives (or the transaction is NAKed due to non receipt). Defaults to None.
            onResponseAckPermitted (bool, optional): Should the onResponse callback be called for regular ACKs (True) or just data responses & NAKs (False). Defaults to False.
            channelIndex (int, optional): Channel number to use. Defaults to 0.
            hopLimit (int, optional): Hop limit to use. Defaults to None.
            pkiEncrypted (bool, optional): If True, the data will be encrypted using the public key. Defaults to False.
            publicKey (bytes, optional): The public key to use for encryption. Defaults to None.
            priority (int, optional): The priority of the message. Defaults to 70.
        """
        iface = meshtastic.tcp_interface.TCPInterface("meshtastic.local")
        try:
            packet = iface.sendData(
                data,
                destinationId,
                portNum,
                wantAck,
                wantResponse,
                onResponse,
                onResponseAckPermitted,
                channelIndex,
                hopLimit,
                pkiEncrypted,
                publicKey,
                priority
            )
            return packet
        finally:
            iface.close()

    @mcp.tool()
    async def send_heartbeat() -> None:
        """sends a heartbeat to the mesh.
        """
        iface = meshtastic.tcp_interface.TCPInterface("meshtastic.local")
        try:
            iface.sendHeartbeat()
        finally:
            iface.close()

    @mcp.tool()
    async def send_position(latitude: float = 0.0,
    longitude: float = 0.0,
    altitude: int = 0,
    destinationId: Union[int, str] = BROADCAST_ADDR,
    wantAck: bool = False,
    wantResponse: bool = False,
    channelIndex: int = 0)-> str:
        """
        `Send a position packet to the mesh.
        
        Args:
            latitude (float): Latitude of the position.
            longitude (float): Longitude of the position.
            altitude (int): Altitude of the position.
            destinationId (Union[int, str]): The destination ID. Defaults to BROADCAST_ADDR.
            wantAck (bool): True if you want an ACK for this message.
            wantResponse (bool): True if you want a response for this message.
            channelIndex (int): Channel index to use. Defaults to 0.
        """

        iface = meshtastic.tcp_interface.TCPInterface("meshtastic.local")
        try:
            packet = iface.sendPosition(
                latitude,
                longitude,
                altitude,
                destinationId,
                wantAck,
                wantResponse,
                channelIndex
            )
            return json.dumps(packet, indent=4)
        finally:
            iface.close()
    
    @mcp.tool()
    async def send_telemetry(destinationId: Union[int, str] = BROADCAST_ADDR,
    wantResponse: bool = False,
    channelIndex: int = 0,
    telemetryType: str = "device_metrics") -> str:
        """Send telemetry data to the mesh.
        
        Args:
            destinationId (Union[int, str]): The destination ID. Defaults to BROADCAST_ADDR.
            wantResponse (bool): True if you want a response for this message.
            channelIndex (int): Channel index to use. Defaults to 0.
            telemetryType (str): Type of telemetry data to send. Defaults to "device_metrics".
        """
        iface = meshtastic.tcp_interface.TCPInterface("meshtastic.local")
        try:
            packet = iface.sendTelemetry(destinationId, wantResponse, channelIndex, telemetryType)
            return json.dumps(packet, indent=4)
        finally:
            iface.close()

    @mcp.tool()
    async def send_text(text: str, destinationId: Union[int, str] = '^all', wantAck: bool = False, wantResponse: bool = False, onResponse: Optional[Callable[[dict], Any]] = None, channelIndex: int = 0, portNum: int = 1) -> str:
        """Send a text message via the Meshtastic device.
        
        Args:
            text (str): The text to send.
        """
        iface = meshtastic.tcp_interface.TCPInterface("meshtastic.local")
        try:
            packet = iface.sendText(text, destinationId, wantAck, wantResponse, onResponse, channelIndex, portNum)
            return json.dumps(packet, indent=4)
        finally:
            iface.close()

    @mcp.tool()
    async def send_traceroute(dest: Union[int, str], hopLimit: int, channelIndex: int = 0) -> None:
        """Send a traceroute packet to the mesh.
        Args:
            dest (Union[int, str]): The destination ID.
            hopLimit (int): The hop limit.
            channelIndex (int, optional): The channel index. Defaults to 0.
        """
        iface = meshtastic.tcp_interface.TCPInterface("meshtastic.local")
        try:
            iface.sendTraceRoute(dest, hopLimit, channelIndex)
        finally:
            iface.close()
    

    @mcp.tool()
    async def show_info(file=sys.stdout)->str:
        """Prints the device information to the console.
        """
        iface = meshtastic.tcp_interface.TCPInterface("meshtastic.local")
        try:
            info = iface.showInfo(file)
            return json.dumps(info, indent=4)
        finally:
            iface.close()
    
    @mcp.tool()
    async def show_nodes(includeSelf: bool = True, showFields: Optional[List[str]] = None) -> str:
        """Prints the information about all nodes in the mesh to the console.
        
        Args:
            includeSelf (bool): Whether to include the local node in the output. Defaults to True.
            showFields (Optional[List[str]]): List of fields to show. If None, all fields are shown.
        """
        iface = meshtastic.tcp_interface.TCPInterface("meshtastic.local")
        try:
            return iface.showNodes(includeSelf, showFields)
        finally:
            iface.close()

    @mcp.tool()
    async def send_waypoint(
        lat: float,
        lon: float,
        name: str = "",
        expire: str = "2023-10-01T00:00:00",
        description: str = "",
        id: int = 0,
    ) -> str:
        """Create a waypoint on the mesh.

        Args:
            lat (float): Latitude of the waypoint.
            lon (float): Longitude of the waypoint.
            name (str, optional): Name of the waypoint. Defaults to "".
            expire (str, optional): Expiration date in ISO format. Defaults to "2023-10-01T00:00:00".
            description (str, optional): Description of the waypoint. Defaults to "".
            id (int, optional): ID of the waypoint. Defaults to 0.
        """
        iface = meshtastic.tcp_interface.TCPInterface("meshtastic.local")
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
    async def delete_waypoint(id: int,destinationId: Union[int, str] = '^all', wantAck: bool = True, wantResponse: bool = False, channelIndex: int = 0) -> str:
        """Delete a waypoint on the device.

        Args:
            id (int): ID of the waypoint to delete.
        """
        iface = meshtastic.tcp_interface.TCPInterface("meshtastic.local")
        try:
            return iface.deleteWaypoint(id, destinationId, wantAck, wantResponse, channelIndex)
        finally:
            iface.close()
    
    return mcp