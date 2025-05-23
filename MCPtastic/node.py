import json
import sys
import os
import asyncio
from typing import Optional
import meshtastic
from meshtastic.node import Node
from meshtastic.util import MessageToJson
from meshtastic.protobuf.config_pb2 import Config

# Add the parent directory to the Python path for local imports
# This is necessary for local imports when running this file directly
if __name__ == "__main__" and __package__ is None:
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from MCPtastic.interface_manager import InterfaceManager


# Helper function to get node object
async def _get_node_object(iface_manager: InterfaceManager, nodeId: str) -> Optional[Node]:
    """Helper function to get the node object, either local or remote."""
    iface = iface_manager.get_interface()
    if not iface:
        # Attempt to set a default interface if none is active
        # This might need adjustment based on how MCPtastic handles default interfaces
        print("No active interface. Attempting to connect to default TCP interface.")
        try:
            iface = await asyncio.to_thread(iface_manager.set_interface, "meshtastic.local", "tcp")
            if not iface:
                raise Exception("Failed to connect to a Meshtastic interface.")
        except Exception as e:
            raise Exception(f"Failed to connect to a Meshtastic interface: {str(e)}")

    if nodeId == "local":
        return iface.localNode
    else:
        # For remote nodes, check if nodes attribute exists and has the requested node
        if hasattr(iface, 'nodes') and iface.nodes:
            return iface.nodes.get(nodeId)
        # Try alternative properties on different meshtastic library versions
        if hasattr(iface, 'nodesByNum') and iface.nodesByNum:
            return iface.nodesByNum.get(nodeId)
        if hasattr(iface, 'getNode'):
            try:
                return iface.getNode(nodeId)
            except Exception:
                pass
        return None


