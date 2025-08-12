"""Unit tests for light control MCP tools."""

import pytest
import pytest_asyncio
import json
from unittest.mock import AsyncMock, patch

from hue_mcp.tools import light_control
from hue_mcp.light_manager import HueResponse
from hue_mcp.hue_client import HueError, HueValidationError


class TestHueControlLight:
    """Test hue_control_light MCP tool."""
    
    async def test_valid_light_control_on(self):
        """Test controlling a light with valid parameters."""
        with patch('hue_mcp.tools.light_control.LightManager') as mock_manager_class:
            # Setup mock
            mock_manager = AsyncMock()
            mock_manager_class.return_value = mock_manager
            
            expected_response = HueResponse(
                success=True,
                message="Light 1 on successfully",
                lights_affected=[1],
                data={"success": True}
            )
            mock_manager.control_light.return_value = expected_response
            
            # Test - Call the underlying function from the FastMCP tool
            result = await light_control.hue_control_light.fn(
                light_id=1,
                action="on",
                brightness=200,
                color_temp=366
            )
            
            # Assertions
            result_dict = json.loads(result)
            assert result_dict["success"] is True
            assert result_dict["message"] == "Light 1 on successfully"
            assert result_dict["lights_affected"] == [1]
            
            # Verify manager was called correctly
            mock_manager.control_light.assert_called_once()
            call_args = mock_manager.control_light.call_args[0][0]
            assert call_args.light_id == 1
            assert call_args.action == "on"
            assert call_args.brightness == 200
            assert call_args.color_temp == 366
    
    async def test_valid_light_control_off(self):
        """Test turning off a light."""
        with patch('hue_mcp.tools.light_control.LightManager') as mock_manager_class:
            # Setup mock
            mock_manager = AsyncMock()
            mock_manager_class.return_value = mock_manager
            
            expected_response = HueResponse(
                success=True,
                message="Light 5 off successfully",
                lights_affected=[5],
                data={"success": True}
            )
            mock_manager.control_light.return_value = expected_response
            
            # Test
            result = await light_control.hue_control_light.fn(
                light_id=5,
                action="off"
            )
            
            # Assertions
            result_dict = json.loads(result)
            assert result_dict["success"] is True
            assert result_dict["message"] == "Light 5 off successfully"
    
    async def test_valid_light_control_toggle(self):
        """Test toggling a light."""
        with patch('hue_mcp.tools.light_control.LightManager') as mock_manager_class:
            # Setup mock
            mock_manager = AsyncMock()
            mock_manager_class.return_value = mock_manager
            
            expected_response = HueResponse(
                success=True,
                message="Light 3 toggle successfully",
                lights_affected=[3],
                data={"success": True}
            )
            mock_manager.control_light.return_value = expected_response
            
            # Test
            result = await light_control.hue_control_light.fn(
                light_id=3,
                action="toggle",
                brightness=150
            )
            
            # Assertions
            result_dict = json.loads(result)
            assert result_dict["success"] is True
    
    async def test_invalid_light_id_low(self):
        """Test with light ID below valid range."""
        result = await light_control.hue_control_light.fn(
            light_id=0,
            action="on"
        )
        
        result_dict = json.loads(result)
        assert result_dict["success"] is False
        assert "validation_errors" in result_dict["data"]
    
    async def test_invalid_light_id_high(self):
        """Test with light ID above valid range."""
        result = await light_control.hue_control_light.fn(
            light_id=18,
            action="on"
        )
        
        result_dict = json.loads(result)
        assert result_dict["success"] is False
        assert "validation_errors" in result_dict["data"]
    
    async def test_invalid_action(self):
        """Test with invalid action parameter."""
        result = await light_control.hue_control_light.fn(
            light_id=1,
            action="invalid_action"
        )
        
        result_dict = json.loads(result)
        assert result_dict["success"] is False
        assert result_dict["data"]["error_type"] == "HueValidationError"
    
    async def test_invalid_brightness_low(self):
        """Test with brightness below valid range."""
        result = await light_control.hue_control_light.fn(
            light_id=1,
            action="on",
            brightness=0
        )
        
        result_dict = json.loads(result)
        assert result_dict["success"] is False
        assert "validation_errors" in result_dict["data"]
    
    async def test_invalid_brightness_high(self):
        """Test with brightness above valid range."""
        result = await light_control.hue_control_light.fn(
            light_id=1,
            action="on",
            brightness=255
        )
        
        result_dict = json.loads(result)
        assert result_dict["success"] is False
        assert "validation_errors" in result_dict["data"]
    
    async def test_invalid_color_temp_low(self):
        """Test with color temperature below valid range."""
        result = await light_control.hue_control_light.fn(
            light_id=1,
            action="on",
            color_temp=150
        )
        
        result_dict = json.loads(result)
        assert result_dict["success"] is False
        assert "validation_errors" in result_dict["data"]
    
    async def test_invalid_color_temp_high(self):
        """Test with color temperature above valid range."""
        result = await light_control.hue_control_light.fn(
            light_id=1,
            action="on",
            color_temp=501
        )
        
        result_dict = json.loads(result)
        assert result_dict["success"] is False
        assert "validation_errors" in result_dict["data"]
    
    async def test_hue_error_handling(self):
        """Test handling of HueError from manager."""
        with patch('hue_mcp.tools.light_control.LightManager') as mock_manager_class:
            # Setup mock to raise HueError
            mock_manager = AsyncMock()
            mock_manager_class.return_value = mock_manager
            mock_manager.control_light.side_effect = HueError("Bridge connection failed")
            
            # Test
            result = await light_control.hue_control_light.fn(
                light_id=1,
                action="on"
            )
            
            # Assertions
            result_dict = json.loads(result)
            assert result_dict["success"] is False
            assert "Bridge connection failed" in result_dict["message"]
            assert result_dict["data"]["error_type"] == "HueError"
    
    async def test_unexpected_error_handling(self):
        """Test handling of unexpected errors."""
        with patch('hue_mcp.tools.light_control.LightManager') as mock_manager_class:
            # Setup mock to raise unexpected error
            mock_manager = AsyncMock()
            mock_manager_class.return_value = mock_manager
            mock_manager.control_light.side_effect = RuntimeError("Unexpected error")
            
            # Test
            result = await light_control.hue_control_light.fn(
                light_id=1,
                action="on"
            )
            
            # Assertions
            result_dict = json.loads(result)
            assert result_dict["success"] is False
            assert "An unexpected error occurred" in result_dict["message"]
            assert result_dict["data"]["error_type"] == "UnexpectedError"


