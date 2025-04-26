# Device information and configuration tools
import contextlib
import io
import json
import meshtastic
from meshtastic import mt_config
import meshtastic.tcp_interface
import re
import sqlite3
from typing import Dict, Any, List, Optional, Union
from google.protobuf.json_format import MessageToDict
from datetime import datetime

import yaml

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

def splitCompoundName(comp_name: str) -> List[str]:
    """Split compound (dot separated) preference name into parts"""
    name: List[str] = comp_name.split(".")
    if len(name) < 2:
        name[0] = comp_name
        name.append(comp_name)
    return name

def traverseConfig(config_root, config, interface_config) -> bool:
    """Iterate through current config level preferences and either traverse deeper if preference is a dict or set preference"""
    snake_name = meshtastic.util.camel_to_snake(config_root)
    for pref in config:
        pref_name = f"{snake_name}.{pref}"
        if isinstance(config[pref], dict):
            traverseConfig(pref_name, config[pref], interface_config)
        else:
            setPref(interface_config, pref_name, config[pref])

    return True

def setPref(config, comp_name, raw_val) -> bool:
    """Set a channel or preferences value"""

    name = splitCompoundName(comp_name)

    snake_name = meshtastic.util.camel_to_snake(name[-1])
    camel_name = meshtastic.util.snake_to_camel(name[-1])
    uni_name = camel_name if mt_config.camel_case else snake_name

    objDesc = config.DESCRIPTOR
    config_part = config
    config_type = objDesc.fields_by_name.get(name[0])
    if config_type and config_type.message_type is not None:
        for name_part in name[1:-1]:
            part_snake_name = meshtastic.util.camel_to_snake((name_part))
            config_part = getattr(config, config_type.name)
            config_type = config_type.message_type.fields_by_name.get(part_snake_name)
    pref = None
    if config_type and config_type.message_type is not None:
        pref = config_type.message_type.fields_by_name.get(snake_name)
    # Others like ChannelSettings are standalone
    elif config_type:
        pref = config_type

    if (not pref) or (not config_type):
        return False

    if isinstance(raw_val, str):
        val = meshtastic.util.fromStr(raw_val)
    else:
        val = raw_val

    if snake_name == "wifi_psk" and len(str(raw_val)) < 8:
        print("Warning: network.wifi_psk must be 8 or more characters.")
        return False

    enumType = pref.enum_type
    # pylint: disable=C0123
    if enumType and type(val) == str:
        # We've failed so far to convert this string into an enum, try to find it by reflection
        e = enumType.values_by_name.get(val)
        if e:
            val = e.number
        else:
            print(
                f"{name[0]}.{uni_name} does not have an enum called {val}, so you can not set it."
            )
            print(f"Choices in sorted order are:")
            names = []
            for f in enumType.values:
                # Note: We must use the value of the enum (regardless if camel or snake case)
                names.append(f"{f.name}")
            for temp_name in sorted(names):
                print(f"    {temp_name}")
            return False

    # repeating fields need to be handled with append, not setattr
    if pref.label != pref.LABEL_REPEATED:
        try:
            if config_type.message_type is not None:
                config_values = getattr(config_part, config_type.name)
                setattr(config_values, pref.name, val)
            else:
                setattr(config_part, snake_name, val)
        except TypeError:
            # The setter didn't like our arg type guess try again as a string
            config_values = getattr(config_part, config_type.name)
            setattr(config_values, pref.name, str(val))
    elif type(val) == list:
        new_vals = [meshtastic.util.fromStr(x) for x in val]
        config_values = getattr(config, config_type.name)
        getattr(config_values, pref.name)[:] = new_vals
    else:
        config_values = getattr(config, config_type.name)
        if val == 0:
            # clear values
            print(f"Clearing {pref.name} list")
            del getattr(config_values, pref.name)[:]
        else:
            print(f"Adding '{raw_val}' to the {pref.name} list")
            cur_vals = [x for x in getattr(config_values, pref.name) if x not in [0, "", b""]]
            cur_vals.append(val)
            getattr(config_values, pref.name)[:] = cur_vals
        return True

    prefix = f"{'.'.join(name[0:-1])}." if config_type.message_type is not None else ""
    print(f"Set {prefix}{uni_name} to {raw_val}")

    return True