def register_node_tools(mcp, iface_manager: InterfaceManager) -> None:
    """Registers the node tools with the MCP."""

    @mcp.tool()
    async def show_channels(nodeId: str = "local") -> str:
        """Retrieves and displays the channel information for the specified node.

        Args:
            nodeId (str): The node ID (e.g., '!b827ebe5a670') or 'local' for the local node. Defaults to "local".
        
        Returns:
            str: JSON string containing channel information or an error message.
        """
        try:
            node = await _get_node_object(iface_manager, nodeId)
            if not node:
                return json.dumps({"status": "error", "message": f"Node {nodeId} not found or interface not available."})

            channels_info = []
            if hasattr(node, 'channels') and node.channels: # localNode stores channels in .channels
                for ch_settings in node.channels:
                    channels_info.append(MessageToJson(ch_settings))
            elif hasattr(node, 'settings') and hasattr(node.settings, 'channel_settings') and node.settings.channel_settings: # remote nodes store in .settings.channel_settings
                for ch_settings in node.settings.channel_settings:
                    channels_info.append(MessageToJson(ch_settings))
            elif hasattr(node, 'localConfig') and hasattr(node.localConfig, 'channel_settings') and node.localConfig.channel_settings: # some local node versions
                for ch_settings in node.localConfig.channel_settings:
                    channels_info.append(MessageToJson(ch_settings))
            else: # Try remote call if local attributes are not found or empty
                if hasattr(node, 'showChannels'):
                    remote_channels = await asyncio.to_thread(node.showChannels)
                    if remote_channels: # showChannels already returns a dict/list of dicts
                        return json.dumps({"status": "success", "nodeId": nodeId, "channels": remote_channels}, indent=4)
                    else:
                        return json.dumps({"status": "error", "nodeId": nodeId, "message": "No channel data found for node or method not directly available for remote nodes in this manner."})
                else:
                    return json.dumps({"status": "error", "nodeId": nodeId, "message": "No channel data found for node and no showChannels method available."})
            
            return json.dumps({"status": "success", "nodeId": nodeId, "channels": channels_info}, indent=4)
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, indent=4)

    @mcp.tool()
    async def show_info(nodeId: str = "local") -> str:
        """Retrieves and displays preferences, module preferences, and channel information for the specified node.

        Args:
            nodeId (str): The node ID (e.g., '!b827ebe5a670') or 'local' for the local node. Defaults to "local".

        Returns:
            str: JSON string containing node information or an error message.
        """
        try:
            node = await _get_node_object(iface_manager, nodeId)
            if not node:
                return json.dumps({"status": "error", "message": f"Node {nodeId} not found or interface not available."})

            # The showInfo method in meshtastic-python typically prints to console.
            # We want to capture this data. It often returns a dictionary or can be made to.
            # For localNode, info is often available as attributes.
            # For remote nodes, it might involve requesting config.
            
            info_data = {}
            if nodeId == "local":
                iface = iface_manager.get_interface()
                # For local node, gather info from various properties
                if hasattr(iface, 'myInfo'):
                    info_data["myNodeInfo"] = iface.myInfo
                if hasattr(iface, 'localNode') and hasattr(iface.localNode, 'localConfig'):
                    info_data["localConfig"] = MessageToJson(iface.localNode.localConfig)
                if hasattr(iface, 'localNode') and hasattr(iface.localNode, 'moduleConfig'):
                    info_data["moduleConfig"] = MessageToJson(iface.localNode.moduleConfig)
                if hasattr(iface, 'localNode') and hasattr(iface.localNode, 'channels'):
                    info_data["channels"] = [MessageToJson(ch) for ch in iface.localNode.channels]
            else:
                # For remote nodes, get available properties
                if hasattr(node, 'localConfig') and node.localConfig:
                    info_data["localConfig"] = MessageToJson(node.localConfig)
                if hasattr(node, 'moduleConfig') and node.moduleConfig:
                    info_data["moduleConfig"] = MessageToJson(node.moduleConfig)
                if hasattr(node, 'role') and node.role: #This is not standard, but some custom versions might have it
                    info_data["role"] = Config.DeviceConfig.Role.Name(node.role)

                # Fallback: try to get common useful info
                if not info_data or len(info_data) == 0:
                    # Add basic node properties safely
                    for attr in ['nodeId', 'longName', 'shortName', 'hwModel']:
                        if hasattr(node, attr):
                            info_data[attr] = getattr(node, attr)
                    
                    # Boolean properties
                    for bool_attr in ['isRouter', 'isMqttEnabled']:
                        if hasattr(node, bool_attr):
                            info_data[bool_attr] = getattr(node, bool_attr)
                    
                    # Handle channels if available
                    if hasattr(node, 'channels') and node.channels:
                        channels_info = [MessageToJson(ch) for ch in node.channels]
                        info_data["channels"] = channels_info
                    elif hasattr(node, 'settings') and hasattr(node.settings, 'channel_settings'):
                        channels_info = [MessageToJson(ch) for ch in node.settings.channel_settings]
                        info_data["channels"] = channels_info

            if not info_data or len(info_data) == 0:
                # Return basic node info if we couldn't get detailed info
                basic_info = {
                    "nodeID": getattr(node, 'nodeId', 'unknown'),
                    "longName": getattr(node, 'longName', 'unknown'),
                    "shortName": getattr(node, 'shortName', 'unknown'),
                    "hwModel": getattr(node, 'hwModel', 'unknown')
                }
                return json.dumps({
                    "status": "success", 
                    "nodeId": nodeId, 
                    "message": "Basic info retrieved. For full remote node details, specific config requests might be needed.", 
                    "data": basic_info
                }, indent=4)

            return json.dumps({"status": "success", "nodeId": nodeId, "info": info_data}, indent=4)

        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, indent=4)

    @mcp.tool()
    async def set_owner(long_name: Optional[str] = None, short_name: Optional[str] = None, is_licensed: bool = False, nodeId: str = "local") -> str:
        """Sets the owner information for the specified node.

        Args:
            long_name (Optional[str]): The long name of the owner. Defaults to None (no change).
            short_name (Optional[str]): The short name of the owner. Defaults to None (no change).
            is_licensed (bool): Whether the user is licensed. Defaults to False.
            nodeId (str): The node ID or 'local'. Defaults to "local".
        
        Returns:
            str: JSON string with operation status.
        """
        try:
            node = await _get_node_object(iface_manager, nodeId)
            if not node:
                return json.dumps({"status": "error", "message": f"Node {nodeId} not found."})

            iface = iface_manager.get_interface()
            if not iface:
                return json.dumps({"status": "error", "message": "Interface not available."})
            
            current_long_name = None
            current_short_name = None

            if nodeId == "local":
                if hasattr(iface, 'getLongName'):
                    current_long_name = iface.getLongName()
                if hasattr(iface, 'getShortName'):
                    current_short_name = iface.getShortName()
            elif hasattr(node, 'user') and node.user:
                current_long_name = getattr(node.user, 'long_name', None)
                current_short_name = getattr(node.user, 'short_name', None)
            
            # Use current names if new names are not provided
            final_long_name = long_name if long_name is not None else current_long_name
            final_short_name = short_name if short_name is not None else current_short_name

            # Ensure names are not None if they couldn't be fetched and weren't provided
            if final_long_name is None:
                final_long_name = "Meshtastic" # Default if not set
            if final_short_name is None:
                final_short_name = "Mesh"    # Default if not set

            if nodeId == "local":
                if hasattr(iface, 'setOwner'):
                    await asyncio.to_thread(iface.setOwner, final_long_name, final_short_name, is_licensed)
                else:
                    return json.dumps({"status": "error", "message": "Interface does not have setOwner method."})
            else:
                if hasattr(node, 'setOwner'):
                    await asyncio.to_thread(node.setOwner, final_long_name, final_short_name, is_licensed)
                else:
                    return json.dumps({"status": "error", "message": "Node does not have setOwner method."})
            
            return json.dumps({"status": "success", "nodeId": nodeId, "message": f"Owner set to Long: {final_long_name}, Short: {final_short_name}, Licensed: {is_licensed}"}, indent=4)
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, indent=4)

    @mcp.tool()
    async def get_url(nodeId: str = "local", includeAll: bool = True) -> str:
        """Gets the sharable URL for the node's primary channel or all channels.

        Args:
            nodeId (str): The node ID or 'local'. Defaults to "local".
            includeAll (bool): If true, include all channels (typically results in QR code for web UI). If false, primary channel URL. Defaults to True.

        Returns:
            str: JSON string with the URL(s) or an error message.
        """
        try:
            node = await _get_node_object(iface_manager, nodeId)
            if not node:
                return json.dumps({"status": "error", "message": f"Node {nodeId} not found."})

            iface = iface_manager.get_interface()
            if not iface:
                return json.dumps({"status": "error", "message": "Interface not available."})

            if nodeId == "local":
                if includeAll:
                    if hasattr(iface, 'getQRCodeURL'):
                        url = await asyncio.to_thread(iface.getQRCodeURL)
                        return json.dumps({"status": "success", "nodeId": "local", "type": "all_channels_qr_code_url", "url": url}, indent=4)
                    else:
                        return json.dumps({"status": "error", "message": "Interface does not have getQRCodeURL method."})
                else:
                    if hasattr(iface, 'getURL'):
                        url = await asyncio.to_thread(iface.getURL, 0)  # Assuming primary channel is index 0
                        return json.dumps({"status": "success", "nodeId": "local", "type": "primary_channel_url", "url": url}, indent=4)
                    else:
                        return json.dumps({"status": "error", "message": "Interface does not have getURL method."})
            else:
                # For remote nodes, collect and return channel settings
                channels_data = []
                if hasattr(node, 'settings') and hasattr(node.settings, 'channel_settings'):
                    for i, ch_setting in enumerate(node.settings.channel_settings):
                        ch_info = {
                            "index": i,
                            "name": getattr(ch_setting, 'name', 'unknown'),
                            "role": Config.ChannelConfig.Role.Name(ch_setting.role) 
                                if hasattr(ch_setting, "role") and hasattr(Config.ChannelConfig.Role, 'Name') 
                                else "PRIMARY",
                            "psk_hint": "PSK required to form URL, not shown for security."
                        }
                        channels_data.append(ch_info)

                if channels_data:
                    return json.dumps({"status": "success", "nodeId": nodeId, "message": "Channel data for URL construction. Manual URL creation may be needed for remote nodes.", "channels": channels_data}, indent=4)
                else:
                    return json.dumps({"status": "info", "nodeId": nodeId, "message": "Cannot directly get URL for remote node without channel data. Try 'show_channels' first."}, indent=4)

        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, indent=4)

    @mcp.tool()
    async def set_url(url: str, addOnly: bool = False, nodeId: str = "local") -> str:
        """Sets the mesh network URL from the provided string.
        This will configure the primary channel based on the URL.
        For broader changes (adding multiple channels from a URL), the behavior depends on the library's interpretation.

        Args:
            url (str): The Meshtastic channel URL (e.g., "https://www.meshtastic.org/c/#ChV...");
            addOnly (bool): If true, only add new channels from the URL, don't modify existing matching channels. Not standard, behavior depends on library. Defaults to False.
            nodeId (str): The node ID or 'local'. Defaults to "local".
        
        Returns:
            str: JSON string with operation status.
        """
        try:
            if nodeId != "local":
                return json.dumps({"status": "error", "message": f"setURL for remote node '{nodeId}' is not directly supported by this tool yet. Use on local node."})

            iface = iface_manager.get_interface()
            if not iface:
                return json.dumps({"status": "error", "message": "Interface not available."})
            
            if addOnly:
                print(f"Note: 'addOnly' parameter for setURL is not a standard feature of meshtastic.py; URL will likely set the primary channel or be handled as per library default.")

            if hasattr(iface, 'setURL'):
                await asyncio.to_thread(iface.setURL, url)
                return json.dumps({"status": "success", "nodeId": "local", "message": f"URL set. Node will apply changes. Current primary channel may have been updated or new channels added based on URL type."}, indent=4)
            else:
                return json.dumps({"status": "error", "message": "Interface does not have setURL method."})
        
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, indent=4)

    @mcp.tool()
    async def reboot(secs: int = 10, nodeId: str = "local") -> str:
        """Reboots the specified node after a delay.

        Args:
            secs (int): Number of seconds to wait before rebooting. Defaults to 10.
            nodeId (str): The node ID or 'local'. Defaults to "local".
        
        Returns:
            str: JSON string with operation status.
        """
        try:
            node = await _get_node_object(iface_manager, nodeId)
            if not node:
                return json.dumps({"status": "error", "message": f"Node {nodeId} not found."})

            if hasattr(node, 'reboot'):
                await asyncio.to_thread(node.reboot, secs)
                return json.dumps({"status": "success", "nodeId": nodeId, "message": f"Node will reboot in {secs} seconds."}, indent=4)
            else:
                # Try via interface if node doesn't have reboot method
                iface = iface_manager.get_interface()
                if nodeId == "local" and hasattr(iface, 'getNode'):
                    node_via_iface = iface.getNode(nodeId)
                    if hasattr(node_via_iface, 'reboot'):
                        await asyncio.to_thread(node_via_iface.reboot, secs)
                        return json.dumps({"status": "success", "nodeId": nodeId, "message": f"Node will reboot in {secs} seconds via interface call."})
                
                return json.dumps({"status": "error", "message": f"Node object for {nodeId} does not have a 'reboot' method."})
        
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, indent=4)

    @mcp.tool()
    async def shutdown(secs: int = 10, nodeId: str = "local") -> str:
        """Shuts down the specified node after a delay.

        Args:
            secs (int): Number of seconds to wait before shutting down. Defaults to 10.
            nodeId (str): The node ID or 'local'. Defaults to "local".

        Returns:
            str: JSON string with operation status.
        """
        try:
            node = await _get_node_object(iface_manager, nodeId)
            if not node:
                return json.dumps({"status": "error", "message": f"Node {nodeId} not found."})

            # Check if the node object has the shutdown method
            if hasattr(node, "shutdown"):
                await asyncio.to_thread(node.shutdown, secs)
                return json.dumps({"status": "success", "nodeId": nodeId, "message": f"Node will shutdown in {secs} seconds."}, indent=4)
            else:
                # Try via interface if node doesn't have shutdown method
                iface = iface_manager.get_interface()
                if nodeId == "local" and hasattr(iface, 'getNode'):
                    node_via_iface = iface.getNode(nodeId) 
                    if hasattr(node_via_iface, 'shutdown'):
                        await asyncio.to_thread(node_via_iface.shutdown, secs)
                        return json.dumps({"status": "success", "nodeId": nodeId, "message": f"Node will shutdown in {secs} seconds via interface call."})
                
                return json.dumps({"status": "error", "message": f"Node object for {nodeId} does not have a 'shutdown' method."})
        
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, indent=4)

    @mcp.tool()
    async def factory_reset(nodeId: str = "local", full: bool = False) -> str:
        """Performs a factory reset on the specified node.

        Args:
            nodeId (str): The node ID or 'local'. Defaults to "local".
            full (bool): If True, performs a more complete factory reset (may erase more settings). Defaults to False.
                         Note: The interpretation of 'full' depends on the device firmware and library version.
        
        Returns:
            str: JSON string with operation status.
        """
        try:
            node = await _get_node_object(iface_manager, nodeId)
            if not node:
                return json.dumps({"status": "error", "message": f"Node {nodeId} not found."})

            if full:
                print(f"Note: 'full=True' for factory_reset is a conceptual parameter. The node will perform its standard factory reset procedure.")

            if hasattr(node, 'factoryReset'):
                await asyncio.to_thread(node.factoryReset)
                return json.dumps({"status": "success", "nodeId": nodeId, "message": "Node will perform a factory reset. It will likely reboot and lose current settings."}, indent=4)
            else:
                # Try via interface if node doesn't have factoryReset method
                iface = iface_manager.get_interface()
                if nodeId == "local" and hasattr(iface, 'getNode'):
                    node_via_iface = iface.getNode(nodeId)
                    if hasattr(node_via_iface, 'factoryReset'):
                        await asyncio.to_thread(node_via_iface.factoryReset)
                        return json.dumps({"status": "success", "nodeId": nodeId, "message": "Node will perform factory reset via interface call."})
                
                return json.dumps({"status": "error", "message": f"Node object for {nodeId} does not have a 'factoryReset' method."})
        
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, indent=4)
    
    return mcp  # Return mcp to chain registrations if needed
