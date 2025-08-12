name: "Philips Hue MCP Server Implementation"
description: |
  Build a comprehensive Model Context Protocol (MCP) server that provides Claude with direct control over Philips Hue lights on the local network using FastMCP framework with production-ready async patterns.

---

## Goal

**Feature Goal**: Create a production-ready MCP server that enables Claude to control Philips Hue lights through natural language commands with comprehensive error handling, connection pooling, and performance optimization.

**Deliverable**: Complete Python MCP server package with 5 core tools (hue_control_light, hue_control_room, hue_list_lights, hue_get_light_state, hue_discover_bridge) that can be deployed and integrated with Claude Desktop.

**Success Definition**: Claude can successfully control actual Hue lights at IP 192.168.1.64 through natural language commands like "turn on kitchen lights", "set office to 50% brightness", and "what lights are currently on?" with sub-second response times and graceful error handling.

## User Persona

**Target User**: Claude AI assistant acting on behalf of a homeowner with Philips Hue smart lighting system

**Use Case**: Natural language control of home lighting through conversational commands during daily activities

**User Journey**: 
1. User tells Claude "turn on the kitchen lights"
2. Claude calls hue_control_room with room="kitchen", action="on"
3. MCP server authenticates with bridge at 192.168.1.64
4. Server controls lights [10, 12, 13, 17] concurrently
5. Returns success confirmation to Claude
6. Claude responds to user with natural language confirmation

**Pain Points Addressed**: 
- Eliminates need for manual Hue app usage
- Enables voice/text control through Claude
- Provides room-level grouping for convenience
- Handles network connectivity issues gracefully

## Why

- **Seamless Integration**: Bridges Claude's natural language understanding with physical smart home control
- **Enhanced User Experience**: Enables intuitive lighting control through conversation rather than app navigation
- **Robust Implementation**: Production-ready server with proper error handling, connection pooling, and performance optimization
- **Local Network Control**: Direct bridge communication without cloud dependencies for faster response times

## What

MCP server that exposes 5 tools for comprehensive Hue light control:

### Success Criteria

- [ ] All 5 MCP tools implemented and functional (hue_control_light, hue_control_room, hue_list_lights, hue_get_light_state, hue_discover_bridge)
- [ ] Successfully controls actual Hue lights at 192.168.1.64 using hardcoded username
- [ ] Response times under 1 second for single light operations, under 3 seconds for room operations
- [ ] Graceful error handling for network timeouts, invalid light IDs, and bridge connectivity issues
- [ ] Room mappings work correctly (kitchen: [10,12,13,17], bedroom: [1,4], etc.)
- [ ] Claude Desktop integration working with natural language commands
- [ ] Unit test coverage above 80% for all tool functions

## All Needed Context

### Context Completeness Check

_Before writing this PRP, validated: "If someone knew nothing about this codebase, would they have everything needed to implement this successfully?" - YES. All URLs, patterns, configurations, and implementation details are provided below._

### Documentation & References

```yaml
# MUST READ - Include these in your context window
- url: https://github.com/jlowin/fastmcp
  why: Primary MCP framework for tool creation with decorators and async support
  critical: FastMCP 2.0 is actively maintained, provides simplified decorators for @mcp.tool()

- url: https://github.com/modelcontextprotocol/python-sdk
  why: Official MCP Python SDK for server implementation patterns
  critical: Required for MCP Server class and context management

- url: https://modelcontextprotocol.io/specification/2025-06-18
  why: MCP specification for tool definition and response formats
  critical: JSON-RPC 2.0 protocol requirements and error response structures

- url: https://developers.meethue.com/develop/get-started-2/
  why: Official Hue API documentation for bridge communication
  critical: Authentication flow and rate limiting (10 commands/second for lights, 1/second for groups)

- url: https://www.burgestrand.se/hue-api/
  why: Comprehensive unofficial Hue API reference with examples
  critical: Complete endpoint documentation and JSON payload examples

- docfile: PRPs/ai_docs/hue_api_patterns.md
  why: Consolidated Hue API patterns, error codes, and Python integration examples
  section: Authentication and Rate Limiting

- docfile: PRPs/ai_docs/fastmcp_async_patterns.md  
  why: Production-ready async patterns for MCP servers with connection pooling
  section: Error Handling and Performance Optimization
```

