# Philips Hue API Patterns and Integration Guide

## Authentication and Rate Limiting

### Authentication Flow
```python
# One-time bridge setup (already completed for this implementation)
bridge_ip = "192.168.1.64"
username = "cJdzxhKlxr2h92jwDkTv-DvpOxglPxn147UEg1Gp"  # Pre-configured

# API Base URL Pattern
base_url = f"http://{bridge_ip}/api/{username}"
```

### Rate Limiting Requirements
- **Individual Lights**: Maximum 10 commands per second
- **Groups**: Maximum 1 command per second
- **Discovery/Status**: No specific limits, but use reasonable spacing

### Rate Limiting Implementation
```python
import asyncio

class HueRateLimiter:
    def __init__(self):
        self.light_semaphore = asyncio.Semaphore(10)  # 10 concurrent light ops
        self.group_semaphore = asyncio.Semaphore(1)   # 1 concurrent group op
        self.last_group_call = 0
    
    async def control_light(self, func, *args, **kwargs):
        async with self.light_semaphore:
            return await func(*args, **kwargs)
    
    async def control_group(self, func, *args, **kwargs):
        async with self.group_semaphore:
            # Ensure 1-second spacing between group calls
            now = time.time()
            time_since_last = now - self.last_group_call
            if time_since_last < 1.0:
                await asyncio.sleep(1.0 - time_since_last)
            
            result = await func(*args, **kwargs)
            self.last_group_call = time.time()
            return result
```

## API Endpoints and Payloads

### Light Control Endpoints
```python
# Get all lights
GET /api/{username}/lights
# Response: {"1": {"name": "Light 1", "state": {...}}, ...}

# Get specific light
GET /api/{username}/lights/{light_id}
# Response: {"name": "Light 1", "state": {"on": true, "bri": 200, ...}, ...}

# Control light state
PUT /api/{username}/lights/{light_id}/state
# Payload examples:
{"on": true}                                    # Turn on
{"on": false}                                   # Turn off  
{"on": true, "bri": 128}                       # On with 50% brightness
{"on": true, "bri": 200, "ct": 250}           # On with brightness and color temp
{"bri": 100}                                   # Just change brightness (if already on)
```

### Group Control Endpoints
```python
# Get all groups
GET /api/{username}/groups
# Response: {"1": {"name": "Kitchen", "lights": ["10", "12"], ...}, ...}

# Control group (all lights in group)
PUT /api/{username}/groups/{group_id}/action
# Note: Use "action" for groups, "state" for individual lights

# Special group 0 = All lights
PUT /api/{username}/groups/0/action
{"on": false}  # Turn off all lights in system
```

## Error Handling Patterns

### HTTP Status Codes
- **200**: Success
- **400**: Bad Request (invalid JSON/parameters)
- **401**: Unauthorized (invalid username)
- **404**: Not Found (invalid light ID/endpoint)
- **429**: Too Many Requests (rate limited)
- **500**: Internal Server Error

### Hue API Error Response Format
```python
# Error responses are arrays with error objects
[{
    "error": {
        "type": 1,                          # Error type code
        "address": "/lights/99/state",      # Failed endpoint
        "description": "resource, /lights/99, not available"
    }
}]

# Success responses vary by operation
[{"success": {"/lights/1/state/on": true}}]  # Light control success
[{"success": {"/groups/0/action/on": false}}] # Group control success
```

### Custom Exception Hierarchy
```python
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
```

## Request/Response Patterns

### Robust HTTP Request Pattern
```python
import httpx
import asyncio
from typing import Optional, Dict, Any

async def safe_hue_request(
    client: httpx.AsyncClient,
    endpoint: str,
    method: str = "GET",
    data: Optional[Dict[str, Any]] = None,
    retries: int = 3
) -> Dict[str, Any]:
    """Make safe request to Hue API with retries."""
    
    for attempt in range(retries):
        try:
            if method.upper() == "GET":
                response = await client.get(endpoint)
            elif method.upper() == "PUT":
                response = await client.put(endpoint, json=data)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            # Handle specific status codes
            if response.status_code == 429:
                # Rate limited - wait and retry
                await asyncio.sleep(1.0 * (2 ** attempt))
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
                raise HueError(f"Hue API error: {error.get('description', 'Unknown error')}")
            
            return result
            
        except httpx.TimeoutException as e:
            if attempt == retries - 1:
                raise HueTimeoutError(f"Request timeout after {retries} attempts: {e}")
            await asyncio.sleep(0.5 * (2 ** attempt))
            
        except httpx.RequestError as e:
            if attempt == retries - 1:
                raise HueConnectionError(f"Request failed after {retries} attempts: {e}")
            await asyncio.sleep(0.5 * (2 ** attempt))
    
    raise HueConnectionError("Unexpected error in request handling")
```