class TestHueGetLightState:
    """Test hue_get_light_state MCP tool."""
    
    async def test_valid_light_state_query(self):
        """Test getting light state with valid light ID."""
        with patch('hue_mcp.tools.light_control.LightManager') as mock_manager_class:
            # Setup mock
            mock_manager = AsyncMock()
            mock_manager_class.return_value = mock_manager
            
            expected_response = HueResponse(
                success=True,
                message="Retrieved status for light 1",
                data={
                    "name": "Test Light",
                    "state": {"on": True, "bri": 200, "ct": 366}
                }
            )
            mock_manager.get_light_status.return_value = expected_response
            
            # Test
            result = await light_control.hue_get_light_state.fn(light_id=1)
            
            # Assertions
            result_dict = json.loads(result)
            assert result_dict["success"] is True
            assert result_dict["message"] == "Retrieved status for light 1"
            assert "Test Light" in str(result_dict["data"])
            
            # Verify manager was called correctly
            mock_manager.get_light_status.assert_called_once_with(1)
    
    async def test_invalid_light_id_type(self):
        """Test with non-integer light ID."""
        result = await light_control.hue_get_light_state.fn(light_id="invalid")
        
        result_dict = json.loads(result)
        assert result_dict["success"] is False
        assert "ValidationError" in result_dict["data"]["error_type"]
    
    async def test_invalid_light_id_low(self):
        """Test with light ID below valid range."""
        result = await light_control.hue_get_light_state.fn(light_id=0)
        
        result_dict = json.loads(result)
        assert result_dict["success"] is False
        assert "must be an integer between 1 and 17" in result_dict["message"]
    
    async def test_invalid_light_id_high(self):
        """Test with light ID above valid range."""
        result = await light_control.hue_get_light_state.fn(light_id=18)
        
        result_dict = json.loads(result)
        assert result_dict["success"] is False
        assert "must be an integer between 1 and 17" in result_dict["message"]
    
    async def test_hue_error_handling(self):
        """Test handling of HueError from manager."""
        with patch('hue_mcp.tools.light_control.LightManager') as mock_manager_class:
            # Setup mock to raise HueError
            mock_manager = AsyncMock()
            mock_manager_class.return_value = mock_manager
            mock_manager.get_light_status.side_effect = HueValidationError("Light not found")
            
            # Test
            result = await light_control.hue_get_light_state.fn(light_id=1)
            
            # Assertions
            result_dict = json.loads(result)
            assert result_dict["success"] is False
            assert "Light not found" in result_dict["message"]
            assert result_dict["data"]["error_type"] == "HueValidationError"
    
    async def test_unexpected_error_handling(self):
        """Test handling of unexpected errors."""
        with patch('hue_mcp.tools.light_control.LightManager') as mock_manager_class:
            # Setup mock to raise unexpected error
            mock_manager = AsyncMock()
            mock_manager_class.return_value = mock_manager
            mock_manager.get_light_status.side_effect = RuntimeError("Unexpected error")
            
            # Test
            result = await light_control.hue_get_light_state.fn(light_id=1)
            
            # Assertions
            result_dict = json.loads(result)
            assert result_dict["success"] is False
            assert "An unexpected error occurred" in result_dict["message"]
            assert result_dict["data"]["error_type"] == "UnexpectedError"