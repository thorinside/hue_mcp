"""Unit tests for AsyncHueClient."""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from hue_mcp.hue_client import (
    AsyncHueClient, 
    HueError, 
    HueConnectionError, 
    HueTimeoutError, 
    HueValidationError,
    HueRateLimiter
)


class TestHueRateLimiter:
    """Test rate limiting functionality."""
    
    @pytest_asyncio.fixture
    async def rate_limiter(self):
        """Create a rate limiter for testing."""
        return HueRateLimiter()
    
    async def test_light_token_acquisition(self, rate_limiter):
        """Test acquiring light tokens."""
        # Should not raise any exceptions
        await rate_limiter.acquire_light_token()
        await rate_limiter.acquire_light_token()
    
    async def test_group_token_acquisition(self, rate_limiter):
        """Test acquiring group tokens."""
        import time
        start_time = time.time()
        
        # First call should be immediate
        await rate_limiter.acquire_group_token()
        
        # Second call should enforce delay
        await rate_limiter.acquire_group_token()
        
        elapsed = time.time() - start_time
        # Should take at least 1 second for the second call
        assert elapsed >= 1.0


class TestAsyncHueClient:
    """Test AsyncHueClient functionality."""
    
    @pytest_asyncio.fixture
    async def hue_client(self):
        """Create a Hue client for testing."""
        return AsyncHueClient()
    
    async def test_context_manager(self, hue_client):
        """Test async context manager functionality."""
        async with hue_client as client:
            assert client._client is not None
        # Client should be closed after exiting context
    
    @patch('hue_mcp.hue_client.httpx.AsyncClient')
    async def test_get_lights_success(self, mock_client_class, hue_client, mock_lights_response):
        """Test successful lights retrieval."""
        # Setup mock
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_lights_response
        mock_response.raise_for_status.return_value = None
        mock_client.get.return_value = mock_response
        
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client_class.return_value.__aexit__.return_value = None
        
        # Test
        result = await hue_client.get_lights()
        
        # Assertions
        assert result == mock_lights_response
        mock_client.get.assert_called_once()
    
    @patch('hue_mcp.hue_client.httpx.AsyncClient')
    async def test_get_light_state_success(self, mock_client_class, hue_client):
        """Test successful light state retrieval."""
        # Setup mock
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        light_state = {
            "name": "Test Light",
            "state": {"on": True, "bri": 200, "ct": 366}
        }
        mock_response.json.return_value = light_state
        mock_response.raise_for_status.return_value = None
        mock_client.get.return_value = mock_response
        
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client_class.return_value.__aexit__.return_value = None
        
        # Test
        result = await hue_client.get_light_state(1)
        
        # Assertions
        assert result == light_state
        mock_client.get.assert_called_once()
    
    @patch('hue_mcp.hue_client.httpx.AsyncClient')
    async def test_control_light_success(self, mock_client_class, hue_client, mock_hue_response_success):
        """Test successful light control."""
        # Setup mock
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_hue_response_success
        mock_response.raise_for_status.return_value = None
        mock_client.put.return_value = mock_response
        
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client_class.return_value.__aexit__.return_value = None
        
        # Test
        state = {"on": True, "bri": 200}
        result = await hue_client.control_light(1, state)
        
        # Assertions
        assert result == mock_hue_response_success[0]
        mock_client.put.assert_called_once()
    
    @patch('hue_mcp.hue_client.httpx.AsyncClient')
    async def test_control_group_success(self, mock_client_class, hue_client, mock_hue_response_success):
        """Test successful group control."""
        # Setup mock
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_hue_response_success
        mock_response.raise_for_status.return_value = None
        mock_client.put.return_value = mock_response
        
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client_class.return_value.__aexit__.return_value = None
        
        # Test
        action = {"on": True}
        result = await hue_client.control_group(0, action)
        
        # Assertions
        assert result == mock_hue_response_success[0]
        mock_client.put.assert_called_once()
    
    @patch('hue_mcp.hue_client.httpx.AsyncClient')
    async def test_404_error_handling(self, mock_client_class, hue_client):
        """Test 404 error handling."""
        # Setup mock
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_client.get.return_value = mock_response
        
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client_class.return_value.__aexit__.return_value = None
        
        # Test
        with pytest.raises(HueValidationError):
            await hue_client.get_lights()
    
    @patch('hue_mcp.hue_client.httpx.AsyncClient')
    async def test_401_error_handling(self, mock_client_class, hue_client):
        """Test 401 error handling."""
        # Setup mock
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_client.get.return_value = mock_response
        
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client_class.return_value.__aexit__.return_value = None
        
        # Test
        with pytest.raises(HueConnectionError):
            await hue_client.get_lights()
    
    @patch('hue_mcp.hue_client.httpx.AsyncClient')
    async def test_hue_api_error_handling(self, mock_client_class, hue_client, mock_hue_response_error):
        """Test Hue API error response handling."""
        # Setup mock
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_hue_response_error
        mock_response.raise_for_status.return_value = None
        mock_client.get.return_value = mock_response
        
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client_class.return_value.__aexit__.return_value = None
        
        # Test
        with pytest.raises(HueError):
            await hue_client.get_lights()
    
    @patch('hue_mcp.hue_client.httpx.AsyncClient')
    async def test_timeout_error_handling(self, mock_client_class, hue_client):
        """Test timeout error handling."""
        # Setup mock
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.TimeoutException("Timeout")
        
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client_class.return_value.__aexit__.return_value = None
        
        # Test
        with pytest.raises(HueTimeoutError):
            await hue_client.get_lights()
    
    @patch('hue_mcp.hue_client.httpx.AsyncClient')
    async def test_connection_error_handling(self, mock_client_class, hue_client):
        """Test connection error handling."""
        # Setup mock
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.RequestError("Connection failed")
        
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client_class.return_value.__aexit__.return_value = None
        
        # Test
        with pytest.raises(HueConnectionError):
            await hue_client.get_lights()
    
    @patch('hue_mcp.hue_client.httpx.AsyncClient')
    async def test_rate_limit_retry(self, mock_client_class, hue_client):
        """Test rate limit retry behavior."""
        # Setup mock
        mock_client = AsyncMock()
        
        # First call returns 429, second call succeeds
        mock_response_429 = MagicMock()
        mock_response_429.status_code = 429
        
        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {"success": True}
        mock_response_200.raise_for_status.return_value = None
        
        mock_client.get.side_effect = [mock_response_429, mock_response_200]
        
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client_class.return_value.__aexit__.return_value = None
        
        # Test
        result = await hue_client.get_lights()
        
        # Assertions
        assert result == {"success": True}
        assert mock_client.get.call_count == 2
    
    @patch('hue_mcp.hue_client.httpx.AsyncClient')
    async def test_get_config_success(self, mock_client_class, hue_client, mock_bridge_config):
        """Test successful bridge config retrieval."""
        # Setup mock
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_bridge_config
        mock_response.raise_for_status.return_value = None
        mock_client.get.return_value = mock_response
        
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client_class.return_value.__aexit__.return_value = None
        
        # Test
        result = await hue_client.get_config()
        
        # Assertions
        assert result == mock_bridge_config
        mock_client.get.assert_called_once()
    
    @patch('hue_mcp.hue_client.httpx.AsyncClient')
    async def test_test_connection_success(self, mock_client_class, hue_client, mock_bridge_config):
        """Test successful connection test."""
        # Setup mock
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_bridge_config
        mock_response.raise_for_status.return_value = None
        mock_client.get.return_value = mock_response
        
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client_class.return_value.__aexit__.return_value = None
        
        # Test
        result = await hue_client.test_connection()
        
        # Assertions
        assert result is True
    
    @patch('hue_mcp.hue_client.httpx.AsyncClient')
    async def test_test_connection_failure(self, mock_client_class, hue_client):
        """Test failed connection test."""
        # Setup mock
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.RequestError("Connection failed")
        
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client_class.return_value.__aexit__.return_value = None
        
        # Test
        result = await hue_client.test_connection()
        
        # Assertions
        assert result is False