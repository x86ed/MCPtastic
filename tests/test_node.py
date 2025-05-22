import pytest
import pytest_asyncio
import json
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import sys
import os

# Add parent directory to path to enable local imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from MCPtastic.node import register_node_tools, _get_node_object
from MCPtastic.interface_manager import InterfaceManager
from meshtastic.node import Node
from meshtastic.config_pb2 import Config # For channel roles, etc.
from meshtastic import MeshtasticInterface # Base interface type for mocking

# Mock MCP class (as in test_mesh.py)
class MockMCP:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def decorator(func):
            # Store the async function directly
            self.tools[func.__name__] = func
            return func
        return decorator

@pytest.fixture
def mock_mcp_object() -> MockMCP:
    """Fixture for a mocked MCP object."""
    return MockMCP()

@pytest.fixture
def mock_iface_manager() -> MagicMock:
    """Fixture for a mocked InterfaceManager."""
    manager = MagicMock(spec=InterfaceManager)
    manager.get_interface = MagicMock() # This will be configured per test
    return manager

@pytest.fixture
def mock_meshtastic_interface() -> MagicMock:
    """Fixture for a mocked MeshtasticInterface."""
    iface = MagicMock(spec=MeshtasticInterface) # Use base spec
    iface.localNode = MagicMock(spec=Node)
    iface.nodes = MagicMock(spec=dict) # To store remote nodes
    # Mock common interface methods that might be called by _get_node_object or tools
    iface.getLongName = MagicMock(return_value="Mock Local LongName")
    iface.getShortName = MagicMock(return_value="MLN")
    iface.myInfo = {"num": 123, "id": "!localNodeId"}
    iface.localNode.localConfig = MagicMock() # Mock nested attributes
    iface.localNode.moduleConfig = MagicMock()
    iface.localNode.channels = []
    return iface

@pytest.fixture
def mock_local_node(mock_meshtastic_interface: MagicMock) -> MagicMock:
    """Fixture for a mocked local Node object, linked to the mock_interface."""
    node = mock_meshtastic_interface.localNode
    node.nodeId = "!localNodeId" # Standardize local node ID for tests
    # Add methods that will be called by tools
    node.showChannels = MagicMock()
    node.showInfo = MagicMock() # This is more of a CLI print method, data is usually from config
    node.setOwner = AsyncMock() # meshtastic node methods can be async
    node.reboot = AsyncMock()
    node.shutdown = AsyncMock()
    node.factoryReset = AsyncMock()
    # Mock config attributes often used by show_info for local node
    node.localConfig = MagicMock(spec=Config.LocalConfig)
    node.moduleConfig = MagicMock(spec=Config.ModuleConfig)
    node.channels = [] # Example: list of channel settings
    # Simulate user attribute for setOwner
    node.user = MagicMock()
    node.user.long_name = "Initial Local Long"
    node.user.short_name = "ILL"
    return node

@pytest.fixture
def mock_remote_node() -> MagicMock:
    """Fixture for a mocked remote Node object."""
    node = MagicMock(spec=Node)
    node.nodeId = "!remoteNodeId"
    node.longName = "Mock Remote LongName"
    node.shortName = "MRN"
    node.hwModel = "T-BEAM"
    node.isRouter = False
    node.isMqttEnabled = True
    # Add methods that will be called by tools
    node.showChannels = MagicMock()
    node.showInfo = MagicMock()
    node.setOwner = AsyncMock()
    node.reboot = AsyncMock()
    node.shutdown = AsyncMock()
    node.factoryReset = AsyncMock()
    # Remote nodes typically have 'settings' for channels if populated
    node.settings = MagicMock(spec=Config) 
    node.settings.channel_settings = []
    # Simulate user attribute for setOwner
    node.user = MagicMock()
    node.user.long_name = "Initial Remote Long"
    node.user.short_name = "IRL"
    return node

@pytest.fixture
def registered_node_tools(mock_mcp_object: MockMCP, mock_iface_manager: MagicMock) -> MockMCP:
    """Fixture to register node tools with the mocked MCP object."""
    register_node_tools(mock_mcp_object, mock_iface_manager)
    return mock_mcp_object


# --- Test Cases Start Here ---

# Tests for _get_node_object (helper function, but good to test its logic)
@pytest.mark.asyncio
async def test_get_node_object_local(mock_iface_manager: MagicMock, mock_meshtastic_interface: MagicMock, mock_local_node: MagicMock):
    mock_iface_manager.get_interface.return_value = mock_meshtastic_interface
    mock_meshtastic_interface.localNode = mock_local_node
    
    node = await _get_node_object(mock_iface_manager, "local")
    assert node == mock_local_node
    mock_iface_manager.get_interface.assert_called_once()

