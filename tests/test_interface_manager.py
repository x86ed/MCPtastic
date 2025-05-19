import unittest
from unittest.mock import MagicMock, patch, call
import sys
from typing import Optional

# Create comprehensive mock module structure
mock_mesh_interface = MagicMock(name="MeshInterface")
sys.modules["meshtastic"] = MagicMock()
sys.modules["meshtastic.mesh_interface"] = MagicMock()
sys.modules["meshtastic.mesh_interface"].MeshInterface = mock_mesh_interface
sys.modules["meshtastic.tcp_interface"] = MagicMock()
sys.modules["meshtastic.ble_interface"] = MagicMock()
sys.modules["meshtastic.serial_interface"] = MagicMock()

# Create mock classes for interfaces
mock_tcp_interface = MagicMock()
mock_ble_interface = MagicMock()
mock_serial_interface = MagicMock()
mock_tcp_interface_class = MagicMock(return_value=mock_tcp_interface)
mock_ble_interface_class = MagicMock(return_value=mock_ble_interface)
mock_serial_interface_class = MagicMock(return_value=mock_serial_interface)

# Add the interface classes to their respective modules
sys.modules["meshtastic.tcp_interface"].TCPInterface = mock_tcp_interface_class
sys.modules["meshtastic.ble_interface"].BLEInterface = mock_ble_interface_class
sys.modules["meshtastic.serial_interface"].SerialInterface = mock_serial_interface_class

# Now we can safely import the InterfaceManager
from MCPtastic.interface_manager import InterfaceManager