### Current Codebase tree

```bash
hue_mcp/
├── doc/
│   └── PRD.md                    # Complete requirements specification
├── PRPs/
│   └── templates/               # PRP template files
└── install-prp.sh              # PRP installer script
```

### Desired Codebase tree with files to be added and responsibility of file

```bash
hue-mcp-server/
├── src/
│   └── hue_mcp/
│       ├── __init__.py          # Package initialization
│       ├── __main__.py          # CLI entry point for `python -m hue_mcp`
│       ├── server.py            # Main MCP server with FastMCP and tool registration
│       ├── hue_client.py        # Async Hue bridge communication with connection pooling
│       ├── light_manager.py     # Light control logic and room mappings
│       ├── config.py            # Configuration management and validation
│       └── tools/
│           ├── __init__.py      # Tools package init
│           ├── light_control.py # Individual light control tools
│           ├── room_control.py  # Room/group control tools
│           └── discovery.py     # Light discovery and status tools
├── tests/
│   ├── __init__.py
│   ├── test_hue_client.py       # Async client tests with mocking
│   ├── test_light_manager.py    # Light control logic tests
│   ├── test_tools/
│   │   ├── test_light_control.py # Tool function tests
│   │   ├── test_room_control.py  # Room control tests
│   │   └── test_discovery.py     # Discovery tool tests
│   └── conftest.py              # Pytest fixtures and configuration
├── pyproject.toml               # Dependencies, build config, test config
├── README.md                    # Setup and usage instructions
├── .env.example                 # Environment variable template
└── .gitignore                   # Git ignore patterns
```

### Known Gotchas of our codebase & Library Quirks

```python
# CRITICAL: FastMCP requires async functions for MCP tools
# All @mcp.tool() decorated functions must be async def

# CRITICAL: Hue bridge rate limiting is strict
# Lights: Maximum 10 commands/second
# Groups: Maximum 1 command/second  
# Must implement proper rate limiting with semaphores

# CRITICAL: httpx AsyncClient requires proper context management
# Always use async with httpx.AsyncClient() or connection pooling
# Don't create new clients for each request

# CRITICAL: Hue bridge uses hardcoded IP and username for this implementation
HUE_BRIDGE_IP = "192.168.1.64"
HUE_USERNAME = "cJdzxhKlxr2h92jwDkTv-DvpOxglPxn147UEg1Gp"

# CRITICAL: Room mappings are hardcoded per PRD requirements
ROOM_MAPPINGS = {
    "kitchen": [10, 12, 13, 17],     # stove_1, toaster_1, toaster_2, stove_2
    "bedroom": [1, 4],               # neals_lamp, bonnies_lamp  
    "office": [7],                   # office
    "basement": [5, 6, 14, 15, 16],  # basement_e, basement_w, stairway, batcave_color_1, batcave_color_2
    "living_room": [3],              # small_reading_lamp
    "all": 0                         # Special group ID for all lights
}

# CRITICAL: Async error handling must propagate properly
# Use custom exception classes (HueError, HueConnectionError, HueTimeoutError)
# Always wrap external API calls in try/except with specific error types
```

## Implementation Blueprint

### Data models and structure

Create the core data models for type safety and validation.

