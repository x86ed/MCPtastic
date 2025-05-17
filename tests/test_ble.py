import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import sys
import os

# Mock the interface_manager module which is being imported in ble.py
sys.modules['interface_manager'] = MagicMock()
InterfaceManager_mock = MagicMock()
sys.modules['interface_manager'].InterfaceManager = InterfaceManager_mock

# Mock meshtastic module
sys.modules['meshtastic'] = MagicMock()
sys.modules['meshtastic.ble_interface'] = MagicMock()
sys.modules['meshtastic.ble_interface'].BLEInterface = MagicMock()

# Now we can safely import the module being tested
from MCPtastic.ble import register_ble

class TestBLE:
    
    def setup_method(self):
        # Create mock MCP object with proper function capturing
        self.registered_functions = {}
        
        # Create a tool decorator that captures the registered functions
        def mock_tool_decorator():
            def decorator(func):
                self.registered_functions[func.__name__] = func
                return func
            return decorator
        
        self.mcp = MagicMock()
        self.mcp.tool.side_effect = mock_tool_decorator
    
    @pytest.mark.asyncio
    async def test_ble_scan_with_devices(self):
        # Setup mock devices
        mock_device1 = MagicMock()
        mock_device1.name = "Test Device 1"
        mock_device1.address = "11:22:33:44:55:66"
        
        mock_device2 = MagicMock()
        mock_device2.name = "Test Device 2"
        mock_device2.address = "AA:BB:CC:DD:EE:FF"
        
        # Mock the scan method
        scan_mock = MagicMock(return_value=[mock_device1, mock_device2])
        sys.modules['meshtastic.ble_interface'].BLEInterface.scan = scan_mock
        
        # Register BLE tools
        registered_mcp = register_ble(self.mcp)
        
        # Get the registered function
        assert 'ble_scan' in self.registered_functions, "ble_scan function not registered"
        ble_scan_func = self.registered_functions['ble_scan']
        
        # Call the function and check results
        result = await ble_scan_func()
        
        assert "starting BLE scan..." in result
        assert "Found: name='Test Device 1' address='11:22:33:44:55:66'" in result
        assert "Found: name='Test Device 2' address='AA:BB:CC:DD:EE:FF'" in result
    
    @pytest.mark.asyncio
    async def test_ble_scan_no_devices(self):
        # Return empty list for scan
        scan_mock = MagicMock(return_value=[])
        sys.modules['meshtastic.ble_interface'].BLEInterface.scan = scan_mock
        
        # Register BLE tools
        register_ble(self.mcp)
        
        # Get the registered function
        assert 'ble_scan' in self.registered_functions, "ble_scan function not registered"
        ble_scan_func = self.registered_functions['ble_scan']
        
        # Call the function and check results
        result = await ble_scan_func()
        
        assert result == "starting BLE scan...\n"
    
    @pytest.mark.asyncio
    async def test_ble_connect_success(self):
        # Setup mock interface
        mock_interface = MagicMock()
        mock_interface.connect = MagicMock()
        
        # Configure the mocked InterfaceManager
        InterfaceManager_mock.get_interface = MagicMock(return_value=mock_interface)
        
        # Register BLE tools
        register_ble(self.mcp)
        
        # Get the registered function
        assert 'ble_connect' in self.registered_functions, "ble_connect function not registered"
        ble_connect_func = self.registered_functions['ble_connect']
        
        # Call the function with an address and check results
        test_address = "11:22:33:44:55:66"
        result = await ble_connect_func(test_address)
        
        # Verify interface was requested and connect was called
        InterfaceManager_mock.get_interface.assert_called_once_with(test_address)
        mock_interface.connect.assert_called_once()
        
        # Verify output message
        assert "connecting to BLE device..." in result
        assert f"Connected to {test_address}" in result
    
    @pytest.mark.asyncio
    async def test_ble_connect_failure(self):
        # Setup mock interface to raise an exception
        InterfaceManager_mock.get_interface = MagicMock(side_effect=Exception("Connection failed"))
        
        # Register BLE tools
        register_ble(self.mcp)
        
        # Get the registered function
        assert 'ble_connect' in self.registered_functions, "ble_connect function not registered"
        ble_connect_func = self.registered_functions['ble_connect']
        
        # Call the function with an address and check results
        test_address = "11:22:33:44:55:66"
        result = await ble_connect_func(test_address)
        
        # Verify error message
        assert "connecting to BLE device..." in result
        assert "Failed to connect: Connection failed" in result
    
    def test_register_ble_returns_mcp(self):
        # Register BLE tools
        result = register_ble(self.mcp)
        
        # Verify that register_ble returns the mcp object it was given
        assert result is self.mcp