@pytest.mark.asyncio
async def test_get_node_object_remote(mock_iface_manager: MagicMock, mock_meshtastic_interface: MagicMock, mock_remote_node: MagicMock):
    mock_iface_manager.get_interface.return_value = mock_meshtastic_interface
    mock_meshtastic_interface.nodes = {mock_remote_node.nodeId: mock_remote_node}
    
    node = await _get_node_object(mock_iface_manager, mock_remote_node.nodeId)
    assert node == mock_remote_node
    mock_iface_manager.get_interface.assert_called_once()

@pytest.mark.asyncio
async def test_get_node_object_remote_not_found(mock_iface_manager: MagicMock, mock_meshtastic_interface: MagicMock):
    mock_iface_manager.get_interface.return_value = mock_meshtastic_interface
    mock_meshtastic_interface.nodes = {} # Empty nodes
    
    node = await _get_node_object(mock_iface_manager, "!nonExistentId")
    assert node is None
    mock_iface_manager.get_interface.assert_called_once()

@pytest.mark.asyncio
async def test_get_node_object_no_interface_attempts_connect(mock_iface_manager: MagicMock, mock_meshtastic_interface: MagicMock, mock_local_node: MagicMock):
    # Simulate no interface initially, then successful connection
    mock_iface_manager.get_interface.return_value = None
    
    # Patch 'asyncio.to_thread' which is used by _get_node_object for set_interface
    with patch('asyncio.to_thread', new_callable=AsyncMock) as mock_to_thread:
        # Simulate set_interface returning the mock_meshtastic_interface
        mock_to_thread.return_value = mock_meshtastic_interface
        mock_meshtastic_interface.localNode = mock_local_node

        node = await _get_node_object(mock_iface_manager, "local")
        
        assert node == mock_local_node
        mock_iface_manager.get_interface.assert_called_once() # First call returns None
        mock_to_thread.assert_called_once_with(mock_iface_manager.set_interface, "meshtastic.local", "tcp")

@pytest.mark.asyncio
async def test_get_node_object_no_interface_connect_fails(mock_iface_manager: MagicMock):
    mock_iface_manager.get_interface.return_value = None
    with patch('asyncio.to_thread', new_callable=AsyncMock) as mock_to_thread:
        mock_to_thread.return_value = None # Simulate connection failure

        with pytest.raises(Exception, match="Failed to connect to a Meshtastic interface."):
            await _get_node_object(mock_iface_manager, "local")
        
        mock_iface_manager.get_interface.assert_called_once()
        mock_to_thread.assert_called_once_with(mock_iface_manager.set_interface, "meshtastic.local", "tcp")

# --- Tests for show_channels ---
@pytest.mark.asyncio
async def test_show_channels_local_node(registered_node_tools: MockMCP, mock_iface_manager: MagicMock, mock_meshtastic_interface: MagicMock, mock_local_node: MagicMock):
    mock_iface_manager.get_interface.return_value = mock_meshtastic_interface
    
    # Simulate channel data directly on localNode.channels
    ch_setting_mock = MagicMock()
    # To make meshtastic.util.MessageToJson work, it needs a _fields attribute or be a real protobuf Message
    # For simplicity, mock its output if it's too complex to simulate MessageToJson behavior fully
    mock_local_node.channels = [ch_setting_mock]
    
    with patch('meshtastic.util.MessageToJson', return_value='{"psk": "SECRET", "name": "Local Primary"}') as mock_msg_to_json:
        result_str = await registered_node_tools.tools["show_channels"](nodeId="local")
    
    result = json.loads(result_str)
    assert result["status"] == "success"
    assert result["nodeId"] == "local"
    assert len(result["channels"]) == 1
    assert result["channels"][0] == {"psk": "SECRET", "name": "Local Primary"}
    mock_msg_to_json.assert_called_once_with(ch_setting_mock)
    # Ensure _get_node_object was implicitly called and worked
    mock_iface_manager.get_interface.assert_called_once()

@pytest.mark.asyncio
async def test_show_channels_remote_node_from_settings(registered_node_tools: MockMCP, mock_iface_manager: MagicMock, mock_meshtastic_interface: MagicMock, mock_remote_node: MagicMock):
    mock_iface_manager.get_interface.return_value = mock_meshtastic_interface
    mock_meshtastic_interface.nodes = {mock_remote_node.nodeId: mock_remote_node}
    
    ch_setting_mock = MagicMock()
    mock_remote_node.settings.channel_settings = [ch_setting_mock] # Channels in remote node settings
    mock_remote_node.channels = [] # Ensure it doesn't use this one by mistake

    with patch('meshtastic.util.MessageToJson', return_value='{"psk": "SECRET_REMOTE", "name": "Remote Channel"}') as mock_msg_to_json:
        result_str = await registered_node_tools.tools["show_channels"](nodeId=mock_remote_node.nodeId)
        
    result = json.loads(result_str)
    assert result["status"] == "success"
    assert result["nodeId"] == mock_remote_node.nodeId
    assert len(result["channels"]) == 1
    assert result["channels"][0] == {"psk": "SECRET_REMOTE", "name": "Remote Channel"}
    mock_msg_to_json.assert_called_once_with(ch_setting_mock)

