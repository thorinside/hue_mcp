# Philips Hue MCP Server Specification

## Overview
Build a Model Context Protocol (MCP) server that provides Claude with direct control over Philips Hue lights on the local network. This server will run on a machine that has access to both the local LAN (where the Hue bridge is located) and can communicate with Claude.

## Requirements

### Core Functionality
- **Light Control**: Turn lights on/off, adjust brightness, set color temperature
- **Light Discovery**: List available lights and their current states
- **Room/Group Control**: Control multiple lights by room or predefined groups
- **Status Queries**: Get current state of lights/rooms

### Network Architecture
- Server runs on local machine with access to Hue bridge at `192.168.1.64`
- Uses Hue bridge username: `cJdzxhKlxr2h92jwDkTv-DvpOxglPxn147UEg1Gp`
- Exposes MCP interface for Claude to call remotely

## Technical Specifications

### Language & Framework
- **Language**: Python 3.9+
- **MCP Framework**: Use `mcp` Python package
- **HTTP Client**: `requests` or `httpx` for Hue API calls
- **Async Support**: Use `asyncio` for concurrent operations

### Project Structure
```
hue-mcp-server/
├── src/
│   ├── hue_mcp/
│   │   ├── __init__.py
│   │   ├── server.py          # Main MCP server
│   │   ├── hue_client.py      # Hue bridge communication
│   │   ├── light_manager.py   # Light control logic
│   │   └── config.py          # Configuration management
├── pyproject.toml             # Dependencies and project config
├── README.md                  # Setup and usage instructions
└── .env.example               # Environment variable template
```

## MCP Tools to Implement

### 1. `hue_control_light`
**Description**: Control individual light by ID
**Parameters**:
- `light_id` (required): Integer light ID (1-17)
- `action` (required): "on" | "off" | "toggle"
- `brightness` (optional): Integer 1-254, default 200
- `color_temp` (optional): Integer 154-500, default 366

**Example**: 
```json
{
  "light_id": 10,
  "action": "on", 
  "brightness": 150,
  "color_temp": 250
}
```

### 2. `hue_control_room`
**Description**: Control lights by room name
**Parameters**:
- `room` (required): "kitchen" | "bedroom" | "office" | "basement" | "living_room" | "all"
- `action` (required): "on" | "off" | "toggle"
- `brightness` (optional): Integer 1-254, default 200
- `color_temp` (optional): Integer 154-500, default 366

**Room Mappings**:
- kitchen: [10, 12, 13, 17] (stove_1, toaster_1, toaster_2, stove_2)
- bedroom: [1, 4] (neals_lamp, bonnies_lamp)
- office: [7] (office)
- basement: [5, 6, 14, 15, 16] (basement_e, basement_w, stairway, batcave_color_1, batcave_color_2)
- living_room: [3] (small_reading_lamp)
- all: Use Hue group 0 (all lights)

### 3. `hue_list_lights`
**Description**: Get all available lights and their current states
**Parameters**: None
**Returns**: Array of light objects with id, name, state (on/off), brightness, reachable status

### 4. `hue_get_light_state`
**Description**: Get current state of specific light
**Parameters**:
- `light_id` (required): Integer light ID
**Returns**: Light object with current state details

### 5. `hue_discover_bridge`
**Description**: Test connectivity to Hue bridge and validate credentials
**Parameters**: None
**Returns**: Bridge info and connection status

## Configuration

### Environment Variables
```bash
HUE_BRIDGE_IP=192.168.1.64
HUE_USERNAME=cJdzxhKlxr2h92jwDkTv-DvpOxglPxn147UEg1Gp
MCP_SERVER_PORT=3001
LOG_LEVEL=INFO
```

### Light Name to ID Mapping
```python
LIGHT_MAPPING = {
    "neals_lamp": 1,
    "tall_lamp": 2,
    "small_reading_lamp": 3,
    "bonnies_lamp": 4,
    "basement_e": 5,
    "basement_w": 6,
    "office": 7,
    "door_1": 8,
    "door_2": 9,
    "stove_1": 10,
    "toaster_1": 12,
    "toaster_2": 13,
    "stairway": 14,
    "batcave_color_1": 15,
    "batcave_color_2": 16,
    "stove_2": 17
}
```

## API Implementation Details

### Hue Bridge Endpoints
- **Get lights**: `GET http://192.168.1.64/api/{username}/lights`
- **Control light**: `PUT http://192.168.1.64/api/{username}/lights/{id}/state`
- **Control group**: `PUT http://192.168.1.64/api/{username}/groups/{id}/action`

### Error Handling
- Handle network timeouts (5-second timeout)
- Validate light IDs exist before commands
- Return meaningful error messages for invalid parameters
- Log all operations for debugging

### Response Format
All tools should return JSON responses with:
```json
{
  "success": true/false,
  "message": "Human readable description",
  "data": { /* relevant response data */ },
  "lights_affected": [1, 2, 3]  /* for multi-light operations */
}
```

## Installation & Usage

### Dependencies
```toml
[dependencies]
mcp = "^1.0.0"
requests = "^2.31.0"
python-dotenv = "^1.0.0"
pydantic = "^2.0.0"
```

### Running the Server
```bash
# Install dependencies
pip install -e .

# Run MCP server
python -m hue_mcp.server
```

### Claude Desktop Integration
Add to Claude Desktop MCP config:
```json
{
  "mcpServers": {
    "hue-control": {
      "command": "python",
      "args": ["-m", "hue_mcp.server"],
      "cwd": "/path/to/hue-mcp-server"
    }
  }
}
```

## Testing Requirements

### Unit Tests
- Test each MCP tool function
- Mock Hue bridge responses
- Test error conditions

### Integration Tests
- Test with actual Hue bridge (optional)
- Validate light control works end-to-end

### Test Commands
```bash
# After installation, test with Claude:
# "Turn on the kitchen lights"
# "Set office light to 50% brightness" 
# "Turn off all lights"
# "What lights are currently on?"
```

## Success Criteria
1. All 5 MCP tools implemented and functional
2. Successfully controls actual Hue lights on local network
3. Proper error handling and logging
4. Claude can control lights through natural language commands
5. Documentation complete with setup instructions

## Notes
- Bridge IP and username are hardcoded for this specific setup
- Server should be robust enough to handle network interruptions
- Consider adding rate limiting to avoid overwhelming the bridge
- Future enhancement: Support for light colors and effects