```python
# Pydantic models for request/response validation
from pydantic import BaseModel, Field
from typing import Optional, Literal, List

class LightControlRequest(BaseModel):
    light_id: int = Field(ge=1, le=17, description="Light ID (1-17)")
    action: Literal["on", "off", "toggle"] = Field(description="Light action")
    brightness: Optional[int] = Field(default=200, ge=1, le=254, description="Brightness (1-254)")
    color_temp: Optional[int] = Field(default=366, ge=154, le=500, description="Color temperature")

class RoomControlRequest(BaseModel):
    room: Literal["kitchen", "bedroom", "office", "basement", "living_room", "all"]
    action: Literal["on", "off", "toggle"]
    brightness: Optional[int] = Field(default=200, ge=1, le=254)
    color_temp: Optional[int] = Field(default=366, ge=154, le=500)

class HueResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None
    lights_affected: Optional[List[int]] = None
```

### Implementation Tasks (ordered by dependencies)

```yaml
Task 1: CREATE src/hue_mcp/__init__.py
  - IMPLEMENT: Package version and basic exports
  - CONTENT: __version__ = "1.0.0" and __all__ exports
  - PLACEMENT: Root of hue_mcp package

Task 2: CREATE src/hue_mcp/config.py  
  - IMPLEMENT: Configuration class with validation using Pydantic
  - FOLLOW pattern: Environment variable loading with python-dotenv
  - INCLUDE: HUE_BRIDGE_IP, HUE_USERNAME constants from PRD
  - VALIDATION: IP format validation, username length validation
  - PLACEMENT: Configuration management in src/hue_mcp/

Task 3: CREATE src/hue_mcp/hue_client.py
  - IMPLEMENT: AsyncHueClient class with httpx and connection pooling
  - FOLLOW pattern: Context manager with async def __aenter__/__aexit__
  - INCLUDE: Rate limiting with asyncio.Semaphore (10/sec lights, 1/sec groups)
  - METHODS: get_lights(), control_light(), control_group(), get_light_state()
  - ERROR HANDLING: Custom exceptions (HueError, HueConnectionError, HueTimeoutError)
  - TIMEOUT: 5 second connection, 10 second read timeout
  - PLACEMENT: Bridge communication in src/hue_mcp/

Task 4: CREATE src/hue_mcp/light_manager.py
  - IMPLEMENT: LightManager class with room mappings and business logic
  - INCLUDE: ROOM_MAPPINGS constant from PRD specification
  - METHODS: async control_light(), async control_room(), async get_light_status()
  - DEPENDENCIES: Import AsyncHueClient from Task 3, config from Task 2
  - VALIDATION: Light ID range checking, room name validation
  - PLACEMENT: Business logic layer in src/hue_mcp/

Task 5: CREATE src/hue_mcp/tools/__init__.py
  - IMPLEMENT: Tools package initialization
  - CONTENT: Empty __init__.py for package structure
  - PLACEMENT: Tools package in src/hue_mcp/tools/

Task 6: CREATE src/hue_mcp/tools/light_control.py
  - IMPLEMENT: hue_control_light and hue_get_light_state MCP tools
  - FOLLOW pattern: @mcp.tool() decorator with async def functions
  - DEPENDENCIES: Import LightManager from Task 4, Pydantic models
  - PARAMETERS: Use LightControlRequest model for validation
  - RETURN: JSON string with HueResponse structure
  - PLACEMENT: Individual light tools in src/hue_mcp/tools/

Task 7: CREATE src/hue_mcp/tools/room_control.py
  - IMPLEMENT: hue_control_room MCP tool with concurrent light control
  - FOLLOW pattern: asyncio.gather() for concurrent room light operations
  - DEPENDENCIES: Import LightManager from Task 4, RoomControlRequest model
  - CONCURRENCY: Use asyncio.Semaphore(5) to limit concurrent operations
  - RETURN: JSON string with lights_affected list
  - PLACEMENT: Room control tools in src/hue_mcp/tools/

Task 8: CREATE src/hue_mcp/tools/discovery.py  
  - IMPLEMENT: hue_list_lights and hue_discover_bridge MCP tools
  - FOLLOW pattern: Simple async functions with error handling
  - DEPENDENCIES: Import AsyncHueClient from Task 3
  - FUNCTIONALITY: Bridge connectivity testing, light enumeration
  - RETURN: JSON string with light data or bridge status
  - PLACEMENT: Discovery tools in src/hue_mcp/tools/

Task 9: CREATE src/hue_mcp/server.py
  - IMPLEMENT: Main MCP server using FastMCP framework
  - FOLLOW pattern: from fastmcp import FastMCP; mcp = FastMCP("Hue Server")
  - INTEGRATE: Import and register all tools from Tasks 6-8
  - INCLUDE: Server configuration, error handling, logging setup
  - ENTRY POINT: if __name__ == "__main__": mcp.run()
  - PLACEMENT: Main server file in src/hue_mcp/

Task 10: CREATE src/hue_mcp/__main__.py
  - IMPLEMENT: CLI entry point for python -m hue_mcp execution
  - CONTENT: from .server import main; main() pattern
  - ENABLE: Command line execution of MCP server
  - PLACEMENT: Package main entry in src/hue_mcp/

Task 11: CREATE pyproject.toml
  - IMPLEMENT: Project configuration with dependencies and metadata
  - DEPENDENCIES: fastmcp>=2.0.0, httpx>=0.24.0, pydantic>=2.0.0, python-dotenv>=1.0.0
  - BUILD SYSTEM: setuptools with src/ layout
  - DEV DEPENDENCIES: pytest>=7.0.0, pytest-asyncio>=0.21.0, coverage>=7.0.0
  - PLACEMENT: Project root configuration

Task 12: CREATE tests/conftest.py
  - IMPLEMENT: Pytest fixtures for async testing and mocking
  - INCLUDE: mock_hue_client, mock_hue_response fixtures
  - SETUP: pytest-asyncio configuration for async tests
  - MOCKING: httpx.AsyncClient mock patterns
  - PLACEMENT: Test configuration in tests/

Task 13: CREATE tests/test_hue_client.py
  - IMPLEMENT: Unit tests for AsyncHueClient with comprehensive mocking
  - FOLLOW pattern: pytest.mark.asyncio for async test functions
  - COVERAGE: Connection handling, rate limiting, error scenarios, timeout handling
  - MOCKING: httpx responses, network failures, rate limit scenarios
  - PLACEMENT: Client tests in tests/

Task 14: CREATE tests/test_tools/test_light_control.py
  - IMPLEMENT: Unit tests for individual light control MCP tools
  - FOLLOW pattern: Mock LightManager dependencies, test tool responses
  - COVERAGE: Valid parameters, invalid light IDs, network errors, success scenarios
  - ASSERTIONS: Verify JSON response format matches HueResponse structure
  - PLACEMENT: Tool tests in tests/test_tools/

Task 15: CREATE .env.example and README.md
  - IMPLEMENT: Environment template and setup documentation
  - INCLUDE: Installation instructions, Claude Desktop integration config
  - EXAMPLE: Complete MCP server configuration for Claude Desktop
  - USAGE: Natural language command examples from PRD
  - PLACEMENT: Project root documentation
```