class TestInterfaceManager(unittest.TestCase):

    def setUp(self):
        # Reset mocks before each test
        mock_tcp_interface_class.reset_mock()
        mock_ble_interface_class.reset_mock()
        mock_serial_interface_class.reset_mock()
        mock_tcp_interface.reset_mock()
        mock_ble_interface.reset_mock()
        mock_serial_interface.reset_mock()
        
        # Create fresh instance for each test
        self.manager = InterfaceManager()

    def test_init_state(self):
        """Test that the initial state is correctly set"""
        self.assertIsNone(self.manager._cached_iface)
        self.assertIsNone(self.manager._cached_hostname)

    def test_set_interface_tcp(self):
        """Test setting a TCP interface"""
        hostname = "192.168.1.100"
        
        # Use patch to directly patch the interface class inside the method
        with patch('MCPtastic.interface_manager.meshtastic.tcp_interface.TCPInterface', 
                  return_value=mock_tcp_interface) as mock_class:
            result = self.manager.set_interface(hostname, "tcp")
            
            # Verify TCP interface was created with correct parameters
            mock_class.assert_called_once_with(
                hostname, None, False, True, 4403, False
            )
        
        # Verify internal state was updated
        self.assertEqual(self.manager._cached_iface, mock_tcp_interface)
        self.assertEqual(self.manager._cached_hostname, hostname)
        
        # Verify the result is the interface
        self.assertEqual(result, mock_tcp_interface)

    def test_set_interface_ble(self):
        """Test setting a BLE interface"""
        hostname = "device_address"
        
        # Use patch to directly patch the interface class inside the method
        with patch('MCPtastic.interface_manager.meshtastic.ble_interface.BLEInterface', 
                  return_value=mock_ble_interface) as mock_class:
            result = self.manager.set_interface(hostname, "ble")
            
            # Verify BLE interface was created with correct parameters
            mock_class.assert_called_once_with(
                hostname, False, None, False
            )
        
        # Verify internal state was updated
        self.assertEqual(self.manager._cached_iface, mock_ble_interface)
        self.assertEqual(self.manager._cached_hostname, hostname)
        
        # Verify the result is the interface
        self.assertEqual(result, mock_ble_interface)

    def test_set_interface_serial(self):
        """Test setting a Serial interface"""
        hostname = "/dev/ttyUSB0"
        
        # Use patch to directly patch the interface class inside the method
        with patch('MCPtastic.interface_manager.meshtastic.serial_interface.SerialInterface', 
                  return_value=mock_serial_interface) as mock_class:
            result = self.manager.set_interface(hostname, "serial")
            
            # Verify Serial interface was created with correct parameters
            mock_class.assert_called_once_with(
                hostname, None, False, True, False
            )
        
        # Verify internal state was updated
        self.assertEqual(self.manager._cached_iface, mock_serial_interface)
        self.assertEqual(self.manager._cached_hostname, hostname)
        
        # Verify the result is the interface
        self.assertEqual(result, mock_serial_interface)

    def test_set_interface_invalid_type(self):
        """Test setting an invalid interface type raises ValueError"""
        with self.assertRaises(ValueError):
            self.manager.set_interface("192.168.1.100", "invalid_type")

    def test_set_interface_closes_previous(self):
        """Test that setting a new interface closes the previous one"""
        # Set initial interface
        with patch('MCPtastic.interface_manager.meshtastic.tcp_interface.TCPInterface', 
                  return_value=mock_tcp_interface):
            self.manager.set_interface("first_host", "tcp")
        
        # Reset the mock to clear any previous calls
        mock_tcp_interface.reset_mock()
        
        # Set new interface
        with patch('MCPtastic.interface_manager.meshtastic.tcp_interface.TCPInterface', 
                  return_value=mock_tcp_interface):
            self.manager.set_interface("second_host", "tcp")
        
        # Verify previous interface was closed
        mock_tcp_interface.close.assert_called_once()

    def test_set_interface_with_custom_parameters(self):
        """Test setting an interface with custom parameters"""
        hostname = "custom.host"
        debug_out = MagicMock()
        no_proto = True
        connect_now = False
        port_number = 4404
        no_nodes = True
        
        # Use patch to directly patch the interface class inside the method
        with patch('MCPtastic.interface_manager.meshtastic.tcp_interface.TCPInterface', 
                  return_value=mock_tcp_interface) as mock_class:
            self.manager.set_interface(
                hostname, "tcp", debug_out, no_proto, connect_now, port_number, no_nodes
            )
            
            # Verify TCP interface was created with custom parameters
            mock_class.assert_called_once_with(
                hostname, debug_out, no_proto, connect_now, port_number, no_nodes
            )

    def test_get_interface(self):
        """Test getting the cached interface"""
        # Set an interface first
        with patch('MCPtastic.interface_manager.meshtastic.tcp_interface.TCPInterface', 
                  return_value=mock_tcp_interface):
            self.manager.set_interface("192.168.1.100", "tcp")
        
        # Get the interface
        result = self.manager.get_interface()
        
        # Verify we got the cached interface
        self.assertEqual(result, mock_tcp_interface)
        
    def test_get_interface_when_none_set(self):
        """Test getting the interface when none has been set"""
        # Get the interface without setting one first
        result = self.manager.get_interface()
        
        # Verify we got None
        self.assertIsNone(result)

    def test_get_interface_with_hostname(self):
        """Test getting an interface that matches the cached hostname"""
        hostname = "test_host"
        with patch('MCPtastic.interface_manager.meshtastic.tcp_interface.TCPInterface', 
                  return_value=mock_tcp_interface):
            self.manager.set_interface(hostname, "tcp")
        
        # Get the interface
        result = self.manager.get_interface(hostname)
        
        # Verify we got the cached interface
        self.assertEqual(result, mock_tcp_interface)
        
    def test_get_interface_with_different_hostname(self):
        """Test getting an interface with a hostname that doesn't match the cached one"""
        # Set up an interface with one hostname
        with patch('MCPtastic.interface_manager.meshtastic.tcp_interface.TCPInterface', 
                  return_value=mock_tcp_interface):
            self.manager.set_interface("first_host", "tcp")
        
        # Try to get an interface with a different hostname
        result = self.manager.get_interface("different_host")
        
        # The manager should return None since the hostnames don't match
        self.assertIsNone(result)

if __name__ == '__main__':
    unittest.main()