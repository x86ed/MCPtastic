import unittest
import json
import sqlite3
import os
from datetime import datetime
from unittest.mock import MagicMock, patch
import tempfile

# Import the module to test
from MCPtastic.device import parse_meshtastic_output, save_json_objects, register_device_tools

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
      "shortName": "Test"
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

    @patch('meshtastic.tcp_interface.TCPInterface')
    def test_get_info_tool(self, mock_interface):
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
        mock_interface.return_value = mock_iface_instance
        
        # Register tools with mock MCP
        register_device_tools(mock_mcp)
        
        # Get the registered get_info function by name
        self.assertIn('get_info', registered_tools)
        get_info_func = registered_tools['get_info']
        
        # Run the function asynchronously
        import asyncio
        result = asyncio.run(get_info_func())
        
        # Verify the interface was used correctly
        mock_interface.assert_called_once_with("meshtastic.local")
        mock_iface_instance.showInfo.assert_called_once()
        mock_iface_instance.close.assert_called_once()
        
        # Check the result
        self.assertEqual(result, "Device information saved to database")

    @patch('meshtastic.tcp_interface.TCPInterface')
    def test_set_owner_tool(self, mock_interface):
        """Test the set_owner tool."""
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
        
        # Mock interface instance
        mock_iface_instance = MagicMock()
        mock_local_node = MagicMock()
        mock_iface_instance.localNode = mock_local_node
        mock_interface.return_value = mock_iface_instance
        
        # Register tools with mock MCP
        register_device_tools(mock_mcp)
        
        # Get the registered set_owner function by name
        self.assertIn('set_owner', registered_tools)
        set_owner_func = registered_tools['set_owner']
        
        # Run the function asynchronously
        import asyncio
        result = asyncio.run(set_owner_func("Long Name", "LN"))
        
        # Verify the interface was used correctly
        mock_interface.assert_called_once_with("meshtastic.local")
        mock_local_node.setOwner.assert_called_once_with("Long Name", "LN")
        mock_iface_instance.close.assert_called_once()
        
        # Check the result
        self.assertEqual(result, "Owner set successfully")


if __name__ == '__main__':
    unittest.main()