# Device information and configuration tools
import json
import meshtastic
import meshtastic.tcp_interface
import re
import sqlite3
from typing import Dict, Any, Optional, Union

def parse_meshtastic_output(content: str) -> Dict[str, Union[Optional[str], Dict[str, Any]]]:
    """
    Parse a Meshtastic output content string into four separate components:
    Owner, MyInfo, Metadata, and Nodes
    
    Args:
        content: Raw Meshtastic output text
        
    Returns:
        Dictionary with four keys: Owner, MyInfo, Metadata, and Nodes
    """
    try:
        # Extract Owner information (simple text, not JSON)
        owner_match = re.search(r'Owner: (.+)', content)
        owner: Optional[str] = owner_match.group(1) if owner_match else None
        
        # Extract MyInfo JSON object
        my_info_match = re.search(r'My info: (\{.+?\})', content)
        if my_info_match:
            try:
                my_info: Dict[str, Any] = json.loads(my_info_match.group(1))
            except json.JSONDecodeError:
                print("Error parsing MyInfo JSON")
                my_info = {}
        else:
            my_info = {}
        
        # Extract Metadata JSON object
        metadata_match = re.search(r'Metadata: (\{.+?\})', content)
        if metadata_match:
            try:
                metadata: Dict[str, Any] = json.loads(metadata_match.group(1))
            except json.JSONDecodeError:
                print("Error parsing Metadata JSON")
                metadata = {}
        else:
            metadata = {}
        
        # Extract Nodes JSON object - this is the most complex part
        nodes_match = re.search(r'Nodes in mesh: (\{[\s\S]+)', content)
        if nodes_match:
            nodes_text = nodes_match.group(1)
            try:
                nodes: Dict[str, Any] = json.loads(nodes_text)
            except json.JSONDecodeError as e:
                print(f"Error parsing Nodes JSON: {e}")
                nodes = {}
        else:
            nodes = {}
        
        return {
            "Owner": owner,
            "MyInfo": my_info,
            "Metadata": metadata,
            "Nodes": nodes
        }
    
    except Exception as e:
        print(f"Error processing content: {str(e)}")
        return {"Owner": None, "MyInfo": {}, "Metadata": {}, "Nodes": {}}

def save_json_objects(data: Dict[str, Any], db_path: str = "meshtastic.db") -> None:
    """
    Save each component to a SQLite database
    
    Args:
        data: Dictionary with extracted Meshtastic data
        db_path: Path to the SQLite database file
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create tables if they don't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS owner (
        id INTEGER PRIMARY KEY,
        name TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS device_info (
        id INTEGER PRIMARY KEY,
        info_type TEXT UNIQUE,
        data JSON,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS nodes (
        id TEXT PRIMARY KEY,
        node_data JSON,
        last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Insert owner information
    if data.get("Owner"):
        cursor.execute('''
        INSERT OR REPLACE INTO owner (id, name, timestamp)
        VALUES (1, ?, CURRENT_TIMESTAMP)
        ''', (data["Owner"],))
        print(f"Saved Owner data to database")
    
    # Insert MyInfo and Metadata
    for info_type in ["MyInfo", "Metadata"]:
        if data.get(info_type):
            cursor.execute('''
            INSERT OR REPLACE INTO device_info (info_type, data, timestamp)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ''', (info_type, json.dumps(data[info_type])))
            print(f"Saved {info_type} data to database")
    
    # Insert or update nodes
    if data.get("Nodes"):
        for node_id, node_data in data["Nodes"].items():
            cursor.execute('''
            INSERT OR REPLACE INTO nodes (id, node_data, last_updated) 
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ''', (node_id, json.dumps(node_data)))
        print(f"Saved {len(data['Nodes'])} nodes to database")
    
    conn.commit()
    conn.close()

def register_device_tools(mcp):
    """Register all device-related tools with MCP."""
    
    @mcp.tool()
    async def get_info() -> str:
        """Returns information about the connected device."""
        iface = meshtastic.tcp_interface.TCPInterface("meshtastic.local")
        try:
            info = iface.showInfo()
            dicts = parse_meshtastic_output(info)
            save_json_objects(dicts)
            return "Device information saved to database"
        finally:
            iface.close()
    
    @mcp.tool()
    async def set_owner(long: str, short:str) -> None:
        """Set the owner of the device (device name).

        Args:
            long (str): The long name of the owner.
            short (str): The short name of the owner.
        """
        iface = meshtastic.tcp_interface.TCPInterface("meshtastic.local")
        try:
            iface.localNode.setOwner(long, short)
            return "Owner set successfully"
        finally:
            iface.close()
    
    return mcp