@pytest.mark.asyncio
async def test_show_channels_remote_node_via_showChannels_method(registered_node_tools: MockMCP, mock_iface_manager: MagicMock, mock_meshtastic_interface: MagicMock, mock_remote_node: MagicMock):
    mock_iface_manager.get_interface.return_value = mock_meshtastic_interface
    mock_meshtastic_interface.nodes = {mock_remote_node.nodeId: mock_remote_node}
    
    # Make it so that .settings.channel_settings is empty, forcing a call to node.showChannels()
    mock_remote_node.settings.channel_settings = [] 
    mock_remote_node.channels = []
    mock_remote_node.localConfig = None # ensure this path isn't taken

    # Mock the return value of node.showChannels()
    # This method in meshtastic-python already returns a list of dicts (protobufs converted)
    mock_remote_node.showChannels.return_value = [{"name": "Remote Chan Via Method", "psk": "..."}]

    with patch('asyncio.to_thread', new_callable=AsyncMock) as mock_to_thread:
        mock_to_thread.return_value = mock_remote_node.showChannels.return_value # Simulate running showChannels in a thread
        result_str = await registered_node_tools.tools["show_channels"](nodeId=mock_remote_node.nodeId)
        
    result = json.loads(result_str)
    assert result["status"] == "success"
    assert result["nodeId"] == mock_remote_node.nodeId
    assert result["channels"] == [{"name": "Remote Chan Via Method", "psk": "..."}]
    mock_remote_node.showChannels.assert_called_once() # Verify the method was called
    mock_to_thread.assert_called_once_with(mock_remote_node.showChannels)


@pytest.mark.asyncio
async def test_show_channels_node_not_found(registered_node_tools: MockMCP, mock_iface_manager: MagicMock, mock_meshtastic_interface: MagicMock):
    mock_iface_manager.get_interface.return_value = mock_meshtastic_interface
    mock_meshtastic_interface.nodes = {} # No nodes
    
    result_str = await registered_node_tools.tools["show_channels"](nodeId="!nonExistent")
    result = json.loads(result_str)
    assert result["status"] == "error"
    assert "Node !nonExistent not found" in result["message"]

@pytest.mark.asyncio
async def test_show_channels_exception(registered_node_tools: MockMCP, mock_iface_manager: MagicMock, mock_meshtastic_interface: MagicMock, mock_local_node: MagicMock):
    mock_iface_manager.get_interface.return_value = mock_meshtastic_interface
    mock_local_node.channels = None # cause an issue
    mock_local_node.settings = None 
    mock_local_node.localConfig = None
    mock_local_node.showChannels.side_effect = Exception("Channels boom!")

    # Need to mock to_thread if showChannels is called, which it will be as a fallback
    with patch('asyncio.to_thread', new_callable=AsyncMock) as mock_to_thread:
        mock_to_thread.side_effect = Exception("Channels boom!")
        result_str = await registered_node_tools.tools["show_channels"](nodeId="local")
    
    result = json.loads(result_str)
    assert result["status"] == "error"
    assert "Channels boom!" in result["message"]

# --- Tests for show_info ---
@pytest.mark.asyncio
async def test_show_info_local_node(registered_node_tools: MockMCP, mock_iface_manager: MagicMock, mock_meshtastic_interface: MagicMock, mock_local_node: MagicMock):
    mock_iface_manager.get_interface.return_value = mock_meshtastic_interface
    
    # Mocking MessageToJson as it's used extensively
    def mock_message_to_json(message_obj):
        if message_obj == mock_local_node.localConfig:
            return {"local_config_key": "value"}
        if message_obj == mock_local_node.moduleConfig:
            return {"module_config_key": "value"}
        if isinstance(message_obj, MagicMock) and hasattr(message_obj, '_is_channel_mock_'): # crude check for channel
             return {"channel_data": "mocked"}
        return {}

    with patch('meshtastic.util.MessageToJson', side_effect=mock_message_to_json) as mock_msg_to_json:
        # Add a mock channel to localNode.channels to test that part
        channel_mock = MagicMock()
        channel_mock._is_channel_mock_ = True # Mark it for our mock_message_to_json
        mock_local_node.channels = [channel_mock]
        
        result_str = await registered_node_tools.tools["show_info"](nodeId="local")

    result = json.loads(result_str)
    assert result["status"] == "success"
    assert result["nodeId"] == "local"
    assert result["info"]["myNodeInfo"] == mock_meshtastic_interface.myInfo
    assert result["info"]["localConfig"] == {"local_config_key": "value"}
    assert result["info"]["moduleConfig"] == {"module_config_key": "value"}
    assert len(result["info"]["channels"]) == 1
    assert result["info"]["channels"][0] == {"channel_data": "mocked"}
    
    # Verify MessageToJson was called for localConfig, moduleConfig, and channels
    assert any(call_args[0][0] == mock_local_node.localConfig for call_args in mock_msg_to_json.call_args_list)
    assert any(call_args[0][0] == mock_local_node.moduleConfig for call_args in mock_msg_to_json.call_args_list)
    assert any(call_args[0][0] == channel_mock for call_args in mock_msg_to_json.call_args_list)