### Implementation Patterns & Key Details

```python
# MCP Tool Pattern with FastMCP
from fastmcp import FastMCP
from typing import Optional

mcp = FastMCP("Hue Server")

@mcp.tool()
async def hue_control_light(
    light_id: int,
    action: str, 
    brightness: Optional[int] = 200,
    color_temp: Optional[int] = 366
) -> str:
    """Control individual Hue light by ID."""
    # PATTERN: Input validation first with Pydantic
    request = LightControlRequest(
        light_id=light_id,
        action=action, 
        brightness=brightness,
        color_temp=color_temp
    )
    
    # PATTERN: Business logic delegation to manager
    manager = LightManager()
    try:
        result = await manager.control_light(request)
        return result.model_dump_json()
    except HueError as e:
        # PATTERN: Standardized error response
        error_response = HueResponse(
            success=False,
            message=str(e),
            data={"error_type": type(e).__name__}
        )
        return error_response.model_dump_json()

# Async HTTP Client Pattern with Connection Pooling
import httpx
from contextlib import asynccontextmanager

class AsyncHueClient:
    def __init__(self):
        self.base_url = f"http://{HUE_BRIDGE_IP}/api/{HUE_USERNAME}"
        self.timeout = httpx.Timeout(connect=5.0, read=10.0)
        self.limits = httpx.Limits(max_connections=10, max_keepalive_connections=5)
        
    @asynccontextmanager
    async def _get_client(self):
        """PATTERN: Reusable client context manager."""
        async with httpx.AsyncClient(
            timeout=self.timeout,
            limits=self.limits,
            http2=True
        ) as client:
            yield client
    
    async def control_light(self, light_id: int, state: dict) -> dict:
        """CRITICAL: Always use context manager for httpx client."""
        async with self._get_client() as client:
            response = await client.put(
                f"{self.base_url}/lights/{light_id}/state",
                json=state
            )
            response.raise_for_status()
            return response.json()

# Rate Limiting Pattern for Hue API
import asyncio

class RateLimitedHueClient:
    def __init__(self):
        # CRITICAL: Hue bridge rate limits
        self.light_semaphore = asyncio.Semaphore(10)  # 10/second for lights
        self.group_semaphore = asyncio.Semaphore(1)   # 1/second for groups
    
    async def control_light(self, light_id: int, state: dict):
        async with self.light_semaphore:
            # PATTERN: Rate-limited operation
            return await self._make_request(f"/lights/{light_id}/state", "PUT", state)
    
    async def control_group(self, group_id: int, action: dict):
        async with self.group_semaphore:
            await asyncio.sleep(1.0)  # CRITICAL: Group operations need 1-second spacing
            return await self._make_request(f"/groups/{group_id}/action", "PUT", action)
```

