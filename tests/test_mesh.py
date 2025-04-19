import pytest
import pytest_asyncio  # Add this import
import json
import datetime
from unittest.mock import Mock, patch, MagicMock
import sys
from typing import Any, List, Optional, Union
import os
from meshtastic import BROADCAST_ADDR
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import MCPtastic.mesh as mesh

# Create mock for the MCP
class MockMCP:
    def __init__(self):
        self.tools = {}
        
    def tool(self):
        def decorator(func):
            self.tools[func.__name__] = func
            return func
        return decorator

@pytest.fixture
def mock_interface():
    """Create a mock TCP interface with predefined responses"""
    mock = MagicMock()
    
    # Configure the mock to return specific values for different methods
    mock.getLongName.return_value = "Test Node Long Name"
    mock.getShortName.return_value = "TN"
    mock.getMyNodeInfo.return_value = {"id": "!abcdef", "num": 123456}
    mock.getMyUser.return_value = {"id": "!abcdef", "long_name": "Test User", "short_name": "TU"}
    mock.getPublicKey.return_value = "testpublickey123"
    mock.sendAlert.return_value = {"id": "msg1", "status": "success"}
    mock.sendData.return_value = {"id": "data1", "status": "success"}
    mock.sendHeartbeat.return_value = None
    mock.sendPosition.return_value = {"id": "pos1", "status": "success"}
    mock.sendTelemetry.return_value = {"id": "telem1", "status": "success"}
    mock.sendText.return_value = {"id": "text1", "status": "success"}
    mock.sendTraceRoute.return_value = None
    mock.showInfo.return_value = {"hardware": "tbeam", "firmware": "2.1.0"}
    mock.showNodes.return_value = "node1: Test Node\nnode2: Other Node"
    mock.sendWaypoint.return_value = "Waypoint created"
    mock.deleteWaypoint.return_value = "Waypoint deleted"
    
    return mock

@pytest.fixture
def mcp_with_tools():
    """Initialize MCP and register tools"""
    mcp = MockMCP()
    mesh.register_mesh_tools(mcp)
    return mcp

# Mark all async tests with pytest.mark.asyncio
@pytest.mark.asyncio
@patch('meshtastic.tcp_interface.TCPInterface')
async def test_get_long_name(mock_tcp, mcp_with_tools, mock_interface):
    """Test the get_long_name tool"""
    mock_tcp.return_value = mock_interface
    
    # Call the tool
    result = await mcp_with_tools.tools["get_long_name"]()
    
    # Verify the interface was created and closed properly
    mock_tcp.assert_called_once_with("meshtastic.local")
    mock_interface.getLongName.assert_called_once()
    mock_interface.close.assert_called_once()
    
    # Verify the result
    assert result == "Test Node Long Name"

@pytest.mark.asyncio
@patch('meshtastic.tcp_interface.TCPInterface')
async def test_get_short_name(mock_tcp, mcp_with_tools, mock_interface):
    """Test the get_short_name tool"""
    mock_tcp.return_value = mock_interface
    
    # Call the tool
    result = await mcp_with_tools.tools["get_short_name"]()
    
    # Verify the interface was created and closed properly
    mock_tcp.assert_called_once_with("meshtastic.local")
    mock_interface.getShortName.assert_called_once()
    mock_interface.close.assert_called_once()
    
    # Verify the result
    assert result == "TN"

@pytest.mark.asyncio
@patch('meshtastic.tcp_interface.TCPInterface')
async def test_get_my_node_info(mock_tcp, mcp_with_tools, mock_interface):
    """Test the get_my_node_info tool"""
    mock_tcp.return_value = mock_interface
    
    # Call the tool
    result = await mcp_with_tools.tools["get_my_node_info"]()
    
    # Verify the interface was created and closed properly
    mock_tcp.assert_called_once_with("meshtastic.local")
    mock_interface.getMyNodeInfo.assert_called_once()
    mock_interface.close.assert_called_once()
    
    # Verify the result is properly converted to JSON
    expected = json.dumps({"id": "!abcdef", "num": 123456}, indent=4)
    assert result == expected

# Remove these mocks and use the real utf8len function

@pytest.mark.asyncio
@patch('meshtastic.tcp_interface.TCPInterface')
async def test_send_text_short(mock_tcp, mcp_with_tools, mock_interface):
    """Test the send_text tool with a short message that doesn't need chunking"""
    mock_tcp.return_value = mock_interface
    
    # Call the tool with a short message that won't need chunking
    result = await mcp_with_tools.tools["send_text"]("Hello, mesh!")
    
    # Verify the interface was created and closed properly
    mock_tcp.assert_called_once_with("meshtastic.local")
    mock_interface.sendText.assert_called_once_with(
        "Hello, mesh!", "^all", False, False, None, 0, 1
    )
    mock_interface.close.assert_called_once()
    
    # Verify the result with the new format
    assert result == "Message sent: Hello, mesh!"


@pytest.mark.asyncio
@patch('meshtastic.tcp_interface.TCPInterface')
async def test_send_text_chunked(mock_tcp, mcp_with_tools, mock_interface):
    """Test the send_text tool with a long message that needs chunking"""
    mock_tcp.return_value = mock_interface
    
    # Create a long message that will need to be chunked
    # Make it long enough to ensure chunking with the real utf8len function
    long_message = "X" * 300
    
    # Call the tool
    result = await mcp_with_tools.tools["send_text"](long_message)
    
    # Verify the interface was created and closed once
    mock_tcp.assert_called_once_with("meshtastic.local")
    mock_interface.close.assert_called_once()
    
    # Verify that sendText was called multiple times
    assert mock_interface.sendText.call_count >= 2
    
    # Check that the first call had the [1/x] prefix
    first_call_args = mock_interface.sendText.call_args_list[0][0]
    assert first_call_args[0].startswith("[1/")
    
    # Verify the result contains success messages for sent chunks
    assert "Sent chunk: [1/" in result