@pytest.mark.asyncio
async def test_show_info_remote_node_basic(registered_node_tools: MockMCP, mock_iface_manager: MagicMock, mock_meshtastic_interface: MagicMock, mock_remote_node: MagicMock):
    mock_iface_manager.get_interface.return_value = mock_meshtastic_interface
    mock_meshtastic_interface.nodes = {mock_remote_node.nodeId: mock_remote_node}

    # Simulate no localConfig or moduleConfig on remote node to hit the "basic" path
    mock_remote_node.localConfig = None
    mock_remote_node.moduleConfig = None
    mock_remote_node.channels = [] # also no direct channels attribute
    mock_remote_node.settings.channel_settings = [] # and no settings channels

    result_str = await registered_node_tools.tools["show_info"](nodeId=mock_remote_node.nodeId)
    result = json.loads(result_str)
    
    assert result["status"] == "success"
    assert result["nodeId"] == mock_remote_node.nodeId
    assert result["info"]["nodeID"] == mock_remote_node.nodeId
    assert result["info"]["longName"] == mock_remote_node.longName
    assert result["info"]["shortName"] == mock_remote_node.shortName
    assert result["info"]["hwModel"] == mock_remote_node.hwModel

@pytest.mark.asyncio
async def test_show_info_node_not_found(registered_node_tools: MockMCP, mock_iface_manager: MagicMock, mock_meshtastic_interface: MagicMock):
    mock_iface_manager.get_interface.return_value = mock_meshtastic_interface
    mock_meshtastic_interface.nodes = {}
    
    result_str = await registered_node_tools.tools["show_info"](nodeId="!nonExistent")
    result = json.loads(result_str)
    assert result["status"] == "error"
    assert "Node !nonExistent not found" in result["message"]

@pytest.mark.asyncio
async def test_show_info_exception(registered_node_tools: MockMCP, mock_iface_manager: MagicMock, mock_meshtastic_interface: MagicMock, mock_local_node: MagicMock):
    mock_iface_manager.get_interface.return_value = mock_meshtastic_interface
    # Cause an error by making an expected attribute something that MessageToJson will fail on
    mock_local_node.localConfig = "not a protobuf" 
    
    with patch('meshtastic.util.MessageToJson', side_effect=TypeError("Can't convert this")):
        result_str = await registered_node_tools.tools["show_info"](nodeId="local")
        
    result = json.loads(result_str)
    assert result["status"] == "error"
    assert "Can't convert this" in result["message"] # Or whatever the actual exception is

# --- Tests for set_owner ---
@pytest.mark.asyncio
async def test_set_owner_local_node(registered_node_tools: MockMCP, mock_iface_manager: MagicMock, mock_meshtastic_interface: MagicMock, mock_local_node: MagicMock):
    mock_iface_manager.get_interface.return_value = mock_meshtastic_interface
    
    # Mock iface.setOwner directly as it's called for local node
    mock_meshtastic_interface.setOwner = AsyncMock()

    with patch('asyncio.to_thread', new_callable=AsyncMock) as mock_to_thread:
        mock_to_thread.return_value = None # Simulate successful run in thread
        result_str = await registered_node_tools.tools["set_owner"](long_name="New Owner", short_name="NO", is_licensed=True, nodeId="local")
    
    result = json.loads(result_str)
    assert result["status"] == "success"
    assert result["nodeId"] == "local"
    assert "Owner set to Long: New Owner, Short: NO, Licensed: True" in result["message"]
    
    mock_to_thread.assert_called_once()
    # The actual call to setOwner is inside the to_thread wrapper
    # We can check the arguments passed to to_thread's first argument (the function)
    # This is a bit indirect. A cleaner way might be to mock the specific 'iface.setOwner'
    assert mock_to_thread.call_args[0][0] == mock_meshtastic_interface.setOwner
    # And check the args passed to that function
    mock_meshtastic_interface.setOwner.assert_called_once_with("New Owner", "NO", True)


@pytest.mark.asyncio
async def test_set_owner_remote_node(registered_node_tools: MockMCP, mock_iface_manager: MagicMock, mock_meshtastic_interface: MagicMock, mock_remote_node: MagicMock):
    mock_iface_manager.get_interface.return_value = mock_meshtastic_interface
    mock_meshtastic_interface.nodes = {mock_remote_node.nodeId: mock_remote_node}
    
    with patch('asyncio.to_thread', new_callable=AsyncMock) as mock_to_thread:
        mock_to_thread.return_value = None # Simulate successful run in thread
        result_str = await registered_node_tools.tools["set_owner"](long_name="Remote New", short_name="RN", nodeId=mock_remote_node.nodeId)

    result = json.loads(result_str)
    assert result["status"] == "success"
    assert result["nodeId"] == mock_remote_node.nodeId
    assert "Owner set to Long: Remote New, Short: RN" in result["message"]
    
    mock_to_thread.assert_called_once()
    assert mock_to_thread.call_args[0][0] == mock_remote_node.setOwner
    mock_remote_node.setOwner.assert_called_once_with("Remote New", "RN", False) # is_licensed defaults to False

