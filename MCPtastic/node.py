import json
import sys
import os
import typing
from typing import Optional
import meshtastic
import asyncio
from meshtastic.node import Node
from meshtastic.config_pb2 import Config

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
        iface = await asyncio.to_thread(iface_manager.set_interface, "meshtastic.local", "tcp")
        if not iface:
            raise Exception("Failed to connect to a Meshtastic interface.")

    if nodeId == "local":
        return iface.localNode
    else:
        # For remote nodes, we need to ensure the node list is populated.
        # The meshtastic library usually handles this on connection or via events.
        # If direct access by nodeId is needed and might not be populated,
        # a brief wait or a refresh mechanism might be necessary.
        # For now, assume iface.nodesByNum or a similar attribute is up-to-date.
        if iface.nodes:
            return iface.nodes.get(nodeId)
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
                    channels_info.append(meshtastic.util.MessageToJson(ch_settings))
            elif hasattr(node, 'settings') and node.settings.channel_settings: # remote nodes store in .settings.channel_settings
                for ch_settings in node.settings.channel_settings:
                    channels_info.append(meshtastic.util.MessageToJson(ch_settings))
            elif hasattr(node, 'localConfig') and node.localConfig.channel_settings: # some local node versions
                 for ch_settings in node.localConfig.channel_settings:
                    channels_info.append(meshtastic.util.MessageToJson(ch_settings))
            else: # Try remote call if local attributes are not found or empty
                remote_channels = await asyncio.to_thread(node.showChannels)
                if remote_channels: # showChannels already returns a dict/list of dicts
                    return json.dumps({"status": "success", "nodeId": nodeId, "channels": remote_channels}, indent=4)
                else:
                    return json.dumps({"status": "error", "nodeId": nodeId, "message": "No channel data found for node or method not directly available for remote nodes in this manner."})
            
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
                info_data["myNodeInfo"] = iface.myInfo
                info_data["localConfig"] = meshtastic.util.MessageToJson(iface.localNode.localConfig)
                info_data["moduleConfig"] = meshtastic.util.MessageToJson(iface.localNode.moduleConfig)
                info_data["channels"] = [meshtastic.util.MessageToJson(ch) for ch in iface.localNode.channels]
            else:
                # For remote nodes, showInfo() might be the best bet if it returns data
                # or we might need to request specific configurations.
                # Let's assume node.showInfo() can be adapted or we use available properties.
                # meshtastic-python's Node.showInfo() prints. We need the data.
                # A common approach is to get the raw protobufs.
                if hasattr(node, 'localConfig') and node.localConfig:
                    info_data["localConfig"] = meshtastic.util.MessageToJson(node.localConfig)
                if hasattr(node, 'moduleConfig') and node.moduleConfig:
                    info_data["moduleConfig"] = meshtastic.util.MessageToJson(node.moduleConfig)
                if hasattr(node, 'role') and node.role: #This is not standard, but some custom versions might have it
                     info_data["role"] = Config.DeviceConfig.Role.Name(node.role)

                # If node.showInfo() exists and returns a dict (ideal but not standard)
                # info_data = await asyncio.to_thread(node.showInfo)
                # Fallback: try to get common useful info if direct showInfo() is not data-returning
                if not info_data: # If we couldn't get much yet
                    info_data["nodeID"] = node.nodeId
                    info_data["longName"] = node.longName
                    info_data["shortName"] = node.shortName
                    info_data["hwModel"] = node.hwModel
                    info_data["isRouter"] = node.isRouter
                    info_data["isMqtt"] = node.isMqttEnabled
                    if hasattr(node, 'channels'): # Attempt to get channels if available
                        channels_info = []
                        if node.channels:
                             for ch_settings in node.channels:
                                channels_info.append(meshtastic.util.MessageToJson(ch_settings))
                        elif hasattr(node, 'settings') and node.settings.channel_settings:
                            for ch_settings in node.settings.channel_settings:
                                channels_info.append(meshtastic.util.MessageToJson(ch_settings))
                        info_data["channels"] = channels_info


            if not info_data: # If still no data (e.g. remote node with minimal info)
                 # Attempt to call the standard showInfo if all else fails, though it prints
                try:
                    # This is a bit of a hack. showInfo prints. We can't capture its output directly here
                    # without redirecting stdout, which is complex in async and might affect MCP.
                    # For now, we'll just indicate it would be printed or try a remote request.
                    # await asyncio.to_thread(node.showInfo) # This would print to MCP's console
                    # A better way for remote nodes is explicit config requests, but that's more involved.
                    # For now, we return what we have or a message.
                    if nodeId != "local":
                         return json.dumps({"status": "success", "nodeId": nodeId, "message": "Basic info retrieved. For full remote node details, specific config requests might be needed.", "data": {"nodeID": node.nodeId, "longName": node.longName, "shortName": node.shortName, "hwModel": node.hwModel} }, indent=4)
                except Exception as e_info:
                    return json.dumps({"status": "error", "nodeId": nodeId, "message": f"Could not retrieve detailed info for node: {str(e_info)}"})


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

            iface = iface_manager.get_interface() # Needed for localNode case and sending commands
            
            current_long_name = None
            current_short_name = None

            if nodeId == "local":
                current_long_name = iface.getLongName()
                current_short_name = iface.getShortName()
            elif hasattr(node, 'user') and node.user: # For remote nodes, user info might be populated
                current_long_name = node.user.long_name
                current_short_name = node.user.short_name
            
            # Use current names if new names are not provided
            final_long_name = long_name if long_name is not None else current_long_name
            final_short_name = short_name if short_name is not None else current_short_name

            # Ensure names are not None if they couldn't be fetched and weren't provided
            if final_long_name is None: final_long_name = "Meshtastic" # Default if not set
            if final_short_name is None: final_short_name = "Mesh"    # Default if not set


            if nodeId == "local":
                # For local node, setOwner is straightforward if available on localNode,
                # otherwise use interface methods.
                # meshtastic-python's typical way is via iface.setOwner()
                await asyncio.to_thread(iface.setOwner, final_long_name, final_short_name, is_licensed)
            else:
                # For remote nodes, setOwner is a command sent to the node.
                await asyncio.to_thread(node.setOwner, final_long_name, final_short_name, is_licensed)
            
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

            iface = iface_manager.get_interface() # Needed for some operations

            if nodeId == "local":
                # meshtastic-python's Interface has getURL() and getQRCodeURL()
                # getURL(channelIndex) gives specific channel URL
                # getQRCodeURL() gives a URL that shows QR codes for all channels
                if includeAll:
                    url = await asyncio.to_thread(iface.getQRCodeURL)
                    return json.dumps({"status": "success", "nodeId": "local", "type": "all_channels_qr_code_url", "url": url}, indent=4)
                else:
                    # Assuming primary channel is index 0
                    url = await asyncio.to_thread(iface.getURL, 0)
                    return json.dumps({"status": "success", "nodeId": "local", "type": "primary_channel_url", "url": url}, indent=4)
            else:
                # For remote nodes, there isn't a direct "getURL" command.
                # URLs are constructed based on channel settings.
                # We'd need to fetch channel settings first.
                # This is complex as it requires having the channel PSK.
                # The `meshtastic --info` CLI can construct these if it has the data.
                # A simplified approach: return the channel settings if available, user can make URL.
                
                channels_data = []
                if hasattr(node, 'settings') and node.settings.channel_settings:
                    for i, ch_setting in enumerate(node.settings.channel_settings):
                        # Constructing a URL requires psk, name, mode.
                        # This is a simplified representation.
                        # Real URL construction: meshtastic.util.our_make_full_channel_url
                        # For security, we won't expose PSKs directly here.
                        # We can provide a placeholder or guide the user.
                        ch_info = {
                            "index": i,
                            "name": ch_setting.name,
                            "role": Config.ChannelConfig.Role.Name(ch_setting.role) if hasattr(ch_setting, "role") else "PRIMARY", # role may not exist on older firmwares
                            "psk_hint": "PSK required to form URL, not shown for security."
                        }
                        # Attempt to build URL if possible (requires meshtastic.util and channel bytes)
                        try:
                            # This is tricky for remote nodes as we don't have the raw channel object easily
                            # or the full interface context to generate the PSK bytes needed for the URL.
                            # The function `our_make_full_channel_url` needs more than just the settings protobuf.
                            # For now, we'll just return channel names.
                            pass
                        except Exception:
                            pass # Could not form URL
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
                # TODO: Implement setURL for remote nodes if node.setURL() or similar becomes available.
                # This typically involves sending a SetChannelRequest protobuf message.
                # For now, remote setURL is complex due to needing specific protobuf constructions.
                # node.writeChannel(channel_index, settings_protobuf) is one way if settings are parsed from URL.
                return json.dumps({"status": "error", "message": f"setURL for remote node '{nodeId}' is not directly supported by this tool yet. Use on local node."})

            iface = iface_manager.get_interface()
            if not iface:
                 return json.dumps({"status": "error", "message": "Interface not available."})
            
            # The setURL method on the interface typically applies the URL.
            # The `addOnly` parameter is not standard in meshtastic-python's setURL.
            # It usually replaces or sets the primary channel.
            # If `addOnly` functionality is critical, it would require custom logic:
            # 1. Parse URL to get channel settings.
            # 2. Get existing channels.
            # 3. Compare and decide whether to add or skip.
            # This is advanced. For now, we use the standard behavior.

            if addOnly:
                # Log that addOnly is not standard for setURL
                print(f"Note: 'addOnly' parameter for setURL is not a standard feature of meshtastic.py; URL will likely set the primary channel or be handled as per library default.")

            await asyncio.to_thread(iface.setURL, url)
            # To confirm, we could fetch channels after setting, but for now, assume success if no exception.
            return json.dumps({"status": "success", "nodeId": "local", "message": f"URL set. Node will apply changes. Current primary channel may have been updated or new channels added based on URL type."}, indent=4)
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

            await asyncio.to_thread(node.reboot, secs)
            return json.dumps({"status": "success", "nodeId": nodeId, "message": f"Node will reboot in {secs} seconds."}, indent=4)
        except AttributeError: # If node object doesn't have reboot (e.g. very old fw or simple dict)
             iface = iface_manager.get_interface()
             if nodeId == "local" and hasattr(iface, 'getNode') and hasattr(iface.getNode(nodeId), 'reboot'): # try via interface
                 await asyncio.to_thread(iface.getNode(nodeId).reboot, secs)
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

            # Check if the node object has the shutdown method (older firmwares might not)
            if not hasattr(node, "shutdown"):
                 iface = iface_manager.get_interface() # Check if it's on the interface.getNode()
                 if nodeId == "local" and hasattr(iface, 'getNode') and hasattr(iface.getNode(nodeId), 'shutdown'):
                     await asyncio.to_thread(iface.getNode(nodeId).shutdown, secs)
                     return json.dumps({"status": "success", "nodeId": nodeId, "message": f"Node will shutdown in {secs} seconds via interface call."})    
                 return json.dumps({"status": "error", "nodeId": nodeId, "message": "Node does not support shutdown command or method not found."})

            await asyncio.to_thread(node.shutdown, secs)
            return json.dumps({"status": "success", "nodeId": nodeId, "message": f"Node will shutdown in {secs} seconds."}, indent=4)
        except AttributeError: # Fallback for safety, though hasattr should catch it.
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

            # The factoryReset method might not have a 'full' parameter in all lib versions/firmwares.
            # We will call it if it exists, otherwise call without it.
            # meshtastic-python's Node.factoryReset() doesn't take args. It's a simple command.
            # The 'full' might be a conceptual parameter for the tool, but the underlying command is fixed.
            
            if full:
                # Log that 'full' might not be specifically implemented by the device command
                print(f"Note: 'full=True' for factory_reset is a conceptual parameter. The node will perform its standard factory reset procedure.")

            await asyncio.to_thread(node.factoryReset)
            return json.dumps({"status": "success", "nodeId": nodeId, "message": "Node will perform a factory reset. It will likely reboot and lose current settings."}, indent=4)

        except AttributeError: # If node object doesn't have factoryReset
             iface = iface_manager.get_interface()
             if nodeId == "local" and hasattr(iface, 'getNode') and hasattr(iface.getNode(nodeId), 'factoryReset'):
                 await asyncio.to_thread(iface.getNode(nodeId).factoryReset)
                 return json.dumps({"status": "success", "nodeId": nodeId, "message": "Node will perform factory reset via interface call."})
             return json.dumps({"status": "error", "message": f"Node object for {nodeId} does not have a 'factoryReset' method."})
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, indent=4)
    
    return mcp # Return mcp to chain registrations if needed