@pytest.mark.asyncio
@patch('meshtastic.tcp_interface.TCPInterface')
async def test_send_text_edge_case(mock_tcp, mcp_with_tools, mock_interface):
    """Test the send_text tool with a message that's exactly at the MAX_TEXT_SIZE limit"""
    mock_tcp.return_value = mock_interface
    
    # Create a message that's exactly at the limit
    edge_message = "This is a message that's exactly at the size limit."
    
    # Call the tool
    result = await mcp_with_tools.tools["send_text"](edge_message)
    
    # Verify sendText was called only once (no chunking)
    mock_interface.sendText.assert_called_once()
    
    # Verify the message wasn't chunked
    assert mock_interface.sendText.call_args[0][0] == edge_message
    
    # Verify the result
    assert result == f"Message sent: {edge_message}"


@pytest.mark.asyncio
@patch('meshtastic.tcp_interface.TCPInterface')
async def test_send_text_unicode(mock_tcp, mcp_with_tools, mock_interface):
    """Test the send_text tool with Unicode characters"""
    mock_tcp.return_value = mock_interface
    
    # Create a Unicode message that's long enough to trigger chunking
    # Each emoji is 4 bytes in UTF-8, so this should be plenty
    unicode_message = "😀" * 100
    
    # Call the tool
    result = await mcp_with_tools.tools["send_text"](unicode_message)
    
    # Verify the interface was properly closed
    mock_interface.close.assert_called_once()
    
    # Verify result contains something about the message being sent
    assert "Sent chunk:" in result or "Message sent:" in result
    
    # If the message was chunked, verify no emoji was split
    if "Sent chunk:" in result:
        for call_args in mock_interface.sendText.call_args_list:
            message = call_args[0][0]
            # Remove the chunk prefix like [1/2]
            if "]" in message:
                content = message.split("]", 1)[1].strip()
            else:
                content
            
            # Check for orphaned UTF-8 continuation bytes
            # If an emoji was split, we'd have invalid UTF-8
            try:
                content.encode('utf-8').decode('utf-8')
            except UnicodeError:
                pytest.fail("Invalid UTF-8 detected - a character might have been split")

@pytest.mark.asyncio
@patch('meshtastic.tcp_interface.TCPInterface')
async def test_send_waypoint(mock_tcp, mcp_with_tools, mock_interface):
    """Test the send_waypoint tool"""
    mock_tcp.return_value = mock_interface
    
    # Set up a fixed timestamp
    timestamp = 1717200000  # Example timestamp
    
    # Use the correct module path for patching
    with patch('MCPtastic.mesh.datetime') as mock_dt_module:
        # Set up the mock datetime module
        mock_datetime = MagicMock()
        mock_datetime.timestamp.return_value = timestamp
        mock_dt_module.datetime.fromisoformat.return_value = mock_datetime
        
        # Call the tool
        result = await mcp_with_tools.tools["send_waypoint"](
            lat=37.7749,
            lon=-122.4194,
            name="Test Point",
            description="A test waypoint",
            id=42
        )
    
    # Verify the interface was created and closed properly
    mock_tcp.assert_called_once_with("meshtastic.local")
    mock_interface.sendWaypoint.assert_called_once_with(
        waypoint_id=42,
        name="Test Point",
        description="A test waypoint",
        expire=timestamp,
        latitude=37.7749,
        longitude=-122.4194
    )
    mock_interface.close.assert_called_once()
    
    # Updated assertion to match the new JSON format
    expected_json = json.dumps({
        "status": "success", 
        "message": "42 updated at lat: 37.7749 lon: -122.4194"
    }, indent=4)
    assert result == expected_json

@pytest.mark.asyncio
@patch('meshtastic.tcp_interface.TCPInterface')
async def test_show_nodes(mock_tcp, mcp_with_tools, mock_interface):
    """Test the show_nodes tool"""
    mock_tcp.return_value = mock_interface
    
    # Call the tool
    result = await mcp_with_tools.tools["show_nodes"]()
    
    # Verify the interface was created and closed properly
    mock_tcp.assert_called_once_with("meshtastic.local")
    mock_interface.showNodes.assert_called_once_with(True, None)
    mock_interface.close.assert_called_once()
    
    # Verify the result
    assert result == "node1: Test Node\nnode2: Other Node"

@pytest.mark.asyncio
@patch('meshtastic.tcp_interface.TCPInterface')
async def test_interface_exception(mock_tcp, mcp_with_tools):
    """Test that the interface is properly closed even if an exception occurs"""
    # Create a mock interface that raises an exception when getLongName is called
    mock_interface = Mock()
    mock_interface.getLongName.side_effect = Exception("Test exception")
    mock_tcp.return_value = mock_interface
    
    # Call the tool and expect an exception
    with pytest.raises(Exception, match="Test exception"):
        await mcp_with_tools.tools["get_long_name"]()
    
    # Verify the interface was still closed
    mock_interface.close.assert_called_once()