@pytest.mark.asyncio
async def test_set_owner_use_existing_names(registered_node_tools: MockMCP, mock_iface_manager: MagicMock, mock_meshtastic_interface: MagicMock, mock_local_node: MagicMock):
    mock_iface_manager.get_interface.return_value = mock_meshtastic_interface
    mock_meshtastic_interface.setOwner = AsyncMock() # Mock the actual setOwner on the interface

    # Simulate existing names being fetched
    mock_meshtastic_interface.getLongName.return_value = "Existing Long"
    mock_meshtastic_interface.getShortName.return_value = "ExS"

    with patch('asyncio.to_thread', new_callable=AsyncMock) as mock_to_thread:
        await registered_node_tools.tools["set_owner"](is_licensed=True, nodeId="local") # No names provided

    # Check that setOwner was called with existing names
    mock_to_thread.assert_called_once()
    assert mock_to_thread.call_args[0][0] == mock_meshtastic_interface.setOwner
    mock_meshtastic_interface.setOwner.assert_called_once_with("Existing Long", "ExS", True)


@pytest.mark.asyncio
async def test_set_owner_node_not_found(registered_node_tools: MockMCP, mock_iface_manager: MagicMock, mock_meshtastic_interface: MagicMock):
    mock_iface_manager.get_interface.return_value = mock_meshtastic_interface
    mock_meshtastic_interface.nodes = {}
    
    result_str = await registered_node_tools.tools["set_owner"](long_name="Test", nodeId="!nonExistent")
    result = json.loads(result_str)
    assert result["status"] == "error"
    assert "Node !nonExistent not found" in result["message"]

@pytest.mark.asyncio
async def test_set_owner_exception(registered_node_tools: MockMCP, mock_iface_manager: MagicMock, mock_meshtastic_interface: MagicMock, mock_local_node: MagicMock):
    mock_iface_manager.get_interface.return_value = mock_meshtastic_interface
    mock_meshtastic_interface.setOwner = AsyncMock(side_effect=Exception("SetOwner failed"))

    with patch('asyncio.to_thread', new_callable=AsyncMock) as mock_to_thread:
        mock_to_thread.side_effect = Exception("SetOwner failed") # Simulate exception during the threaded call
        result_str = await registered_node_tools.tools["set_owner"](long_name="Test", nodeId="local")
        
    result = json.loads(result_str)
    assert result["status"] == "error"
    assert "SetOwner failed" in result["message"]

# --- Tests for get_url ---
@pytest.mark.asyncio
async def test_get_url_local_node_all_channels(registered_node_tools: MockMCP, mock_iface_manager: MagicMock, mock_meshtastic_interface: MagicMock):
    mock_iface_manager.get_interface.return_value = mock_meshtastic_interface
    mock_meshtastic_interface.getQRCodeURL.return_value = "http://example.com/qr_all_channels"

    with patch('asyncio.to_thread', new_callable=AsyncMock) as mock_to_thread:
        mock_to_thread.return_value = "http://example.com/qr_all_channels"
        result_str = await registered_node_tools.tools["get_url"](nodeId="local", includeAll=True)
        
    result = json.loads(result_str)
    assert result["status"] == "success"
    assert result["nodeId"] == "local"
    assert result["type"] == "all_channels_qr_code_url"
    assert result["url"] == "http://example.com/qr_all_channels"
    mock_to_thread.assert_called_once_with(mock_meshtastic_interface.getQRCodeURL)

@pytest.mark.asyncio
async def test_get_url_local_node_primary_channel(registered_node_tools: MockMCP, mock_iface_manager: MagicMock, mock_meshtastic_interface: MagicMock):
    mock_iface_manager.get_interface.return_value = mock_meshtastic_interface
    mock_meshtastic_interface.getURL.return_value = "http://example.com/primary_channel"

    with patch('asyncio.to_thread', new_callable=AsyncMock) as mock_to_thread:
        mock_to_thread.return_value = "http://example.com/primary_channel"
        result_str = await registered_node_tools.tools["get_url"](nodeId="local", includeAll=False)

    result = json.loads(result_str)
    assert result["status"] == "success"
    assert result["nodeId"] == "local"
    assert result["type"] == "primary_channel_url"
    assert result["url"] == "http://example.com/primary_channel"
    mock_to_thread.assert_called_once_with(mock_meshtastic_interface.getURL, 0) # 0 for primary channel

