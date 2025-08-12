"""Async Hue bridge client with connection pooling and rate limiting."""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

import httpx

from .config import config

logger = logging.getLogger(__name__)


class HueError(Exception):
    """Base exception for all Hue-related errors."""

    pass


class HueConnectionError(HueError):
    """Network/connection related errors."""

    pass


class HueTimeoutError(HueError):
    """Request timeout errors."""

    pass


class HueValidationError(HueError):
    """Parameter validation errors."""

    pass


class HueRateLimitError(HueError):
    """Rate limiting errors."""

    pass


class HueRateLimiter:
    """Rate limiter for Hue API compliance."""

    def __init__(self):
        # Token bucket for lights (10/second)
        self.light_tokens = config.light_rate_limit
        self.light_max_tokens = config.light_rate_limit
        self.light_refill_rate = config.light_rate_limit
        self.light_last_refill = time.time()
        self.light_lock = asyncio.Lock()

        # Simple rate limiter for groups (1/second)
        self.group_last_call = 0
        self.group_lock = asyncio.Lock()

    async def acquire_light_token(self):
        """Acquire token for light operation."""
        async with self.light_lock:
            now = time.time()

            # Refill tokens based on elapsed time
            elapsed = now - self.light_last_refill
            tokens_to_add = elapsed * self.light_refill_rate
            self.light_tokens = min(
                self.light_max_tokens, self.light_tokens + tokens_to_add
            )
            self.light_last_refill = now

            # Wait if no tokens available
            while self.light_tokens < 1:
                wait_time = 1.0 / self.light_refill_rate
                await asyncio.sleep(wait_time)

                # Try to refill again
                now = time.time()
                elapsed = now - self.light_last_refill
                tokens_to_add = elapsed * self.light_refill_rate
                self.light_tokens = min(
                    self.light_max_tokens, self.light_tokens + tokens_to_add
                )
                self.light_last_refill = now

            # Consume token
            self.light_tokens -= 1

    async def acquire_group_token(self):
        """Acquire token for group operation."""
        async with self.group_lock:
            now = time.time()
            time_since_last = now - self.group_last_call

            if time_since_last < config.group_rate_limit:
                # Wait until required time has passed
                wait_time = config.group_rate_limit - time_since_last
                await asyncio.sleep(wait_time)

            self.group_last_call = time.time()


class AsyncHueClient:
    """Async HTTP client for Hue bridge with connection pooling and rate limiting."""

    def __init__(self):
        self.base_url = config.base_url
        self.timeout = httpx.Timeout(
            connect=config.timeout_connect,
            read=config.timeout_read,
            write=5.0,
            pool=5.0,
        )
        self.limits = httpx.Limits(
            max_connections=config.max_connections,
            max_keepalive_connections=config.max_keepalive_connections,
        )
        self.rate_limiter = HueRateLimiter()
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """Async context manager entry."""
        self._client = httpx.AsyncClient(timeout=self.timeout, limits=self.limits)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()

    @asynccontextmanager
    async def _get_client(self):
        """Get HTTP client (context manager for standalone usage)."""
        if self._client:
            yield self._client
        else:
            async with httpx.AsyncClient(
                timeout=self.timeout, limits=self.limits
            ) as client:
                yield client

    async def _safe_request(
        self,
        endpoint: str,
        method: str = "GET",
        data: Optional[Dict[str, Any]] = None,
        retries: int = 3,
    ) -> Dict[str, Any]:
        """Make safe request to Hue API with retries."""

        for attempt in range(retries):
            try:
                async with self._get_client() as client:
                    if method.upper() == "GET":
                        response = await client.get(endpoint)
                    elif method.upper() == "PUT":
                        response = await client.put(endpoint, json=data)
                    else:
                        raise ValueError(f"Unsupported method: {method}")

                    # Handle specific status codes
                    if response.status_code == 429:
                        # Rate limited - wait and retry
                        await asyncio.sleep(1.0 * (2**attempt))
                        continue
                    elif response.status_code == 404:
                        raise HueValidationError(f"Resource not found: {endpoint}")
                    elif response.status_code == 401:
                        raise HueConnectionError("Invalid username/authentication")

                    response.raise_for_status()
                    result = response.json()

                    # Check for Hue API errors in response
                    if isinstance(result, list) and result and "error" in result[0]:
                        error = result[0]["error"]
                        raise HueError(
                            f"Hue API error: {error.get('description', 'Unknown error')}"
                        )

                    # For PUT requests (light control), Hue API returns a list of success/error objects
                    # For GET requests, it returns the data directly
                    if isinstance(result, list) and method.upper() == "PUT":
                        # Handle list of responses from PUT operations
                        if result and isinstance(result[0], dict):
                            if "success" in result[0]:
                                # Return the success object for validation
                                return result[0]
                            elif "error" in result[0]:
                                error = result[0]["error"]
                                raise HueError(
                                    f"Hue API error: {error.get('description', 'Unknown error')}"
                                )
                        # If it's an empty list or unexpected format, return as-is
                        return result

                    return result

            except httpx.TimeoutException as e:
                if attempt == retries - 1:
                    raise HueTimeoutError(
                        f"Request timeout after {retries} attempts: {e}"
                    ) from e
                await asyncio.sleep(0.5 * (2**attempt))

            except httpx.RequestError as e:
                if attempt == retries - 1:
                    raise HueConnectionError(
                        f"Request failed after {retries} attempts: {e}"
                    ) from e
                await asyncio.sleep(0.5 * (2**attempt))

        raise HueConnectionError("Unexpected error in request handling")

    async def get_lights(self) -> Dict[str, Any]:
        """Get all lights from the bridge."""
        endpoint = f"{self.base_url}/lights"
        return await self._safe_request(endpoint, "GET")

    async def get_light_state(self, light_id: int) -> Dict[str, Any]:
        """Get state of a specific light."""
        endpoint = f"{self.base_url}/lights/{light_id}"
        return await self._safe_request(endpoint, "GET")

    async def control_light(
        self, light_id: int, state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Control a specific light with rate limiting."""
        await self.rate_limiter.acquire_light_token()
        endpoint = f"{self.base_url}/lights/{light_id}/state"
        return await self._safe_request(endpoint, "PUT", state)

    async def control_group(
        self, group_id: int, action: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Control a group of lights with rate limiting."""
        await self.rate_limiter.acquire_group_token()
        endpoint = f"{self.base_url}/groups/{group_id}/action"
        return await self._safe_request(endpoint, "PUT", action)

    async def get_groups(self) -> Dict[str, Any]:
        """Get all groups from the bridge."""
        endpoint = f"{self.base_url}/groups"
        return await self._safe_request(endpoint, "GET")

    async def get_config(self) -> Dict[str, Any]:
        """Get bridge configuration."""
        endpoint = f"{self.base_url}/config"
        return await self._safe_request(endpoint, "GET")

    async def test_connection(self) -> bool:
        """Test connection to the bridge."""
        try:
            await self.get_config()
            logger.info("Successfully connected to Hue bridge")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Hue bridge: {e}")
            return False
