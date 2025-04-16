# MCPtastic

## What is MCPtastic?

MCPtastic provides Model Context Protocol (MCP) bindings for the Meshtastic CLI. This allows AI assistants like Claude to directly interact with your Meshtastic devices, enabling powerful voice and text control of your mesh network.

With MCPtastic, you can ask Claude to:

- Send messages over your mesh network
- Create and manage waypoints
- Get device information
- Set device configuration
- Access location data
- And much more...

## Installation

### Prerequisites

- Python 3.9 or higher
- UV package manager (a modern replacement for pip)
- A Meshtastic device (connected via USB or available on your network)
- Claude Desktop app

### Setup Instructions

1. **Clone the repository**:

   ```bash
   git clone https://github.com/username/MCPtastic.git
   cd MCPtastic
   ```

2. **Install dependencies**:

   ```bash
   # If you don't have uv installed yet
   curl -sSf https://install.ultraviolet.rs | sh

   # Install dependencies with uv
   uv pip install -r requirements.txt
   ```

3. **Configure Claude Desktop**:
   - Open Claude Desktop
   - Go to Settings
   - Navigate to the "Tools" section
   - Click "Add Tool"
   - Select "Add Local Tool"
   - Fill in the following details:
     - Name: MCPtastic
     - Description: Meshtastic MCP bindings
     - Command: `python -m MCPtastic.main`
     - Working Directory: /path/to/your/MCPtastic/directory

4. **Connect your Meshtastic device**:
   - Connect your device via USB or ensure it's available on your local network
   - For network devices, make sure they're accessible via `meshtastic.local` or configure the appropriate IP address in the code

## Example Prompts for Claude

Here are some example prompts you can use with Claude Desktop to interact with your Meshtastic device:

### Basic Device Information

```
Can you get information about my connected Meshtastic device?
```

### Sending Messages

```
Please send a message saying "Hello from Claude!" to everyone on my mesh network.
```

### Working with Locations

```
What's my device's current location? If it doesn't have one set, can you use my IP address to set an approximate location?
```

### Managing Waypoints

```
Please create a waypoint at Golden Gate Bridge (37.8199° N, 122.4783° W) named "Golden Gate Bridge" with a description "Famous suspension bridge in San Francisco".
```

### Device Configuration

```
Could you set my device name to "Claude's Node" with the short name "CN"?
```

### Getting Network Information

```
Show me all the nodes currently connected to my mesh network.
```

### Combining Multiple Operations

```
Please find my current location using my IP address, set it as my device's fixed position, and then send a message to the network with my coordinates.
```

## Advanced Usage

MCPtastic organizes Meshtastic functionality into different modules:

- `device.py`: Device information and configuration
- `location.py`: Location services and GPS features
- `messaging.py`: Text and data messaging
- `waypoints.py`: Creating and managing waypoints

You can ask Claude to perform complex sequences of operations that combine these different capabilities. The more specific your instructions, the better the results will be.

## Troubleshooting

If Claude has trouble connecting to your device, try these common solutions:

- Ensure your device is properly connected and powered on
- Verify that your device is accessible at `meshtastic.local` or provide the correct IP address
- Check that you have the latest Meshtastic firmware installed
- Restart Claude Desktop to refresh the connection

## Contributing

Contributions to MCPtastic are welcome! Please feel free to submit issues or pull requests.