## Light ID and Room Mappings

### Complete Light Mapping (from PRD)
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

ROOM_MAPPINGS = {
    "kitchen": [10, 12, 13, 17],        # stove_1, toaster_1, toaster_2, stove_2
    "bedroom": [1, 4],                  # neals_lamp, bonnies_lamp
    "office": [7],                      # office
    "basement": [5, 6, 14, 15, 16],     # basement_e, basement_w, stairway, batcave_color_1, batcave_color_2
    "living_room": [3],                 # small_reading_lamp
    "all": 0                            # Special group ID for all lights
}
```

### Room Control Implementation Pattern
```python
async def control_room_lights(room: str, action: str, **kwargs) -> Dict[str, Any]:
    """Control all lights in a room concurrently."""
    
    if room not in ROOM_MAPPINGS:
        raise HueValidationError(f"Unknown room: {room}")
    
    if room == "all":
        # Use group 0 for all lights (more efficient)
        return await control_group(0, action, **kwargs)
    
    light_ids = ROOM_MAPPINGS[room]
    
    # Control lights concurrently with rate limiting
    semaphore = asyncio.Semaphore(5)  # Limit concurrent operations
    
    async def control_single_light(light_id: int):
        async with semaphore:
            try:
                return await control_light(light_id, action, **kwargs)
            except Exception as e:
                return {"light_id": light_id, "error": str(e), "success": False}
    
    # Execute all operations concurrently
    tasks = [control_single_light(light_id) for light_id in light_ids]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results
    successful = [r for r in results if isinstance(r, dict) and r.get("success", True)]
    failed = [r for r in results if isinstance(r, dict) and not r.get("success", True)]
    
    return {
        "success": len(failed) == 0,
        "message": f"Controlled {len(successful)}/{len(light_ids)} lights in {room}",
        "lights_affected": light_ids,
        "results": results
    }
```

## Performance Optimization Patterns

### Connection Pooling
```python
# Use single httpx.AsyncClient with connection pooling
import httpx

class OptimizedHueClient:
    def __init__(self):
        self.timeout = httpx.Timeout(connect=5.0, read=10.0)
        self.limits = httpx.Limits(
            max_connections=10,
            max_keepalive_connections=5
        )
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            timeout=self.timeout,
            limits=self.limits,
            http2=True  # Enable HTTP/2 for better performance
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()
```

### Caching for Read Operations
```python
import time
from typing import Optional

class HueCache:
    def __init__(self, ttl: float = 60.0):
        self.ttl = ttl
        self.cache: Dict[str, Dict[str, Any]] = {}
    
    def get(self, key: str) -> Optional[Any]:
        if key not in self.cache:
            return None
        
        entry = self.cache[key]
        if time.time() - entry["timestamp"] > self.ttl:
            del self.cache[key]
            return None
        
        return entry["data"]
    
    def put(self, key: str, data: Any):
        self.cache[key] = {
            "data": data,
            "timestamp": time.time()
        }

# Use cache for frequently accessed data
cache = HueCache(ttl=30.0)  # 30-second cache for light states

async def get_lights_cached():
    cached = cache.get("all_lights")
    if cached:
        return cached
    
    result = await get_lights()
    cache.put("all_lights", result)
    return result
```

## Testing Patterns

### Mock Response Patterns
```python
# Typical successful light control response
MOCK_LIGHT_CONTROL_SUCCESS = [{"success": {"/lights/1/state/on": True}}]

# Typical error response
MOCK_LIGHT_NOT_FOUND = [{
    "error": {
        "type": 3,
        "address": "/lights/99",
        "description": "resource, /lights/99, not available"
    }
}]

# Light list response
MOCK_LIGHTS_RESPONSE = {
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
```