### Integration Points

```yaml
ENVIRONMENT:
  - add to: .env.example
  - variables: "HUE_BRIDGE_IP=192.168.1.64\nHUE_USERNAME=cJdzxhKlxr2h92jwDkTv-DvpOxglPxn147UEg1Gp\nLOG_LEVEL=INFO"

CLAUDE_DESKTOP:
  - add to: README.md Claude Integration section
  - config: |
    {
      "mcpServers": {
        "hue-control": {
          "command": "python",
          "args": ["-m", "hue_mcp"],
          "cwd": "/path/to/hue-mcp-server"
        }
      }
    }

TESTING:
  - add to: pyproject.toml [tool.pytest.ini_options]
  - config: "asyncio_mode = auto\ntestpaths = ['tests']\naddopts = '-v --tb=short'"
```

## Validation Loop

### Level 1: Syntax & Style (Immediate Feedback)

```bash
# Run after each file creation - fix before proceeding
python -m ruff check src/hue_mcp/ --fix     # Auto-format and fix linting
python -m mypy src/hue_mcp/                 # Type checking
python -m ruff format src/hue_mcp/          # Consistent formatting

# Project-wide validation
python -m ruff check . --fix
python -m mypy src/
python -m ruff format .

# Expected: Zero errors. If errors exist, READ output and fix before proceeding.
```

### Level 2: Unit Tests (Component Validation)

```bash
# Test each component as it's created
python -m pytest tests/test_hue_client.py -v
python -m pytest tests/test_light_manager.py -v
python -m pytest tests/test_tools/ -v

# Full test suite
python -m pytest tests/ -v --cov=src --cov-report=term-missing

# Expected: All tests pass, coverage above 80%. If failing, debug and fix implementation.
```

### Level 3: Integration Testing (System Validation)

```bash
# MCP server startup validation
python -m hue_mcp &
sleep 3

# Test individual tools (requires actual Hue bridge)
echo '{"method": "tools/call", "params": {"name": "hue_control_light", "arguments": {"light_id": 1, "action": "on"}}}' | python -m hue_mcp

# Test bridge connectivity
echo '{"method": "tools/call", "params": {"name": "hue_discover_bridge", "arguments": {}}}' | python -m hue_mcp

# Test room control
echo '{"method": "tools/call", "params": {"name": "hue_control_room", "arguments": {"room": "kitchen", "action": "on"}}}' | python -m hue_mcp

# Test light discovery  
echo '{"method": "tools/call", "params": {"name": "hue_list_lights", "arguments": {}}}' | python -m hue_mcp

# Expected: All tools return valid JSON responses, actual lights respond correctly
```

