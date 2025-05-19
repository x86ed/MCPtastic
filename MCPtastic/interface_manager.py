# This module provides shared functionality for managing and caching interfaces.

from typing import Optional
import meshtastic
import meshtastic.tcp_interface
import meshtastic.ble_interface
import meshtastic.serial_interface
import meshtastic.mesh_interface

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
            debugOut: Output stream for debug messages. Defaults to None.
            noProto (bool): Whether to disable protocol communication. Defaults to False.
            connectNow (bool): Whether to connect immediately. Defaults to True.
            portNumber (int): Port number for TCP connections. Defaults to 4403.
            noNodes (bool): Whether to disable node communication. Defaults to False.

        Returns:
            Optional[meshtastic.mesh_interface.MeshInterface]: The interface instance.

        Raises:
            ValueError: If the connection type is not supported.
        """
        if self._cached_iface:
            self._cached_iface.close()

        if connection_type == "tcp":
            self._cached_iface = meshtastic.tcp_interface.TCPInterface(hostname, debugOut, noProto, connectNow, portNumber, noNodes)
        elif connection_type == "ble":
            self._cached_iface = meshtastic.ble_interface.BLEInterface(hostname, noProto, debugOut, noNodes)
        elif connection_type == "serial":
            self._cached_iface = meshtastic.serial_interface.SerialInterface(hostname, debugOut, noProto, connectNow, noNodes)
        else:
            raise ValueError(f"Unsupported connection type: {connection_type}")

        self._cached_hostname = hostname
        return self._cached_iface

    def get_interface(self, hostname: Optional[str] = None) -> Optional[meshtastic.mesh_interface.MeshInterface]:
        """Retrieve the cached interface if it matches the hostname.

        Args:
            hostname (Optional[str]): The hostname to match. If None, returns the cached interface.

        Returns:
            Optional[meshtastic.mesh_interface.MeshInterface]: The cached interface or None if no match.
        """
        if hostname is None or hostname == self._cached_hostname:
            return self._cached_iface
        return None