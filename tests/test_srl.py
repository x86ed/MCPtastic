import unittest
from unittest.mock import MagicMock, patch, call
import sys
import asyncio
import logging

# Enable logging for debugging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create mock classes before importing module under test
mock_serial_interface = MagicMock()
mock_serial_interface_class = MagicMock(return_value=mock_serial_interface)

# Mock the MeshInterface class and the interface manager
mock_interface_manager = MagicMock()
mock_mcp = MagicMock()

# Create a tool registration mock to capture the registered function
registered_tools = {}
def mock_tool_decorator():
    def decorator(func):
        registered_tools[func.__name__] = func
        return func
    return decorator

mock_mcp.tool = mock_tool_decorator

# Create an actual custom class to trace the calls
class TracedMock(MagicMock):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.traced_calls = []
        self._connect_side_effect = None
    
    def connect(self, *args, **kwargs):
        logger.debug("TracedMock.connect() called")
        self.traced_calls.append(("connect", args, kwargs))
        
        # Handle side effects if set
        if self._connect_side_effect:
            if isinstance(self._connect_side_effect, Exception):
                raise self._connect_side_effect
            elif callable(self._connect_side_effect):
                return self._connect_side_effect(*args, **kwargs)
            else:
                return self._connect_side_effect
        
        return MagicMock()
    
    @property
    def connect_side_effect(self):
        return self._connect_side_effect
    
    @connect_side_effect.setter
    def connect_side_effect(self, effect):
        self._connect_side_effect = effect

# Properly patch the modules
sys.modules['meshtastic'] = MagicMock()
sys.modules['meshtastic.serial_interface'] = MagicMock()

# Use patch to mock the necessary modules
with patch('meshtastic.serial_interface.SerialInterface', mock_serial_interface_class):
    # Import after mocks are set up
    from MCPtastic.srl import register_serial

class TestSerial(unittest.TestCase):

    def setUp(self):
        # Reset mocks before each test
        mock_serial_interface_class.reset_mock()
        mock_serial_interface.reset_mock()
        mock_interface_manager.reset_mock()
        registered_tools.clear()
        
        # Register tools
        register_serial(mock_mcp, mock_interface_manager)

    def test_register_serial_returns_mcp(self):
        """Test that register_serial returns the MCP instance"""
        result = register_serial(mock_mcp, mock_interface_manager)
        self.assertEqual(result, mock_mcp)

    def test_serial_connect_registers_tool(self):
        """Test that serial_connect is registered as a tool"""
        self.assertIn('serial_connect', registered_tools)
        
    def test_serial_connect_uses_interface_manager(self):
        """Test that serial_connect uses the interface manager to set the interface"""
        # Set up the test
        path = "/dev/ttyUSB0"
        
        # Create a better traced mock for this test
        traced_mock = TracedMock()
        
        # Debug what's happening with the mock
        def mock_set_interface(*args, **kwargs):
            logger.debug(f"mock_set_interface called with {args}, {kwargs}")
            return traced_mock
        
        mock_interface_manager.set_interface = MagicMock(side_effect=mock_set_interface)
        
        # Call the serial_connect function
        try:
            result = asyncio.run(registered_tools['serial_connect'](path))
            logger.debug(f"Result: {result}")
            logger.debug(f"Traced calls: {traced_mock.traced_calls}")
        except Exception as e:
            self.fail(f"serial_connect raised exception: {e}")
        
        # Verify interface_manager.set_interface was called with correct arguments
        mock_interface_manager.set_interface.assert_called_once_with(
            path, "serial", None, False, True, 4403, False
        )
        
        # Verify connect was called on the specific interface instance
        self.assertTrue(
            any(call[0] == "connect" for call in traced_mock.traced_calls),
            f"connect() not called on interface. Traced calls: {traced_mock.traced_calls}. Output: {result}"
        )
        
        # Verify the output message contains the expected text
        self.assertIn(f"Connected to {path}", result)

    def test_serial_connect_handles_exceptions(self):
        """Test that serial_connect handles exceptions properly"""
        # Set up the test
        path = "/dev/ttyUSB0"
        mock_interface_manager.set_interface.side_effect = Exception("Connection failed")
        
        # Call the serial_connect function
        result = asyncio.run(registered_tools['serial_connect'](path))
        
        # Verify the output message contains the expected error text
        self.assertIn("Failed to connect: Connection failed", result)

    def test_serial_connect_handles_connect_exceptions(self):
        """Test that serial_connect handles exceptions from the connect method"""
        # Set up the test
        path = "/dev/ttyUSB0"
        
        # Create a traced mock with a specific side effect
        traced_mock = TracedMock()
        traced_mock.connect_side_effect = Exception("Connect failed")
        mock_interface_manager.set_interface.return_value = traced_mock
        
        # Call the serial_connect function
        result = asyncio.run(registered_tools['serial_connect'](path))
        
        # Verify the output message contains the expected error text
        self.assertIn("Failed to connect: Connect failed", result)

    def test_serial_connect_with_custom_parameters(self):
        """Test serial_connect with custom parameters"""
        # Set up the test
        path = "/dev/ttyUSB0"
        debug_out = MagicMock()
        no_proto = True
        connect_now = False
        no_nodes = True
        
        # Create a better traced mock for this test
        traced_mock = TracedMock()
        
        # Debug what's happening with the mock
        def mock_set_interface(*args, **kwargs):
            logger.debug(f"mock_set_interface called with custom params: {args}, {kwargs}")
            return traced_mock
        
        mock_interface_manager.set_interface = MagicMock(side_effect=mock_set_interface)
        
        # Call the serial_connect function
        result = asyncio.run(registered_tools['serial_connect'](
            path, debug_out, no_proto, connect_now, no_nodes
        ))
        logger.debug(f"Custom params result: {result}")
        logger.debug(f"Traced calls: {traced_mock.traced_calls}")
        
        # Verify interface_manager.set_interface was called with correct arguments
        mock_interface_manager.set_interface.assert_called_once_with(
            path, "serial", debug_out, no_proto, connect_now, 4403, no_nodes
        )
        
        # Verify connect was called on the traced interface
        self.assertTrue(
            any(call[0] == "connect" for call in traced_mock.traced_calls),
            f"connect() not called on interface. Traced calls: {traced_mock.traced_calls}. Output: {result}"
        )
        
        # Verify the output message contains the expected text
        self.assertIn(f"Connected to {path}", result)
        
if __name__ == '__main__':
    unittest.main()