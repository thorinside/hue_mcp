"""Simple functional tests for core functionality without FastMCP decorators."""

import pytest
import pytest_asyncio
import json
from unittest.mock import AsyncMock, patch

from hue_mcp.light_manager import LightManager, LightControlRequest, HueResponse
from hue_mcp.hue_client import AsyncHueClient, HueError


class TestLightManager:
    """Test LightManager functionality."""
    
    async def test_light_manager_creation(self):
        """Test basic LightManager creation."""
        manager = LightManager()
        assert manager is not None
        assert manager.room_mappings is not None
        assert manager.light_mapping is not None
    
    async def test_light_control_request_validation(self):
        """Test LightControlRequest validation."""
        # Valid request
        request = LightControlRequest(
            light_id=1,
            action="on",
            brightness=200,
            color_temp=366
        )
        assert request.light_id == 1
        assert request.action == "on"
        assert request.brightness == 200
        assert request.color_temp == 366
        
        # Invalid light ID
        with pytest.raises(Exception):
            LightControlRequest(
                light_id=0,  # Invalid
                action="on"
            )
        
        # Invalid brightness
        with pytest.raises(Exception):
            LightControlRequest(
                light_id=1,
                action="on",
                brightness=300  # Invalid (>254)
            )
    
    @patch('hue_mcp.light_manager.AsyncHueClient')
    async def test_control_light_success(self, mock_client_class):
        """Test successful light control."""
        # Setup mock
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        # Mock the light info that get_light_state returns
        light_info = {
            "name": "Test Light",
            "type": "Extended color light",
            "state": {"on": True, "bri": 200},
            "capabilities": {"control": {"ct": {"min": 154, "max": 500}}}
        }
        mock_client.get_light_state.return_value = light_info
        mock_client.control_light.return_value = {"success": True}
        
        # Test
        manager = LightManager()
        request = LightControlRequest(light_id=1, action="on")
        result = await manager.control_light(request)
        
        # Assertions
        assert isinstance(result, HueResponse)
        assert result.success is True
        assert result.lights_affected == [1]


class TestAsyncHueClientBasic:
    """Basic tests for AsyncHueClient."""
    
    def test_hue_client_creation(self):
        """Test basic client creation."""
        client = AsyncHueClient()
        assert client is not None
        assert client.base_url is not None
        assert client.timeout is not None
        assert client.limits is not None
        assert client.rate_limiter is not None