### Level 4: Creative & Domain-Specific Validation

```bash
# Claude Desktop Integration Testing
# Add to Claude Desktop config and test these natural language commands:

# "Turn on the kitchen lights"
# Expected: Lights 10, 12, 13, 17 turn on

# "Set office light to 50% brightness"  
# Expected: Light 7 dims to ~127 brightness

# "Turn off all lights"
# Expected: All lights in system turn off via group 0

# "What lights are currently on?"
# Expected: JSON list of active lights with states

# Performance Testing
time python -c "
import asyncio
import json
from src.hue_mcp.tools.room_control import hue_control_room
result = asyncio.run(hue_control_room('kitchen', 'on'))
print(result)
"
# Expected: Room control completes in under 3 seconds

# Network Resilience Testing
# Disconnect network briefly during operation
# Expected: Graceful error handling with proper error messages

# Rate Limiting Testing  
# Make 20 rapid light control calls
for i in {1..20}; do
  echo '{"method": "tools/call", "params": {"name": "hue_control_light", "arguments": {"light_id": 1, "action": "toggle"}}}' | python -m hue_mcp &
done
wait
# Expected: No rate limit errors, proper request spacing
```

## Final Validation Checklist

### Technical Validation

- [ ] All 4 validation levels completed successfully
- [ ] All tests pass: `python -m pytest tests/ -v`
- [ ] No linting errors: `python -m ruff check .`
- [ ] No type errors: `python -m mypy src/`
- [ ] No formatting issues: `python -m ruff format . --check`
- [ ] Test coverage above 80%: `python -m pytest --cov=src --cov-report=term`

### Feature Validation

- [ ] All 5 MCP tools (hue_control_light, hue_control_room, hue_list_lights, hue_get_light_state, hue_discover_bridge) implemented and working
- [ ] Bridge connectivity test successful at 192.168.1.64 with provided username
- [ ] Room mappings working correctly (kitchen: [10,12,13,17], bedroom: [1,4], etc.)
- [ ] Light control response times under 1 second for individual lights
- [ ] Room control response times under 3 seconds for multiple lights
- [ ] Error handling graceful for network timeouts and invalid parameters
- [ ] Claude Desktop integration working with natural language commands

### Code Quality Validation

- [ ] FastMCP framework properly implemented with @mcp.tool() decorators
- [ ] Async/await patterns correctly implemented throughout
- [ ] Connection pooling with httpx working properly
- [ ] Rate limiting implemented (10/sec lights, 1/sec groups)
- [ ] Custom error classes (HueError, HueConnectionError, HueTimeoutError) properly used
- [ ] Pydantic models for request/response validation working
- [ ] All hardcoded values from PRD properly configured

### Documentation & Deployment

- [ ] README.md includes complete setup instructions
- [ ] Claude Desktop integration configuration documented
- [ ] Environment variables properly documented in .env.example  
- [ ] Natural language command examples provided
- [ ] Installation instructions clear and complete

---

## Anti-Patterns to Avoid

- ❌ Don't create synchronous functions for I/O operations - use async/await
- ❌ Don't create new httpx.AsyncClient for each request - use connection pooling
- ❌ Don't ignore Hue bridge rate limits - implement proper semaphore limiting  
- ❌ Don't catch generic Exception without specific error handling
- ❌ Don't hardcode light IDs in individual functions - use room mappings
- ❌ Don't skip input validation - use Pydantic models for all parameters
- ❌ Don't forget to test with actual Hue bridge before deployment
- ❌ Don't return Python objects from MCP tools - always return JSON strings