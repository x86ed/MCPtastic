# Device information and configuration tools
import json
import os
import meshtastic
import meshtastic.tcp_interface
import re
import sqlite3
from typing import Dict, Any, Optional, Union
from datetime import datetime

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
        long_name TEXT,
        short_name TEXT,
        hw_model TEXT,
        public_key TEXT,
        role TEXT,
        position_lat REAL,
        position_lon REAL,
        position_alt INTEGER,
        battery_level INTEGER,
        channel_utilization REAL,
        air_util_tx REAL,
        snr REAL,
        hops_away INTEGER,
        channel INTEGER,
        last_heard TIMESTAMP,
        since TIMESTAMP,   
        node_data JSON,
        created TIMESTAMP,
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
            # Extract user fields
            user_data = node_data.get("user", {})
            long_name = user_data.get("longName")
            short_name = user_data.get("shortName")
            hw_model = user_data.get("hwModel")
            public_key = user_data.get("publicKey")
            role = user_data.get("role")
            
            # Extract position data
            position_data = node_data.get("position", {})
            position_lat = position_data.get("latitude")
            position_lon = position_data.get("longitude")
            position_alt = position_data.get("altitude")
            
            # Extract metrics
            metrics = node_data.get("deviceMetrics", {})
            battery_level = metrics.get("batteryLevel")
            channel_util = metrics.get("channelUtilization")
            air_util_tx = metrics.get("airUtilTx")
            uptime_seconds = metrics.get("uptimeSeconds")
            
            # Other top-level fields
            snr = node_data.get("snr")
            hops_away = node_data.get("hopsAway")
            channel = node_data.get("channel")
            last_heard = node_data.get("lastHeard")
            
            # Convert timestamps
            last_heard_ts = None
            since_ts = None
            
            if last_heard is not None:
                # Convert Unix timestamp to ISO8601 format
                last_heard_ts = datetime.fromtimestamp(last_heard).isoformat()
            
            # Calculate "since" field - last_heard minus uptime_seconds gives the start time
            if last_heard is not None and uptime_seconds is not None:
                since_unix = last_heard - uptime_seconds
                since_ts = datetime.fromtimestamp(since_unix).isoformat()
            
            # Check if record already exists to preserve created timestamp
            cursor.execute("SELECT created FROM nodes WHERE id = ?", (node_id,))
            existing = cursor.fetchone()
            
            # If record exists, use its created timestamp, otherwise use current time
            current_time = datetime.now().isoformat()
            created_timestamp = existing[0] if existing else current_time
            
            cursor.execute('''
            INSERT OR REPLACE INTO nodes (
                id, long_name, short_name, hw_model, public_key, role, 
                position_lat, position_lon, position_alt,
                battery_level, channel_utilization, air_util_tx, 
                snr, hops_away, channel, last_heard, since, node_data,
                created, last_updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (
                node_id, long_name, short_name, hw_model, public_key, role,
                position_lat, position_lon, position_alt,
                battery_level, channel_util, air_util_tx,
                snr, hops_away, channel, last_heard_ts, since_ts, json.dumps(node_data),
                created_timestamp
            ))
        
        print(f"Saved {len(data['Nodes'])} nodes to database")
    
    conn.commit()
    conn.close()

def register_device_tools(mcp):
    """Register all device-related tools with MCP."""
    
    @mcp.tool()
    async def get_info() -> str:
        """Returns information about the connected device."""
        import io
        import contextlib
        
        # Create a string buffer to capture output
        string_buffer = io.StringIO()
        
        iface = meshtastic.tcp_interface.TCPInterface("meshtastic.local")
        try:
            # Capture all stdout to our buffer
            with contextlib.redirect_stdout(string_buffer):
                iface.showInfo()
            
            # Get the captured output
            info = string_buffer.getvalue()
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