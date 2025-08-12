# Hue MCP Server

A production-ready Model Context Protocol (MCP) server that enables Claude to control Philips Hue lights through natural language commands. Built with FastMCP framework and designed for seamless integration with Claude Desktop.

## Features

- **🏠 Room-based Control**: Control lights by room (kitchen, bedroom, office, basement, living_room)
- **💡 Individual Light Control**: Control specific lights by ID (1-17)
- **🔍 Light Discovery**: List all lights and get their current states
- **🌉 Bridge Integration**: Discover and test connectivity to Hue bridge
- **⚡ High Performance**: Async operations with connection pooling and rate limiting
- **🛡️ Error Handling**: Comprehensive error handling with retry logic
- **📊 Production Ready**: Full test coverage, logging, and monitoring

## Available MCP Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `hue_control_light` | Control individual light by ID | `light_id`, `action`, `brightness?`, `color_temp?` |
| `hue_control_room` | Control all lights in a room | `room`, `action`, `brightness?`, `color_temp?` |
| `hue_get_light_state` | Get current state of a light | `light_id` |
| `hue_list_lights` | List all lights and states | None |
| `hue_discover_bridge` | Test bridge connectivity | None |

### Supported Rooms

- `kitchen` - Controls lights: 10, 12, 13, 17 (stove_1, toaster_1, toaster_2, stove_2)
- `bedroom` - Controls lights: 1, 4 (neals_lamp, bonnies_lamp)
- `office` - Controls lights: 7 (office)
- `basement` - Controls lights: 5, 6, 14, 15, 16 (basement_e, basement_w, stairway, batcave_color_1, batcave_color_2)
- `living_room` - Controls lights: 3 (small_reading_lamp)
- `all` - Controls all lights using group 0

### Supported Actions

- `on` - Turn lights on
- `off` - Turn lights off
- `toggle` - Toggle light state

## Installation

### Prerequisites

- Python 3.8 or higher
- Philips Hue Bridge on local network
- Bridge username (already configured for IP 192.168.1.64)

### Install Dependencies

```bash
# Install the package
pip install -e .

# Or install with development dependencies
pip install -e ".[dev]"
```

### Environment Configuration

1. Copy the environment template:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` file if needed (default values work for the configured setup):
   ```
   HUE_BRIDGE_IP=192.168.1.64
   HUE_USERNAME=cJdzxhKlxr2h92jwDkTv-DvpOxglPxn147UEg1Gp
   LOG_LEVEL=INFO
   ```

## Usage

### Running the MCP Server

```bash
# Run directly
python -m hue_mcp

# Or using the console script
hue-mcp
```

### Claude Desktop Integration

Add this configuration to your Claude Desktop MCP settings:

```json
{
  "mcpServers": {
    "hue-control": {
      "command": "python",
      "args": ["-m", "hue_mcp"],
      "cwd": "/path/to/hue-mcp-server"
    }
  }
}
```

### Natural Language Examples

Once integrated with Claude Desktop, you can use natural language commands:

- **"Turn on the kitchen lights"** → Turns on lights 10, 12, 13, 17
- **"Set office light to 50% brightness"** → Dims office light (ID 7) to ~127 brightness
- **"Turn off all lights"** → Turns off all lights using group control
- **"What lights are currently on?"** → Lists all lights with their current states
- **"Toggle the bedroom lights"** → Toggles lights 1 and 4

## Testing

### Run Unit Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=term-missing

# Run specific test file
pytest tests/test_hue_client.py -v
```

### Test Bridge Connectivity

```bash
# Test basic connectivity
python -c "
import asyncio
from src.hue_mcp.hue_client import AsyncHueClient

async def test():
    async with AsyncHueClient() as client:
        success = await client.test_connection()
        print(f'Bridge connection: {\"SUCCESS\" if success else \"FAILED\"}')

asyncio.run(test())
"
```

## Development

### Code Quality

```bash
# Linting and formatting
ruff check src/ --fix
ruff format src/

# Type checking
mypy src/

# Run all quality checks
ruff check . --fix && mypy src/ && ruff format .
```

### Project Structure

```
hue-mcp-server/
├── src/hue_mcp/
│   ├── __init__.py          # Package initialization
│   ├── __main__.py          # CLI entry point
│   ├── server.py            # Main MCP server
│   ├── hue_client.py        # Async HTTP client with rate limiting
│   ├── light_manager.py     # Business logic and room mappings
│   ├── config.py            # Configuration management
│   └── tools/               # MCP tool implementations
│       ├── light_control.py # Individual light control
│       ├── room_control.py  # Room-based control
│       └── discovery.py     # Light discovery and bridge testing
├── tests/                   # Comprehensive test suite
├── pyproject.toml           # Project configuration
├── README.md               # This file
└── .env.example            # Environment template
```

## Performance

- **Light Operations**: Under 1 second response time
- **Room Operations**: Under 3 seconds for multiple lights
- **Rate Limiting**: 10 light operations/second, 1 group operation/second
- **Connection Pooling**: Optimized HTTP connections with keepalive
- **Concurrent Operations**: Up to 5 concurrent light operations per room

## Error Handling

The server includes comprehensive error handling for:

- **Network Issues**: Connection timeouts, DNS failures
- **Bridge Errors**: Invalid light IDs, bridge unavailable
- **Rate Limiting**: Automatic retry with exponential backoff
- **Validation Errors**: Invalid parameters, out-of-range values

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HUE_BRIDGE_IP` | `192.168.1.64` | IP address of Hue bridge |
| `HUE_USERNAME` | (configured) | Bridge authentication username |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `HUE_TIMEOUT_CONNECT` | `5.0` | Connection timeout (seconds) |
| `HUE_TIMEOUT_READ` | `10.0` | Read timeout (seconds) |
| `HUE_MAX_CONNECTIONS` | `10` | Maximum HTTP connections |
| `HUE_LIGHT_RATE_LIMIT` | `10` | Light operations per second |
| `HUE_GROUP_RATE_LIMIT` | `1.0` | Group operations per second |

## Troubleshooting

### Common Issues

**Bridge Not Found**
```
Error: Failed to connect to Hue bridge at 192.168.1.64
Solution: Verify bridge IP and network connectivity
```

**Authentication Failed**
```
Error: Invalid username/authentication
Solution: Verify HUE_USERNAME in .env file
```

**Rate Limiting**
```
Warning: Rate limited, retrying...
Solution: Normal behavior, requests will retry automatically
```

### Debugging

Enable debug logging:
```bash
export LOG_LEVEL=DEBUG
python -m hue_mcp
```

### Bridge Information

- **IP Address**: 192.168.1.64
- **Username**: cJdzxhKlxr2h92jwDkTv-DvpOxglPxn147UEg1Gp
- **Light Range**: IDs 1-17
- **Configured Rooms**: kitchen, bedroom, office, basement, living_room

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Run quality checks: `ruff check . --fix && mypy src/ && pytest`
5. Submit a pull request

---

Built with ❤️ using [FastMCP](https://github.com/jlowin/fastmcp) and designed for seamless Claude integration.