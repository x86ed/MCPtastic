import unittest
import sys
import os
import json
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio

# Add the parent directory to the Python path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from MCPtastic.node import register_node_tools, _get_node_object
from MCPtastic.interface_manager import InterfaceManager

class TestNode(unittest.TestCase):
    def setUp(self):
        # Create mock MCP, interface manager and interface
        self.mock_mcp = MagicMock()
        self.mock_iface_manager = MagicMock(spec=InterfaceManager)
        self.mock_interface = MagicMock()
        self.mock_iface_manager.get_interface.return_value = self.mock_interface
        
        # Create mock local node and remote node
        self.mock_local_node = MagicMock()
        self.mock_remote_node = MagicMock()
        
        # Set up node access via interface
        self.mock_interface.localNode = self.mock_local_node
        self.mock_interface.nodes = {'!abc123': self.mock_remote_node}
        
        # Register the tools with our mock MCP
        register_node_tools(self.mock_mcp, self.mock_iface_manager)

    @patch('MCPtastic.node._get_node_object')
    async def test_show_channels_local_success(self, mock_get_node):
        # Arrange
        self.mock_local_node.channels = [MagicMock()]
        mock_get_node.return_value = self.mock_local_node
        
        # Act - Call the function through the decorator
        # Find the proper function in the mcp.tool() decorator calls
        show_channels_func = None
        for call in self.mock_mcp.tool.mock_calls:
            # Get the function that was decorated
            func = call[1][0] if call[1] else None
            if func and func.__name__ == 'show_channels':
                show_channels_func = func
                break
        
        result = await show_channels_func("local")
        result_json = json.loads(result)
        
        # Assert
        self.assertEqual(result_json["status"], "success")
        self.assertEqual(result_json["nodeId"], "local")
        self.assertIn("channels", result_json)

    @patch('MCPtastic.node._get_node_object')
    async def test_show_channels_node_not_found(self, mock_get_node):
        # Arrange
        mock_get_node.return_value = None
        
        # Find the show_channels function
        show_channels_func = None
        for call in self.mock_mcp.tool.mock_calls:
            func = call[1][0] if call[1] else None
            if func and func.__name__ == 'show_channels':
                show_channels_func = func
                break
        
        # Act
        result = await show_channels_func("!nonexistent")
        result_json = json.loads(result)
        
        # Assert
        self.assertEqual(result_json["status"], "error")
        self.assertIn("not found", result_json["message"])

    @patch('MCPtastic.node._get_node_object')
    async def test_show_info_local_success(self, mock_get_node):
        # Arrange
        mock_get_node.return_value = self.mock_local_node
        self.mock_interface.myInfo = {"name": "TestNode"}
        self.mock_local_node.localConfig = MagicMock()
        self.mock_local_node.moduleConfig = MagicMock()
        
        # Find the show_info function
        show_info_func = None
        for call in self.mock_mcp.tool.mock_calls:
            func = call[1][0] if call[1] else None
            if func and func.__name__ == 'show_info':
                show_info_func = func
                break
        
        # Act
        result = await show_info_func("local")
        result_json = json.loads(result)
        
        # Assert
        self.assertEqual(result_json["status"], "success")
        self.assertEqual(result_json["nodeId"], "local")
        self.assertIn("info", result_json)

    @patch('MCPtastic.node._get_node_object')
    @patch('asyncio.to_thread')
    async def test_set_owner_success(self, mock_to_thread, mock_get_node):
        # Arrange
        mock_get_node.return_value = self.mock_local_node
        self.mock_interface.setOwner = MagicMock()
        mock_to_thread.return_value = None
        
        # Find the set_owner function
        set_owner_func = None
        for call in self.mock_mcp.tool.mock_calls:
            func = call[1][0] if call[1] else None
            if func and func.__name__ == 'set_owner':
                set_owner_func = func
                break
        
        # Act
        result = await set_owner_func("Test User", "Test", False, "local")
        result_json = json.loads(result)
        
        # Assert
        self.assertEqual(result_json["status"], "success")
        self.assertEqual(result_json["nodeId"], "local")
        mock_to_thread.assert_called_once()

    @patch('MCPtastic.node._get_node_object')
    @patch('asyncio.to_thread')
    async def test_get_url_success(self, mock_to_thread, mock_get_node):
        # Arrange
        mock_get_node.return_value = self.mock_local_node
        self.mock_interface.getQRCodeURL = MagicMock(return_value="https://meshtastic.org/qr#...")
        mock_to_thread.return_value = "https://meshtastic.org/qr#..."
        
        # Find the get_url function
        get_url_func = None
        for call in self.mock_mcp.tool.mock_calls:
            func = call[1][0] if call[1] else None
            if func and func.__name__ == 'get_url':
                get_url_func = func
                break
        
        # Act
        result = await get_url_func("local", True)
        result_json = json.loads(result)
        
        # Assert
        self.assertEqual(result_json["status"], "success")
        self.assertEqual(result_json["nodeId"], "local")
        self.assertIn("url", result_json)

    @patch('MCPtastic.node._get_node_object')
    @patch('asyncio.to_thread')
    async def test_set_url_success(self, mock_to_thread, mock_get_node):
        # Arrange
        self.mock_interface.setURL = MagicMock()
        mock_to_thread.return_value = None
        
        # Find the set_url function
        set_url_func = None
        for call in self.mock_mcp.tool.mock_calls:
            func = call[1][0] if call[1] else None
            if func and func.__name__ == 'set_url':
                set_url_func = func
                break
        
        # Act
        result = await set_url_func("https://meshtastic.org/c/#sample", False, "local")
        result_json = json.loads(result)
        
        # Assert
        self.assertEqual(result_json["status"], "success")
        self.assertEqual(result_json["nodeId"], "local")
        mock_to_thread.assert_called_once()

    @patch('MCPtastic.node._get_node_object')
    @patch('asyncio.to_thread')
    async def test_reboot_success(self, mock_to_thread, mock_get_node):
        # Arrange
        mock_get_node.return_value = self.mock_local_node
        self.mock_local_node.reboot = MagicMock()
        mock_to_thread.return_value = None
        
        # Find the reboot function
        reboot_func = None
        for call in self.mock_mcp.tool.mock_calls:
            func = call[1][0] if call[1] else None
            if func and func.__name__ == 'reboot':
                reboot_func = func
                break
        
        # Act
        result = await reboot_func(5, "local")
        result_json = json.loads(result)
        
        # Assert
        self.assertEqual(result_json["status"], "success")
        self.assertEqual(result_json["nodeId"], "local")
        mock_to_thread.assert_called_once()

    @patch('MCPtastic.node._get_node_object')
    @patch('asyncio.to_thread')
    async def test_shutdown_success(self, mock_to_thread, mock_get_node):
        # Arrange
        mock_get_node.return_value = self.mock_local_node
        self.mock_local_node.shutdown = MagicMock()
        mock_to_thread.return_value = None
        
        # Find the shutdown function
        shutdown_func = None
        for call in self.mock_mcp.tool.mock_calls:
            func = call[1][0] if call[1] else None
            if func and func.__name__ == 'shutdown':
                shutdown_func = func
                break
        
        # Act
        result = await shutdown_func(5, "local")
        result_json = json.loads(result)
        
        # Assert
        self.assertEqual(result_json["status"], "success")
        self.assertEqual(result_json["nodeId"], "local")
        mock_to_thread.assert_called_once()

    @patch('MCPtastic.node._get_node_object')
    @patch('asyncio.to_thread')
    async def test_factory_reset_success(self, mock_to_thread, mock_get_node):
        # Arrange
        mock_get_node.return_value = self.mock_local_node
        self.mock_local_node.factoryReset = MagicMock()
        mock_to_thread.return_value = None
        
        # Find the factory_reset function
        factory_reset_func = None
        for call in self.mock_mcp.tool.mock_calls:
            func = call[1][0] if call[1] else None
            if func and func.__name__ == 'factory_reset':
                factory_reset_func = func
                break
        
        # Act
        result = await factory_reset_func("local", False)
        result_json = json.loads(result)
        
        # Assert
        self.assertEqual(result_json["status"], "success")
        self.assertEqual(result_json["nodeId"], "local")
        mock_to_thread.assert_called_once()

    @patch('MCPtastic.node._get_node_object')
    async def test_factory_reset_node_not_found(self, mock_get_node):
        # Arrange
        mock_get_node.return_value = None
        
        # Find the factory_reset function
        factory_reset_func = None
        for call in self.mock_mcp.tool.mock_calls:
            func = call[1][0] if call[1] else None
            if func and func.__name__ == 'factory_reset':
                factory_reset_func = func
                break
        
        # Act
        result = await factory_reset_func("!nonexistent", False)
        result_json = json.loads(result)
        
        # Assert
        self.assertEqual(result_json["status"], "error")
        self.assertIn("not found", result_json["message"])

    @patch('MCPtastic.node._get_node_object')
    async def test_factory_reset_method_not_available(self, mock_get_node):
        # Arrange
        # Create a node without factoryReset method
        node_without_factory_reset = MagicMock()
        # Remove the factoryReset attribute
        del node_without_factory_reset.factoryReset
        mock_get_node.return_value = node_without_factory_reset
        
        # Set up interface that doesn't have getNode method
        mock_interface = MagicMock()
        del mock_interface.getNode
        self.mock_iface_manager.get_interface.return_value = mock_interface
        
        # Find the factory_reset function
        factory_reset_func = None
        for call in self.mock_mcp.tool.mock_calls:
            func = call[1][0] if call[1] else None
            if func and func.__name__ == 'factory_reset':
                factory_reset_func = func
                break
        
        # Act
        result = await factory_reset_func("local", False)
        result_json = json.loads(result)
        
        # Assert
        self.assertEqual(result_json["status"], "error")
        self.assertIn("does not have", result_json["message"])
        self.assertIn("factoryReset", result_json["message"])

# This allows the tests to be run from the command line
if __name__ == "__main__":
    unittest.main()