@pytest.mark.asyncio
async def test_get_url_remote_node(registered_node_tools: MockMCP, mock_iface_manager: MagicMock, mock_meshtastic_interface: MagicMock, mock_remote_node: MagicMock):
    mock_iface_manager.get_interface.return_value = mock_meshtastic_interface
    mock_meshtastic_interface.nodes = {mock_remote_node.nodeId: mock_remote_node}
    
    # Simulate channel settings on remote node
    ch_setting = MagicMock(spec=Config.ChannelConfig) # Make it a spec of ChannelConfig
    ch_setting.name = "RemotePrimary"
    # Ensure role is an enum value for Config.ChannelConfig.Role.Name() to work
    ch_setting.role = Config.ChannelConfig.Role.PRIMARY 
    mock_remote_node.settings.channel_settings = [ch_setting]

    result_str = await registered_node_tools.tools["get_url"](nodeId=mock_remote_node.nodeId)
    result = json.loads(result_str)
    
    assert result["status"] == "success"
    assert result["nodeId"] == mock_remote_node.nodeId
    assert "Channel data for URL construction" in result["message"]
    assert len(result["channels"]) == 1
    assert result["channels"][0]["name"] == "RemotePrimary"
    assert result["channels"][0]["role"] == "PRIMARY" # Check role name
    assert "PSK required" in result["channels"][0]["psk_hint"]

@pytest.mark.asyncio
async def test_get_url_node_not_found(registered_node_tools: MockMCP, mock_iface_manager: MagicMock, mock_meshtastic_interface: MagicMock):
    mock_iface_manager.get_interface.return_value = mock_meshtastic_interface
    result_str = await registered_node_tools.tools["get_url"](nodeId="!nonExistent")
    result = json.loads(result_str)
    assert result["status"] == "error"
    assert "Node !nonExistent not found" in result["message"]

# --- Tests for set_url ---
@pytest.mark.asyncio
async def test_set_url_local_node(registered_node_tools: MockMCP, mock_iface_manager: MagicMock, mock_meshtastic_interface: MagicMock):
    mock_iface_manager.get_interface.return_value = mock_meshtastic_interface
    mock_meshtastic_interface.setURL = AsyncMock() # Mock the method on the interface
    test_url = "http://example.com/new_channel_url"

    with patch('asyncio.to_thread', new_callable=AsyncMock) as mock_to_thread:
        mock_to_thread.return_value = None
        result_str = await registered_node_tools.tools["set_url"](url=test_url, nodeId="local")

    result = json.loads(result_str)
    assert result["status"] == "success"
    assert result["nodeId"] == "local"
    assert "URL set" in result["message"]
    mock_to_thread.assert_called_once_with(mock_meshtastic_interface.setURL, test_url)

@pytest.mark.asyncio
async def test_set_url_remote_node_error(registered_node_tools: MockMCP, mock_iface_manager: MagicMock, mock_meshtastic_interface: MagicMock, mock_remote_node: MagicMock):
    mock_iface_manager.get_interface.return_value = mock_meshtastic_interface
    mock_meshtastic_interface.nodes = {mock_remote_node.nodeId: mock_remote_node}
    
    result_str = await registered_node_tools.tools["set_url"](url="http://example.com/url", nodeId=mock_remote_node.nodeId)
    result = json.loads(result_str)
    assert result["status"] == "error"
    assert f"setURL for remote node '{mock_remote_node.nodeId}' is not directly supported" in result["message"]

@pytest.mark.asyncio
async def test_set_url_exception_on_local(registered_node_tools: MockMCP, mock_iface_manager: MagicMock, mock_meshtastic_interface: MagicMock):
    mock_iface_manager.get_interface.return_value = mock_meshtastic_interface
    mock_meshtastic_interface.setURL = AsyncMock(side_effect=Exception("Failed to set URL"))

    with patch('asyncio.to_thread', new_callable=AsyncMock) as mock_to_thread:
        mock_to_thread.side_effect = Exception("Failed to set URL")
        result_str = await registered_node_tools.tools["set_url"](url="http://example.com/url", nodeId="local")
        
    result = json.loads(result_str)
    assert result["status"] == "error"
    assert "Failed to set URL" in result["message"]

# --- Tests for reboot, shutdown, factory_reset (similar structure) ---
# Using reboot as an example, shutdown and factory_reset will be analogous

