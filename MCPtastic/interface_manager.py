# This module provides shared functionality for managing and caching interfaces.

from typing import Optional
import mcp
import meshtastic
import meshtastic.mesh_interface
import meshtastic.tcp_interface
import meshtastic.ble_interface
import meshtastic.serial_interface

class InterfaceManager:
    def __init__(self):
        """Initialize the InterfaceManager with no cached interface."""
        self._cached_iface = None
        self._cached_hostname = None

    def set_interface(self, hostname: str, connection_type: str = "tcp", debugOut=None, noProto: bool = False, connectNow: bool = True, portNumber: int = 4403, noNodes: bool = False) -> Optional[meshtastic.mesh_interface.MeshInterface]:
        """Set and cache the interface based on the hostname and connection type.

        Args:
            hostname (str): The hostname to connect to.
            connection_type (str): The type of connection (e.g., "tcp" or "ble"). Defaults to "tcp".
        """
        if self._cached_iface:
            self._cached_iface.close()

        if connection_type == "tcp":
            self._cached_iface = meshtastic.tcp_interface.TCPInterface(hostname, debugOut, noProto,connectNow,portNumber,noNodes)
        elif connection_type == "ble":
            self._cached_iface = meshtastic.ble_interface.BLEInterface(hostname,noProto,debugOut,noNodes)
        elif connection_type == "serial":
            self._cached_iface = meshtastic.serial_interface.SerialInterface(hostname, debugOut, noProto,connectNow,noNodes)
        else:
            raise ValueError(f"Unsupported connection type: {connection_type}")

        self._cached_hostname = hostname
        return self._cached_iface

    def get_interface(self) -> Optional[meshtastic.mesh_interface.MeshInterface]:
        """Retrieve the cached interface if it matches the hostname.

        Returns:
            Optional[meshtastic.interface.Interface]: The cached interface or None if no match.
        """
        return self._cached_iface