"""Pytest configuration and fixtures for Hue MCP server tests."""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

import httpx


@pytest.fixture
def mock_hue_response_success():
    """Mock successful Hue API response."""
    return [{"success": {"/lights/1/state/on": True}}]


@pytest.fixture
def mock_hue_response_error():
    """Mock error Hue API response."""
    return [{
        "error": {
            "type": 3,
            "address": "/lights/99",
            "description": "resource, /lights/99, not available"
        }
    }]


@pytest.fixture
def mock_lights_response():
    """Mock response for listing all lights."""
    return {
        "1": {
            "name": "Living Room Light",
            "state": {"on": True, "bri": 200, "ct": 366, "reachable": True},
            "type": "Extended color light"
        },
        "2": {
            "name": "Kitchen Light",
            "state": {"on": False, "bri": 100, "ct": 300, "reachable": True},
            "type": "Dimmable light"
        }
    }


@pytest.fixture
def mock_bridge_config():
    """Mock bridge configuration response."""
    return {
        "name": "Test Bridge",
        "swversion": "1.50.1963220030",
        "apiversion": "1.50.0",
        "mac": "00:17:88:01:02:03",
        "bridgeid": "001788FFFE010203",
        "modelid": "BSB002"
    }


@pytest.fixture
def mock_httpx_response():
    """Mock httpx.Response object."""
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = [{"success": {"/lights/1/state/on": True}}]
    response.raise_for_status.return_value = None
    return response


@pytest.fixture
async def mock_async_client(mock_httpx_response):
    """Mock httpx.AsyncClient with predefined responses."""
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get.return_value = mock_httpx_response
    client.put.return_value = mock_httpx_response
    client.aclose.return_value = None
    return client


@pytest.fixture
def mock_hue_client(mock_async_client):
    """Mock HueClient with mocked HTTP client."""
    with patch('hue_mcp.hue_client.httpx.AsyncClient') as mock_client_class:
        mock_client_class.return_value.__aenter__.return_value = mock_async_client
        mock_client_class.return_value.__aexit__.return_value = None
        yield mock_client_class


@pytest.fixture
def sample_light_control_request():
    """Sample light control request data."""
    return {
        "light_id": 1,
        "action": "on",
        "brightness": 200,
        "color_temp": 366
    }


@pytest.fixture
def sample_room_control_request():
    """Sample room control request data."""
    return {
        "room": "kitchen",
        "action": "on",
        "brightness": 200,
        "color_temp": 366
    }


@pytest.fixture
def mock_rate_limiter():
    """Mock rate limiter that doesn't enforce limits in tests."""
    with patch('hue_mcp.hue_client.HueRateLimiter') as mock_limiter:
        instance = mock_limiter.return_value
        instance.acquire_light_token = AsyncMock()
        instance.acquire_group_token = AsyncMock()
        yield instance


@pytest.fixture
def mock_light_manager():
    """Mock LightManager for testing tools."""
    with patch('hue_mcp.tools.light_control.LightManager') as mock_manager:
        manager_instance = AsyncMock()
        mock_manager.return_value = manager_instance
        yield manager_instance


@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    with patch('hue_mcp.config.config') as mock_cfg:
        mock_cfg.bridge_ip = "192.168.1.64"
        mock_cfg.username = "test_username"
        mock_cfg.base_url = "http://192.168.1.64/api/test_username"
        mock_cfg.timeout_connect = 5.0
        mock_cfg.timeout_read = 10.0
        mock_cfg.max_connections = 10
        mock_cfg.max_keepalive_connections = 5
        mock_cfg.light_rate_limit = 10
        mock_cfg.group_rate_limit = 1.0
        mock_cfg.log_level = "INFO"
        yield mock_cfg


@pytest.fixture
def mock_room_mappings():
    """Mock room mappings for testing."""
    return {
        "kitchen": [10, 12, 13, 17],
        "bedroom": [1, 4],
        "office": [7],
        "basement": [5, 6, 14, 15, 16],
        "living_room": [3],
        "all": 0
    }


@pytest_asyncio.fixture
async def async_context_manager():
    """Helper fixture for async context manager testing."""
    class AsyncContextManager:
        async def __aenter__(self):
            return self
        
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
    
    return AsyncContextManager()


# Configure pytest-asyncio
pytest_asyncio.asyncio_mode = "auto"