@pytest.mark.asyncio
@pytest.mark.parametrize("tool_name, node_method_name", [
    ("reboot", "reboot"),
    ("shutdown", "shutdown"),
    ("factory_reset", "factoryReset")
])
async def test_node_command_local_node(tool_name, node_method_name, registered_node_tools: MockMCP, mock_iface_manager: MagicMock, mock_meshtastic_interface: MagicMock, mock_local_node: MagicMock):
    mock_iface_manager.get_interface.return_value = mock_meshtastic_interface
    
    # Get the actual method from the mock_local_node to check calls later
    actual_node_method = getattr(mock_local_node, node_method_name)
    actual_node_method.return_value = None # Ensure it's awaitable if it's an AsyncMock

    args = (15,) if tool_name in ["reboot", "shutdown"] else ()
    
    with patch('asyncio.to_thread', new_callable=AsyncMock) as mock_to_thread:
        mock_to_thread.return_value = None
        if tool_name in ["reboot", "shutdown"]:
             result_str = await registered_node_tools.tools[tool_name](secs=15, nodeId="local")
        else: # factory_reset
             result_str = await registered_node_tools.tools[tool_name](nodeId="local")


    result = json.loads(result_str)
    assert result["status"] == "success"
    assert result["nodeId"] == "local"
    
    # Check that the correct node method was wrapped by to_thread
    mock_to_thread.assert_called_once()
    assert mock_to_thread.call_args[0][0] == actual_node_method
    
    # Check that the node method itself was called with correct args
    actual_node_method.assert_called_once_with(*args)


@pytest.mark.asyncio
@pytest.mark.parametrize("tool_name, node_method_name", [
    ("reboot", "reboot"),
    ("shutdown", "shutdown"),
    ("factory_reset", "factoryReset")
])
async def test_node_command_remote_node(tool_name, node_method_name, registered_node_tools: MockMCP, mock_iface_manager: MagicMock, mock_meshtastic_interface: MagicMock, mock_remote_node: MagicMock):
    mock_iface_manager.get_interface.return_value = mock_meshtastic_interface
    mock_meshtastic_interface.nodes = {mock_remote_node.nodeId: mock_remote_node}

    actual_node_method = getattr(mock_remote_node, node_method_name)
    actual_node_method.return_value = None

    args = (20,) if tool_name in ["reboot", "shutdown"] else ()

    with patch('asyncio.to_thread', new_callable=AsyncMock) as mock_to_thread:
        mock_to_thread.return_value = None
        if tool_name in ["reboot", "shutdown"]:
            result_str = await registered_node_tools.tools[tool_name](secs=20, nodeId=mock_remote_node.nodeId)
        else: # factory_reset
            result_str = await registered_node_tools.tools[tool_name](nodeId=mock_remote_node.nodeId)

    result = json.loads(result_str)
    assert result["status"] == "success"
    assert result["nodeId"] == mock_remote_node.nodeId
    
    mock_to_thread.assert_called_once()
    assert mock_to_thread.call_args[0][0] == actual_node_method
    actual_node_method.assert_called_once_with(*args)

@pytest.mark.asyncio
@pytest.mark.parametrize("tool_name", ["reboot", "shutdown", "factory_reset"])
async def test_node_command_node_not_found(tool_name, registered_node_tools: MockMCP, mock_iface_manager: MagicMock, mock_meshtastic_interface: MagicMock):
    mock_iface_manager.get_interface.return_value = mock_meshtastic_interface
    mock_meshtastic_interface.nodes = {}

    if tool_name in ["reboot", "shutdown"]:
        result_str = await registered_node_tools.tools[tool_name](secs=10, nodeId="!nonExistent")
    else: # factory_reset
        result_str = await registered_node_tools.tools[tool_name](nodeId="!nonExistent")
        
    result = json.loads(result_str)
    assert result["status"] == "error"
    assert "Node !nonExistent not found" in result["message"]

@pytest.mark.asyncio
@pytest.mark.parametrize("tool_name, node_method_name", [
    ("reboot", "reboot"),
    ("shutdown", "shutdown"),
    ("factory_reset", "factoryReset")
])
async def test_node_command_exception(tool_name, node_method_name, registered_node_tools: MockMCP, mock_iface_manager: MagicMock, mock_meshtastic_interface: MagicMock, mock_local_node: MagicMock):
    mock_iface_manager.get_interface.return_value = mock_meshtastic_interface
    
    actual_node_method = getattr(mock_local_node, node_method_name)
    actual_node_method.side_effect = Exception(f"{tool_name} failed")

    with patch('asyncio.to_thread', new_callable=AsyncMock) as mock_to_thread:
        mock_to_thread.side_effect = Exception(f"{tool_name} failed")
        if tool_name in ["reboot", "shutdown"]:
            result_str = await registered_node_tools.tools[tool_name](secs=10, nodeId="local")
        else: # factory_reset
            result_str = await registered_node_tools.tools[tool_name](nodeId="local")

    result = json.loads(result_str)
    assert result["status"] == "error"
    assert f"{tool_name} failed" in result["message"]

