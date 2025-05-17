# This module provides shared functionality for managing and caching interfaces.

from typing import Optional
import mcp
import meshtastic
import meshtastic.mesh_interface
import meshtastic.tcp_interface
import meshtastic.ble_interface

class InterfaceManager:
    _cached_iface = None
    _cached_hostname = None

    @staticmethod
    def set_interface(hostname: str, connection_type: str = "tcp") -> None:
        """Set and cache the interface based on the hostname and connection type.

        Args:
            hostname (str): The hostname to connect to.
            connection_type (str): The type of connection (e.g., "tcp" or "ble"). Defaults to "tcp".
        """
        if InterfaceManager._cached_iface:
            InterfaceManager._cached_iface.close()

        if connection_type == "tcp":
            InterfaceManager._cached_iface = meshtastic.tcp_interface.TCPInterface(hostname)
        elif connection_type == "ble":
            InterfaceManager._cached_iface = meshtastic.ble_interface.BLEInterface(hostname)
        else:
            raise ValueError(f"Unsupported connection type: {connection_type}")

        InterfaceManager._cached_hostname = hostname

    @staticmethod
    def get_interface(hostname: str) -> Optional[meshtastic.mesh_interface.MeshInterface]:
        """Retrieve the cached interface if it matches the hostname.

        Args:
            hostname (str): The hostname to check.

        Returns:
            Optional[meshtastic.interface.Interface]: The cached interface or None if no match.
        """
        if InterfaceManager._cached_hostname == hostname:
            return InterfaceManager._cached_iface
        return None