def ex_config(interface) -> str:
    """used in --export-config"""
    configObj = {}

    owner = interface.getLongName()
    owner_short = interface.getShortName()
    channel_url = interface.localNode.getURL()
    myinfo = interface.getMyNodeInfo()
    pos = myinfo.get("position")
    lat = None
    lon = None
    alt = None
    if pos:
        lat = pos.get("latitude")
        lon = pos.get("longitude")
        alt = pos.get("altitude")

    if owner:
        configObj["owner"] = owner
    if owner_short:
        configObj["owner_short"] = owner_short
    if channel_url:
        if mt_config.camel_case:
            configObj["channelUrl"] = channel_url
        else:
            configObj["channel_url"] = channel_url
    # lat and lon don't make much sense without the other (so fill with 0s), and alt isn't meaningful without both
    if lat or lon:
        configObj["location"] = {"lat": lat or float(0), "lon": lon or float(0)}
        if alt:
            configObj["location"]["alt"] = alt

    config = MessageToDict(interface.localNode.localConfig)	#checkme - Used as a dictionary here and a string below
    if config:
        # Convert inner keys to correct snake/camelCase
        prefs = {}
        for pref in config:
            if mt_config.camel_case:
                prefs[meshtastic.util.snake_to_camel(pref)] = config[pref]
            else:
                prefs[pref] = config[pref]
            # mark base64 encoded fields as such
            if pref == "security":
                if 'privateKey' in prefs[pref]:
                    prefs[pref]['privateKey'] = 'base64:' + prefs[pref]['privateKey']
                if 'publicKey' in prefs[pref]:
                    prefs[pref]['publicKey'] = 'base64:' + prefs[pref]['publicKey']
                if 'adminKey' in prefs[pref]:
                    for i in range(len(prefs[pref]['adminKey'])):
                        prefs[pref]['adminKey'][i] = 'base64:' + prefs[pref]['adminKey'][i]
        if mt_config.camel_case:
            configObj["config"] = config		#Identical command here and 2 lines below?
        else:
            configObj["config"] = config

    module_config = MessageToDict(interface.localNode.moduleConfig)
    if module_config:
        # Convert inner keys to correct snake/camelCase
        prefs = {}
        for pref in module_config:
            if len(module_config[pref]) > 0:
                prefs[pref] = module_config[pref]
        if mt_config.camel_case:
            configObj["module_config"] = prefs
        else:
            configObj["module_config"] = prefs

    config_txt = "# start of Meshtastic configure yaml\n"		#checkme - "config" (now changed to config_out)
                                                                        #was used as a string here and a Dictionary above
    config_txt += yaml.dump(configObj)
    return config_txt



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
    async def get_support_info() -> str:
        """Returns support information about the connected device."""
        
        iface = meshtastic.tcp_interface.TCPInterface("meshtastic.local")
        try:
            # Capture all stdout to our buffer
            output_buffer = io.StringIO()
            with contextlib.redirect_stdout(output_buffer):
                meshtastic.util.support_info()
            return output_buffer.getvalue()
        finally:
            iface.close()

    @mcp.tool()
    async def export_config() -> str:
        """Exports the configuration of the connected device as YAML."""
        
        iface = meshtastic.tcp_interface.TCPInterface("meshtastic.local")
        try:
            return ex_config(iface)
        finally:
            iface.close()

    @mcp.tool()
    async def configure(yml: str) -> str:
        """sets the configuration of the connected device from YAML.
        
        Args:
            yml (str): YAML configuration string
        """
        
        iface = meshtastic.tcp_interface.TCPInterface("meshtastic.local")
        out = ""
        try:
            configuration = yaml.safe_load(yml)
            if "owner" in configuration:
                    out += f"Setting device owner to {configuration['owner']}"
                    usr = iface.getMyNodeInfo().get("user")
                    id = usr.get("id")
                    iface.getNode(id).setOwner(configuration["owner"])

            if "owner_short" in configuration:
                    print(
                        f"Setting device owner short to {configuration['owner_short']}"
                    )
                    iface.getNode(id).setOwner(
                        long_name=None, short_name=configuration["owner_short"]
                    )

            if "ownerShort" in configuration:
                    print(
                        f"Setting device owner short to {configuration['ownerShort']}"
                    )
                    iface.getNode(id).setOwner(
                        long_name=None, short_name=configuration["ownerShort"]
                    )

            if "channel_url" in configuration:
                    print("Setting channel url to", configuration["channel_url"])
                    iface.getNode(id).setURL(configuration["channel_url"])

            if "channelUrl" in configuration:
                    print("Setting channel url to", configuration["channelUrl"])
                    iface.getNode(id).setURL(configuration["channelUrl"])

            if "location" in configuration:
                alt = 0
                lat = 0.0
                lon = 0.0
                localConfig = iface.localNode.localConfig

                if "alt" in configuration["location"]:
                    alt = int(configuration["location"]["alt"] or 0)
                    print(f"Fixing altitude at {alt} meters")
                if "lat" in configuration["location"]:
                    lat = float(configuration["location"]["lat"] or 0)
                    print(f"Fixing latitude at {lat} degrees")
                if "lon" in configuration["location"]:
                    lon = float(configuration["location"]["lon"] or 0)
                    print(f"Fixing longitude at {lon} degrees")
                print("Setting device position")
                iface.localNode.setFixedPosition(lat, lon, alt)

                if "config" in configuration:
                    localConfig = iface.getNode(id).localConfig
                    for section in configuration["config"]:
                        traverseConfig(
                            section, configuration["config"][section], localConfig
                        )
                        iface.getNode(id).writeConfig(
                            meshtastic.util.camel_to_snake(section)
                        )

                if "module_config" in configuration:
                    moduleConfig = iface.getNode(id).moduleConfig
                    for section in configuration["module_config"]:
                        traverseConfig(
                            section,
                            configuration["module_config"][section],
                            moduleConfig,
                        )
                        iface.getNode(id).writeConfig(
                            meshtastic.util.camel_to_snake(section)
                        )

                iface.getNode(id).commitSettingsTransaction()
                print("Writing modified configuration to device")

        
            return out
        finally:
            iface.close()        
    
    return mcp