@pytest.mark.asyncio
@pytest.mark.parametrize("tool_name, node_method_name", [
    ("reboot", "reboot"),
    ("shutdown", "shutdown"),
    ("factory_reset", "factoryReset")
])
async def test_node_command_attribute_error_fallback(tool_name, node_method_name, registered_node_tools: MockMCP, mock_iface_manager: MagicMock, mock_meshtastic_interface: MagicMock):
    mock_iface_manager.get_interface.return_value = mock_meshtastic_interface
    
    # Simulate localNode initially not having the method (e.g. older firmware object)
    # but the interface's getNode() version does.
    faulty_local_node = MagicMock(spec=Node)
    delattr(faulty_local_node, node_method_name) # Remove the method
    mock_meshtastic_interface.localNode = faulty_local_node

    # Mock the iface.getNode("local") call to return a capable node
    capable_local_node_mock = MagicMock(spec=Node)
    mock_meshtastic_interface.getNode.return_value = capable_local_node_mock
    
    actual_node_method_on_capable_node = getattr(capable_local_node_mock, node_method_name)
    actual_node_method_on_capable_node.return_value = None

    args = (10,) if tool_name in ["reboot", "shutdown"] else ()

    with patch('asyncio.to_thread', new_callable=AsyncMock) as mock_to_thread:
        mock_to_thread.return_value = None
        if tool_name in ["reboot", "shutdown"]:
            result_str = await registered_node_tools.tools[tool_name](secs=10, nodeId="local")
        else: # factory_reset
            result_str = await registered_node_tools.tools[tool_name](nodeId="local")
            
    result = json.loads(result_str)
    assert result["status"] == "success"
    mock_meshtastic_interface.getNode.assert_called_once_with("local") # Verify fallback was tried
    
    mock_to_thread.assert_called_once()
    assert mock_to_thread.call_args[0][0] == actual_node_method_on_capable_node
    actual_node_method_on_capable_node.assert_called_once_with(*args)

@pytest.mark.asyncio
@pytest.mark.parametrize("tool_name, node_method_name", [
    ("shutdown", "shutdown"), # Shutdown has a specific check for this
])
async def test_node_command_attribute_error_no_fallback(tool_name, node_method_name, registered_node_tools: MockMCP, mock_iface_manager: MagicMock, mock_meshtastic_interface: MagicMock, mock_remote_node: MagicMock):
    mock_iface_manager.get_interface.return_value = mock_meshtastic_interface
    mock_meshtastic_interface.nodes = {mock_remote_node.nodeId: mock_remote_node}
    
    # Remove the method from the remote_node to simulate it not being supported
    delattr(mock_remote_node, node_method_name)

    if tool_name in ["reboot", "shutdown"]: # reboot also has a fallback, but shutdown's is more explicit in code
        result_str = await registered_node_tools.tools[tool_name](secs=10, nodeId=mock_remote_node.nodeId)
    else:
        result_str = await registered_node_tools.tools[tool_name](nodeId=mock_remote_node.nodeId)
            
    result = json.loads(result_str)
    assert result["status"] == "error"
    if tool_name == "shutdown":
        assert "Node does not support shutdown command or method not found" in result["message"]
    else: # Generic message for other commands if they fail similarly
        assert f"Node object for {mock_remote_node.nodeId} does not have a '{node_method_name}' method" in result["message"]

# Final check to ensure the file is created.
# If pytest is run, these tests would execute.
# For now, just creating the file with the tests.
print("Test file tests/test_node.py created with Pytest tests.")

# To run these tests (outside this environment, in a real shell):
# Ensure pytest and pytest-asyncio are installed: pip install pytest pytest-asyncio
# Navigate to the root directory of MCPtastic (where tests/ folder is)
# Run: pytest tests/test_node.py
# (May require __init__.py in MCPtastic and tests folders for module discovery)

# Add __init__.py files if they don't exist to make directories importable as packages
# This is more for local testing than for the tool environment if it handles paths.
# For example:
# create_file_with_block
# MCPtastic/__init__.py
# (empty file)
# create_file_with_block
# tests/__init__.py
# (empty file)
# However, the sys.path.insert should handle it for this script's context.
# The tool environment might also implicitly handle module paths.
# I will not add __init__.py files unless an import error occurs during a test run step.
# The current file creation tool should be sufficient for this subtask.

# One final thought: The `_get_node_object` tries to establish a TCP connection if no interface exists.
# This involves `asyncio.to_thread(iface_manager.set_interface, "meshtastic.local", "tcp")`.
# My tests for `_get_node_object_no_interface_attempts_connect` and `_get_node_object_no_interface_connect_fails`
# correctly patch `asyncio.to_thread`. This is good.
# The actual tools (like `show_channels`) rely on `_get_node_object`. If `_get_node_object` fails
# (e.g. cannot connect), it will raise an exception *before* the tool's main logic is hit.
# The tool's try-except block will catch this and return a JSON error.
# This behavior seems correctly covered.
# For instance, if `_get_node_object` raises "Failed to connect...", the tool's `except Exception as e`
# will catch it and put `str(e)` in the JSON response.
# The tests for individual tools mostly assume `_get_node_object` succeeds in returning a node or None (for not found).
# The `test_show_channels_node_not_found` covers the "None" case.
# If `_get_node_object` itself throws an unhandled exception (which it shouldn't due to its own error message for connection failure),
# then the test framework would catch that.
# The current structure seems robust enough for typical scenarios.

```
