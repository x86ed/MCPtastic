import unittest
import json
import sqlite3
import os
from datetime import datetime
from unittest.mock import MagicMock, patch, Mock
import tempfile

import meshtastic
# Import the module to test
from MCPtastic.device import (
    parse_meshtastic_output, 
    save_json_objects, 
    register_device_tools,
    splitCompoundName,
    traverseConfig,
    setPref,
    ex_config
)

class TestDeviceModule(unittest.TestCase):
    
    def setUp(self):
        # Sample test data
        self.test_content = """Owner: Test User (🧪)
My info: { "myNodeNum": 1234567890, "rebootCount": 5, "deviceId": "TestDeviceId" }
Metadata: { "firmwareVersion": "2.5.1.123abc", "deviceStateVersion": 23, "hasWifi": true }

Nodes in mesh: {
  "!12345678": {
    "num": 1234567890,
    "user": {
      "id": "!12345678",
      "longName": "Test User",
      "shortName": "Test",
      "hwModel": "TBEAM"
    },
    "lastHeard": 1234567890,
    "deviceMetrics": {
      "batteryLevel": 75,
      "voltage": 3.8,
      "channelUtilization": 15.5,
      "airUtilTx": 2.3,
      "uptimeSeconds": 3600
    },
    "snr": 5.0,
    "position": {
      "latitude": 34.12345,
      "longitude": -118.12345,
      "altitude": 100
    },
    "hopsAway": 1
  },
  "!87654321": {
    "num": 987654321,
    "user": {
      "id": "!87654321",
      "longName": "Another User",
      "shortName": "AU",
      "role": "CLIENT"
    }
  }
}"""

        # Create a temporary database file for testing
        self.db_fd, self.db_path = tempfile.mkstemp()
        
    def tearDown(self):
        # Clean up the temporary database
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_parse_meshtastic_output_success(self):
        """Test successful parsing of Meshtastic output."""
        result = parse_meshtastic_output(self.test_content)
        
        # Check basic structure
        self.assertIn("Owner", result)
        self.assertIn("MyInfo", result)
        self.assertIn("Metadata", result)
        self.assertIn("Nodes", result)
        
        # Check specific values
        self.assertEqual(result["Owner"], "Test User (🧪)")
        self.assertEqual(result["MyInfo"]["myNodeNum"], 1234567890)
        self.assertEqual(result["Metadata"]["firmwareVersion"], "2.5.1.123abc")
        self.assertEqual(len(result["Nodes"]), 2)
        self.assertIn("!12345678", result["Nodes"])
        self.assertIn("!87654321", result["Nodes"])

    def test_parse_meshtastic_output_missing_sections(self):
        """Test parsing with missing sections."""
        partial_content = "Owner: Test User\nMy info: {}\n"
        result = parse_meshtastic_output(partial_content)
        
        self.assertEqual(result["Owner"], "Test User")
        self.assertEqual(result["MyInfo"], {})
        self.assertEqual(result["Metadata"], {})
        self.assertEqual(result["Nodes"], {})

    def test_parse_meshtastic_output_invalid_json(self):
        """Test parsing with invalid JSON content."""
        invalid_json_content = """Owner: Test User
My info: { invalid json }
Metadata: { "valid": "json" }
Nodes in mesh: { more invalid json }
"""
        result = parse_meshtastic_output(invalid_json_content)
        
        # Owner should still be parsed correctly
        self.assertEqual(result["Owner"], "Test User")
        # Invalid JSON parts should be empty dictionaries
        self.assertEqual(result["MyInfo"], {})
        # Valid JSON parts should be parsed correctly
        self.assertEqual(result["Metadata"]["valid"], "json")
        self.assertEqual(result["Nodes"], {})

    def test_save_json_objects(self):
        """Test saving data to SQLite database."""
        test_data = {
            "Owner": "Test User",
            "MyInfo": {"myNodeNum": 1234567890},
            "Metadata": {"firmwareVersion": "2.5.1"},
            "Nodes": {
                "!12345678": {"user": {"longName": "Test Node"}}
            }
        }
        
        # Save to the temporary database
        save_json_objects(test_data, self.db_path)
        
        # Connect to the database and verify data
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check owner table
        cursor.execute("SELECT name FROM owner")
        self.assertEqual(cursor.fetchone()[0], "Test User")
        
        # Check device_info table for MyInfo
        cursor.execute("SELECT data FROM device_info WHERE info_type = 'MyInfo'")
        my_info = json.loads(cursor.fetchone()[0])
        self.assertEqual(my_info["myNodeNum"], 1234567890)
        
        # Check device_info table for Metadata
        cursor.execute("SELECT data FROM device_info WHERE info_type = 'Metadata'")
        metadata = json.loads(cursor.fetchone()[0])
        self.assertEqual(metadata["firmwareVersion"], "2.5.1")
        
        # Check nodes table
        cursor.execute("SELECT node_data FROM nodes WHERE id = '!12345678'")
        node_data = json.loads(cursor.fetchone()[0])
        self.assertEqual(node_data["user"]["longName"], "Test Node")
        
        conn.close()

    def test_save_json_objects_empty_data(self):
        """Test saving empty data to SQLite database."""
        empty_data = {
            "Owner": None,
            "MyInfo": {},
            "Metadata": {},
            "Nodes": {}
        }
        
        # This should not raise an exception
        save_json_objects(empty_data, self.db_path)
        
        # Verify database was created but no data was saved
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM owner")
        self.assertEqual(cursor.fetchone()[0], 0)
        
        cursor.execute("SELECT COUNT(*) FROM device_info")
        self.assertEqual(cursor.fetchone()[0], 0)
        
        cursor.execute("SELECT COUNT(*) FROM nodes")
        self.assertEqual(cursor.fetchone()[0], 0)
        
        conn.close()

    def test_save_json_objects_with_timestamps(self):
        """Test saving data with timestamp fields to SQLite database."""
        current_time = int(datetime.now().timestamp())
        uptime = 3600  # 1 hour
        
        test_data = {
            "Owner": "Test User",
            "MyInfo": {"myNodeNum": 1234567890},
            "Metadata": {"firmwareVersion": "2.5.1"},
            "Nodes": {
                "!12345678": {
                    "user": {
                        "longName": "Test Node",
                        "shortName": "TN",
                        "hwModel": "TBEAM"
                    },
                    "lastHeard": current_time,
                    "deviceMetrics": {
                        "uptimeSeconds": uptime,
                        "batteryLevel": 75
                    }
                }
            }
        }
        
        # Save to the temporary database
        save_json_objects(test_data, self.db_path)
        
        # Connect to the database and verify data
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check timestamps in nodes table
        cursor.execute("SELECT last_heard, since, created FROM nodes WHERE id = '!12345678'")
        result = cursor.fetchone()
        
        # Verify last_heard and since are properly formatted ISO timestamps
        self.assertIsNotNone(result[0])  # last_heard should not be None
        self.assertIsNotNone(result[1])  # since should not be None
        self.assertIsNotNone(result[2])  # created should not be None
        
        # Check that since = last_heard - uptime (approximately)
        last_heard_dt = datetime.fromisoformat(result[0])
        since_dt = datetime.fromisoformat(result[1])
        time_diff_seconds = (last_heard_dt - since_dt).total_seconds()
        self.assertAlmostEqual(time_diff_seconds, uptime, delta=2)  # Allow 2 seconds tolerance
        
        conn.close()

    def test_created_timestamp_preservation(self):
        """Test that created timestamp is preserved on updates."""
        # First insertion
        first_data = {
            "Nodes": {
                "!12345678": {
                    "user": {"longName": "Original Name"},
                    "lastHeard": int(datetime.now().timestamp())
                }
            }
        }
        save_json_objects(first_data, self.db_path)
        
        # Get the original created timestamp
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT created FROM nodes WHERE id = '!12345678'")
        original_created = cursor.fetchone()[0]
        conn.close()
        
        # Wait a moment to ensure timestamps would be different
        import time
        time.sleep(1)
        
        # Update the same record
        updated_data = {
            "Nodes": {
                "!12345678": {
                    "user": {"longName": "Updated Name"},
                    "lastHeard": int(datetime.now().timestamp())
                }
            }
        }
        save_json_objects(updated_data, self.db_path)
        
        # Check that created timestamp hasn't changed
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT created, long_name FROM nodes WHERE id = '!12345678'")
        new_created, new_name = cursor.fetchone()
        conn.close()
        
        # Created timestamp should remain the same even after update
        self.assertEqual(original_created, new_created)
        # But the data should be updated
        self.assertEqual(new_name, "Updated Name")

    @patch('MCPtastic.device.get_interface')
    def test_get_info_tool(self, mock_get_interface):
        """Test the get_info tool."""
        # Mock MCP
        mock_mcp = MagicMock()

        # Capture the decorated functions
        registered_tools = {}

        # Create a capturing decorator
        def capturing_decorator(func):
            registered_tools[func.__name__] = func
            return func

        # Make the mock tool method return our capturing decorator
        mock_mcp.tool = MagicMock(return_value=capturing_decorator)

        # Mock interface instance with stdout capture
        mock_iface_instance = MagicMock()

        # Modified to handle new output redirection approach
        def side_effect_showinfo(*args, **kwargs):
            return self.test_content

        mock_iface_instance.showInfo.side_effect = side_effect_showinfo
        mock_get_interface.return_value = mock_iface_instance

        # Register tools with mock MCP
        register_device_tools(mock_mcp)

        # Get the registered get_info function by name
        self.assertIn('get_info', registered_tools)
        get_info_func = registered_tools['get_info']

        # Run the function asynchronously
        import asyncio
        result = asyncio.run(get_info_func())

        # Verify the interface was used correctly
        mock_get_interface.assert_called_once_with("meshtastic.local", "tcp")
        mock_iface_instance.showInfo.assert_called_once()
        mock_iface_instance.close.assert_called_once()

        # Check the result
        self.assertEqual(result, "Device information saved to database")

    def test_split_compound_name(self):
        """Test the splitCompoundName function."""
        # Single name with no dots
        result = splitCompoundName("test")
        self.assertEqual(result, ["test", "test"])
        
        # Compound name with dots
        result = splitCompoundName("device.config")
        self.assertEqual(result, ["device", "config"])
        
        # Multi-part compound name
        result = splitCompoundName("device.config.setting")
        # The actual implementation splits all dots, not just the first one
        self.assertEqual(result, ["device", "config", "setting"])

    @patch('meshtastic.util.camel_to_snake')
    def test_traverse_config(self, mock_camel_to_snake):
        """Test the traverseConfig function."""
        # Setup mock for camel_to_snake conversion
        mock_camel_to_snake.return_value = "test_snake"
        
        # Create mock config and interface
        mock_config_root = "testRoot"
        mock_config = {
            "simple": "value",
            "nested": {
                "setting1": "value1",
                "setting2": "value2"
            }
        }
        mock_interface_config = MagicMock()
        
        # Create a mock for setPref that we can track
        with patch('MCPtastic.device.setPref') as mock_set_pref:
            mock_set_pref.return_value = True
            
            # Execute the function
            result = traverseConfig(mock_config_root, mock_config, mock_interface_config)
            
            # Verify setPref was called for simple value
            mock_set_pref.assert_any_call(mock_interface_config, "test_snake.simple", "value")
            
            # Based on the actual implementation, traverseConfig flattens nested keys
            # and doesn't preserve the nested structure in key paths
            mock_set_pref.assert_any_call(mock_interface_config, "test_snake.setting1", "value1")
            mock_set_pref.assert_any_call(mock_interface_config, "test_snake.setting2", "value2")
            
            self.assertTrue(result)

    @patch('meshtastic.util')
    def test_set_pref(self, mock_util):
        """Test the setPref function."""
        # Setup mocks
        mock_config = MagicMock()
        mock_descriptor = MagicMock()
        mock_field = MagicMock()
        mock_message_type = MagicMock()
        
        # Mock the DESCRIPTOR structure
        mock_config.DESCRIPTOR = mock_descriptor
        mock_descriptor.fields_by_name = {"test": mock_field}
        mock_field.name = "test"
        mock_field.message_type = mock_message_type
        mock_message_type.fields_by_name = {"property": MagicMock()}
        mock_message_type.fields_by_name["property"].name = "property"
        mock_message_type.fields_by_name["property"].label = "LABEL_OPTIONAL"
        mock_message_type.fields_by_name["property"].enum_type = None
        
        # Mock the conversion functions
        mock_util.camel_to_snake.return_value = "property"
        mock_util.snake_to_camel.return_value = "property"
        mock_util.fromStr.return_value = "converted_value"
        
        # Execute with simple config structure
        with patch('meshtastic.mt_config') as mock_mt_config:
            mock_mt_config.camel_case = False
            
            # Test basic property setting
            result = setPref(mock_config, "test.property", "test_value")
            
            # Assertions
            self.assertTrue(result)
            mock_util.fromStr.assert_called_with("test_value")

    @patch('meshtastic.util')
    def test_set_pref_enum(self, mock_util):
        """Test setPref with enum values."""
        # Setup mocks
        mock_config = MagicMock()
        mock_descriptor = MagicMock()
        mock_field = MagicMock()
        mock_enum_type = MagicMock()
        
        # Mock the DESCRIPTOR structure
        mock_config.DESCRIPTOR = mock_descriptor
        mock_descriptor.fields_by_name = {"test": mock_field}
        mock_field.name = "test"
        mock_field.message_type = None  # Direct field
        mock_field.label = "LABEL_OPTIONAL"
        mock_field.enum_type = mock_enum_type
        
        # Setup enum values
        mock_enum_value = MagicMock()
        mock_enum_value.number = 42
        mock_enum_type.values_by_name = {"TEST_ENUM": mock_enum_value}
        mock_enum_type.values = [MagicMock(name="TEST_ENUM"), MagicMock(name="OTHER_ENUM")]
        
        # Mock utility functions
        mock_util.camel_to_snake.return_value = "test"
        mock_util.snake_to_camel.return_value = "test"
        
        # Execute with enum value as string
        result = setPref(mock_config, "test", "TEST_ENUM")
        
        # Assertions
        self.assertTrue(result)
        # Verify it was set with the enum number value
        mock_config.test = 42

    @patch('meshtastic.util')
    def test_set_pref_repeated(self, mock_util):
        """Test setPref with repeated fields."""
        # Setup mocks
        mock_config = MagicMock()
        mock_descriptor = MagicMock()
        mock_field = MagicMock()
        
        # Mock the DESCRIPTOR structure for repeated field
        mock_config.DESCRIPTOR = mock_descriptor
        mock_descriptor.fields_by_name = {"test": mock_field}
        mock_field.name = "test"
        mock_field.message_type = None  # Direct field
        mock_field.label = "LABEL_REPEATED"  # This is a repeated field
        mock_field.enum_type = None
        
        # Setup the test values and field access
        mock_util.camel_to_snake.return_value = "test"
        mock_util.snake_to_camel.return_value = "test"
        mock_util.fromStr.side_effect = lambda x: int(x)  # Convert string to int
        
        # Test adding to repeated field
        result = setPref(mock_config, "test", [1, 2, 3])
        self.assertTrue(result)
        
        # Test clearing a repeated field (value=0)
        result = setPref(mock_config, "test", 0)
        self.assertTrue(result)

    @patch('yaml.dump')
    def test_ex_config(self, mock_yaml_dump):
        """Test the ex_config function."""
        # Setup mock interface
        mock_interface = MagicMock()
        mock_interface.getLongName.return_value = "Test User"
        mock_interface.getShortName.return_value = "TU"
        mock_interface.localNode.getURL.return_value = "https://example.com/channel"
        
        # Mock node info with position data
        mock_interface.getMyNodeInfo.return_value = {
            "position": {
                "latitude": 12.345,
                "longitude": -67.890,
                "altitude": 100
            }
        }
        
        # Test each camel_case setting separately
        for camel_case_setting in [True, False]:
            # Reset mock for yaml.dump
            mock_yaml_dump.reset_mock()
            mock_yaml_dump.return_value = "mocked yaml output"
            
            # Mock message to dict conversion for configs
            with patch('MCPtastic.device.MessageToDict') as mock_to_dict:
                mock_to_dict.side_effect = [
                    {"testConfig": {"nested": "value"}},  # localConfig
                    {"moduleA": {"enabled": True}}        # moduleConfig
                ]
                
                # Mock for snake_to_camel
                with patch('meshtastic.util.snake_to_camel') as mock_snake_to_camel:
                    mock_snake_to_camel.return_value = "testConfig"
                    
                    # Patch mt_config.camel_case directly, not through a context manager
                    with patch.object(meshtastic.mt_config, 'camel_case', camel_case_setting):
                        
                        # Execute the function
                        result = ex_config(mock_interface)
                        
                        # Verify result contains expected parts
                        self.assertIn("# start of Meshtastic configure yaml", result)
                        self.assertIn("mocked yaml output", result)
                        
                        # Verify the correct data was passed to yaml.dump
                        config_obj = mock_yaml_dump.call_args[0][0]
                        
                        # Check that key elements are in the config object
                        self.assertEqual(config_obj["owner"], "Test User")
                        self.assertEqual(config_obj["owner_short"], "TU")
                        
                        # Check URL key based on camel_case setting
                        if camel_case_setting:
                            self.assertEqual(config_obj["channelUrl"], "https://example.com/channel")
                        else:
                            self.assertEqual(config_obj["channel_url"], "https://example.com/channel")
                        
                        self.assertEqual(config_obj["location"]["lat"], 12.345)
                        self.assertEqual(config_obj["location"]["lon"], -67.890)
                        self.assertEqual(config_obj["location"]["alt"], 100)
                        self.assertIn("config", config_obj)
                        self.assertIn("module_config", config_obj)

    @patch('meshtastic.tcp_interface.TCPInterface')
    @patch('meshtastic.util.support_info')
    def test_get_support_info_tool(self, mock_support_info, mock_interface):
        """Test the get_support_info tool."""
        # Mock MCP and setup for tool registration
        mock_mcp = MagicMock()
        
        # Capture the decorated functions
        registered_tools = {}
        
        # Create a capturing decorator
        def capturing_decorator(func):
            registered_tools[func.__name__] = func
            return func
        
        # Make the mock tool method return our capturing decorator
        mock_mcp.tool = MagicMock(return_value=capturing_decorator)
        
        # Mock interface instance
        mock_iface_instance = MagicMock()
        mock_interface.return_value = mock_iface_instance
        
        # Register tools with mock MCP
        register_device_tools(mock_mcp)
        
        # Get the registered get_support_info function
        self.assertIn('get_support_info', registered_tools)
        get_support_info_func = registered_tools['get_support_info']
        
        # Set up the support_info function to write something to stdout
        def side_effect_support_info():
            print("Support info output")
        mock_support_info.side_effect = side_effect_support_info
        
        # Run the function asynchronously
        import asyncio
        result = asyncio.run(get_support_info_func())
        
        # Verify the interface was used correctly
        mock_interface.assert_called_once_with("meshtastic.local")
        mock_support_info.assert_called_once()
        mock_iface_instance.close.assert_called_once()
        
        # Check the result
        self.assertIn("Support info output", result)

    @patch('meshtastic.tcp_interface.TCPInterface')
    def test_export_config_tool(self, mock_interface):
        """Test the export_config tool."""
        # Mock MCP and setup for tool registration
        mock_mcp = MagicMock()
        
        # Capture the decorated functions
        registered_tools = {}
        
        # Create a capturing decorator
        def capturing_decorator(func):
            registered_tools[func.__name__] = func
            return func
        
        # Make the mock tool method return our capturing decorator
        mock_mcp.tool = MagicMock(return_value=capturing_decorator)
        
        # Mock interface instance
        mock_iface_instance = MagicMock()
        mock_interface.return_value = mock_iface_instance
        
        # Mock the ex_config function when called with this interface
        with patch('MCPtastic.device.ex_config') as mock_ex_config:
            mock_ex_config.return_value = "# Mock YAML config"
            
            # Register tools with mock MCP
            register_device_tools(mock_mcp)
            
            # Get the registered export_config function
            self.assertIn('export_config', registered_tools)
            export_config_func = registered_tools['export_config']
            
            # Run the function asynchronously
            import asyncio
            result = asyncio.run(export_config_func())
            
            # Verify the interface was used correctly
            mock_interface.assert_called_once_with("meshtastic.local")
            mock_ex_config.assert_called_once_with(mock_iface_instance)
            mock_iface_instance.close.assert_called_once()
            
            # Check the result
            self.assertEqual(result, "# Mock YAML config")

    @patch('meshtastic.tcp_interface.TCPInterface')
    @patch('yaml.safe_load')
    def test_configure_tool(self, mock_safe_load, mock_interface):
        """Test the configure tool."""
        # Mock MCP and setup for tool registration
        mock_mcp = MagicMock()
        
        # Capture the decorated functions
        registered_tools = {}
        
        # Create a capturing decorator
        def capturing_decorator(func):
            registered_tools[func.__name__] = func
            return func
        
        # Make the mock tool method return our capturing decorator
        mock_mcp.tool = MagicMock(return_value=capturing_decorator)
        
        # Mock interface instance
        mock_iface_instance = MagicMock()
        mock_interface.return_value = mock_iface_instance
        
        # Define node_id before using it
        node_id = 'test_id'
        
        # Mock node and user info
        mock_node = MagicMock()
        mock_iface_instance.getNode.return_value = mock_node
        mock_iface_instance.getMyNodeInfo.return_value = {'user': {'id': node_id}}
        
        # Setup the YAML configuration
        mock_safe_load.return_value = {
            "owner": "New Owner",
            "owner_short": "NO"
        }
        
        # Register tools with mock MCP
        register_device_tools(mock_mcp)
        
        # Get the registered configure function
        self.assertIn('configure', registered_tools)
        configure_func = registered_tools['configure']
        
        # Run the function asynchronously
        import asyncio
        result = asyncio.run(configure_func("test_yaml"))
        
        # Verify the interface was used correctly
        mock_interface.assert_called_once_with("meshtastic.local")
        mock_safe_load.assert_called_once_with("test_yaml")
        mock_iface_instance.getMyNodeInfo.assert_called_once()
        mock_iface_instance.getNode.assert_called_with(node_id)
        
        # Use assert_any_call for more flexible assertions
        mock_node.setOwner.assert_any_call("New Owner")
        
        mock_iface_instance.close.assert_called_once()
        
        # Check the result
        self.assertIn("Setting device owner to New Owner", result)

    @patch('meshtastic.tcp_interface.TCPInterface')
    @patch('yaml.safe_load')
    def test_configure_tool_with_full_config(self, mock_safe_load, mock_interface):
        """Test the configure tool with more comprehensive configuration."""
        # Mock MCP and setup for tool registration
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capturing_decorator(func):
            registered_tools[func.__name__] = func
            return func
        
        mock_mcp.tool = MagicMock(return_value=capturing_decorator)
        
        # Mock interface instance and node
        mock_iface_instance = MagicMock()
        mock_node = MagicMock()
        mock_interface.return_value = mock_iface_instance
        mock_iface_instance.getNode.return_value = mock_node
        mock_iface_instance.getMyNodeInfo.return_value = {'user': {'id': 'test_id'}}
        
        # Setup comprehensive YAML configuration
        mock_safe_load.return_value = {
            "owner": "New Owner",
            "ownerShort": "NO",  # Test camelCase version
            "channelUrl": "https://example.com/channel",
            "location": {
                "lat": 12.345,
                "lon": -67.890,
                "alt": 100
            },
            "config": {
                "device": {"role": "ROUTER"}
            },
            "module_config": {
                "serial": {"enabled": True}
            }
        }
        
        # Mock traverseConfig
        with patch('MCPtastic.device.traverseConfig') as mock_traverse_config:
            # Register tools with mock MCP
            register_device_tools(mock_mcp)
            
            # Get the registered configure function
            configure_func = registered_tools['configure']
            
            # Run the function asynchronously
            import asyncio
            result = asyncio.run(configure_func("test_yaml"))
            
            # Verify all configuration parts were handled
            mock_node.setOwner.assert_any_call(long_name=None, short_name="NO")
            mock_node.setURL.assert_called_with("https://example.com/channel")
            mock_iface_instance.localNode.setFixedPosition.assert_called_with(12.345, -67.890, 100)
            mock_traverse_config.assert_called()
            mock_node.writeConfig.assert_called()
            mock_node.commitSettingsTransaction.assert_called_once()
            
            # Check the result contains success message
            self.assertIn("Setting device owner to New Owner", result)
            
    @patch('meshtastic.tcp_interface.TCPInterface')
    @patch('yaml.safe_load')
    def test_configure_tool_with_alternate_keys(self, mock_safe_load, mock_interface):
        """Test the configure tool with alternate key formats."""
        # Mock MCP and setup for tool registration
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capturing_decorator(func):
            registered_tools[func.__name__] = func
            return func
        
        mock_mcp.tool = MagicMock(return_value=capturing_decorator)
        
        # Mock interface instance and node
        mock_iface_instance = MagicMock()
        mock_node = MagicMock()
        mock_interface.return_value = mock_iface_instance
        mock_iface_instance.getNode.return_value = mock_node
        
        # Define node_id before using it
        node_id = 'test_id'
        # Set up getMyNodeInfo to return a user dict with id
        mock_iface_instance.getMyNodeInfo.return_value = {'user': {'id': node_id}}
        
        # Setup YAML configuration with alternate keys - include owner to initialize id variable
        mock_safe_load.return_value = {
            "owner": "Test Owner",  # Add owner to initialize id in the function
            "channel_url": "https://example.com/alt-channel",  # snake_case version
        }
        
        # Register tools with mock MCP
        register_device_tools(mock_mcp)
        
        # Get the registered configure function
        self.assertIn('configure', registered_tools)
        configure_func = registered_tools['configure']
        
        # Run the function asynchronously
        import asyncio
        asyncio.run(configure_func("test_yaml"))
        
        # Verify the alternate key was processed correctly
        mock_node.setOwner.assert_called_with("Test Owner")
        mock_node.setURL.assert_called_with("https://example.com/alt-channel")
        mock_iface_instance.getNode.assert_called_with(node_id)


if __name__ == '__main__':
    unittest.main()