# FastMCP Async Patterns and Performance Optimization

## Error Handling and Performance Optimization

### FastMCP Server Setup Pattern
```python
from fastmcp import FastMCP
import logging
import asyncio
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create MCP server instance
mcp = FastMCP("Hue Control Server")

# Global resource management
_resource_manager = None

@asynccontextmanager
async def lifespan():
    """Manage server lifespan with proper resource cleanup."""
    global _resource_manager
    try:
        logger.info("Starting Hue MCP server...")
        _resource_manager = HueResourceManager()
        await _resource_manager.initialize()
        yield
    finally:
        logger.info("Shutting down Hue MCP server...")
        if _resource_manager:
            await _resource_manager.cleanup()

# Set lifespan context
mcp.set_lifespan(lifespan)
```

### MCP Tool Definition Pattern
```python
from typing import Optional
import json
from pydantic import BaseModel, ValidationError

@mcp.tool()
async def hue_control_light(
    light_id: int,
    action: str,
    brightness: Optional[int] = 200,
    color_temp: Optional[int] = 366,
    ctx: Optional[mcp.Context] = None
) -> str:
    """
    Control individual Hue light by ID.
    
    Args:
        light_id: Light ID (1-17)
        action: "on", "off", or "toggle"
        brightness: Brightness level (1-254), default 200
        color_temp: Color temperature (154-500), default 366
        ctx: MCP context for progress reporting
    
    Returns:
        JSON string with operation result
    """
    # CRITICAL: Always return JSON string from MCP tools
    try:
        # Input validation with Pydantic
        request = LightControlRequest(
            light_id=light_id,
            action=action,
            brightness=brightness,
            color_temp=color_temp
        )
        
        # Progress reporting
        if ctx:
            await ctx.info(f"Controlling light {light_id} - {action}")
            await ctx.report_progress(0.1, 1.0, "Starting light control")
        
        # Business logic delegation
        async with get_hue_manager() as manager:
            result = await manager.control_light(request)
        
        if ctx:
            await ctx.report_progress(1.0, 1.0, "Light control completed")
            await ctx.debug(f"Successfully controlled light {light_id}")
        
        # CRITICAL: Always return JSON string
        return result.model_dump_json()
        
    except ValidationError as e:
        error_response = HueResponse(
            success=False,
            message=f"Invalid parameters: {e}",
            data={"validation_errors": e.errors()}
        )
        return error_response.model_dump_json()
        
    except HueError as e:
        if ctx:
            await ctx.debug(f"Hue error: {str(e)}")
        error_response = HueResponse(
            success=False,
            message=str(e),
            data={"error_type": type(e).__name__}
        )
        return error_response.model_dump_json()
        
    except Exception as e:
        logger.error(f"Unexpected error in hue_control_light: {e}")
        if ctx:
            await ctx.debug(f"Unexpected error: {str(e)}")
        error_response = HueResponse(
            success=False,
            message="An unexpected error occurred",
            data={"error_type": "UnexpectedError"}
        )
        return error_response.model_dump_json()
```

### Async Resource Management Pattern
```python
import httpx
import asyncio
from typing import Optional, Dict, Any
import weakref

class HueResourceManager:
    """Manage HTTP clients and connections for Hue API."""
    
    def __init__(self):
        self._clients: Dict[str, httpx.AsyncClient] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
        self._cleanup_tasks: Dict[str, asyncio.Task] = {}
        self.rate_limiter = HueRateLimiter()
    
    async def initialize(self):
        """Initialize resource manager."""
        logger.info("Initializing Hue resource manager...")
        # Pre-warm connection to bridge
        await self._warmup_connection()
    
    async def cleanup(self):
        """Clean up all resources."""
        logger.info("Cleaning up Hue resources...")
        
        # Cancel cleanup tasks
        for task in self._cleanup_tasks.values():
            task.cancel()
        self._cleanup_tasks.clear()
        
        # Close all clients
        for client in self._clients.values():
            await client.aclose()
        self._clients.clear()
        
        logger.info("Hue resource cleanup completed")
    
    @asynccontextmanager
    async def get_client(self, name: str = "default"):
        """Get or create HTTP client with connection pooling."""
        if name not in self._locks:
            self._locks[name] = asyncio.Lock()
        
        async with self._locks[name]:
            if name not in self._clients:
                # Create new client with optimized settings
                self._clients[name] = httpx.AsyncClient(
                    timeout=httpx.Timeout(connect=5.0, read=10.0),
                    limits=httpx.Limits(
                        max_connections=10,
                        max_keepalive_connections=5
                    ),
                    http2=True
                )
                
                # Schedule cleanup after idle period
                self._schedule_cleanup(name, idle_timeout=300)
        
        try:
            yield self._clients[name]
        finally:
            # Reset cleanup timer
            self._schedule_cleanup(name, idle_timeout=300)
    
    def _schedule_cleanup(self, name: str, idle_timeout: float):
        """Schedule client cleanup after idle period."""
        # Cancel existing cleanup
        if name in self._cleanup_tasks:
            self._cleanup_tasks[name].cancel()
        
        # Schedule new cleanup
        self._cleanup_tasks[name] = asyncio.create_task(
            self._cleanup_after_delay(name, idle_timeout)
        )
    
    async def _cleanup_after_delay(self, name: str, delay: float):
        """Clean up client after delay."""
        try:
            await asyncio.sleep(delay)
            async with self._locks.get(name, asyncio.Lock()):
                if name in self._clients:
                    await self._clients[name].aclose()
                    del self._clients[name]
                if name in self._cleanup_tasks:
                    del self._cleanup_tasks[name]
        except asyncio.CancelledError:
            pass
    
    async def _warmup_connection(self):
        """Warm up connection to Hue bridge."""
        try:
            async with self.get_client() as client:
                response = await client.get(f"{HUE_BASE_URL}/config")
                if response.status_code == 200:
                    logger.info("Hue bridge connection warmed up successfully")
                else:
                    logger.warning(f"Hue bridge warmup returned status {response.status_code}")
        except Exception as e:
            logger.warning(f"Failed to warm up Hue bridge connection: {e}")

# Global resource manager
_resource_manager: Optional[HueResourceManager] = None

@asynccontextmanager
async def get_hue_manager():
    """Get global Hue resource manager."""
    global _resource_manager
    if _resource_manager is None:
        raise RuntimeError("Hue resource manager not initialized")
    yield _resource_manager
```

### Advanced Error Handling Pattern
```python
import functools
import time
from typing import Callable, TypeVar, Any

T = TypeVar('T')

def with_hue_error_handling(
    retries: int = 3,
    backoff_factor: float = 1.0,
    timeout: float = 30.0
):
    """Decorator for robust error handling in MCP tools."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            start_time = time.time()
            last_exception = None
            
            for attempt in range(retries):
                # Check timeout
                if time.time() - start_time > timeout:
                    raise HueTimeoutError(f"Operation timed out after {timeout}s")
                
                try:
                    return await func(*args, **kwargs)
                    
                except (HueConnectionError, HueTimeoutError, httpx.RequestError) as e:
                    last_exception = e
                    if attempt < retries - 1:
                        delay = backoff_factor * (2 ** attempt)
                        logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                        await asyncio.sleep(delay)
                    else:
                        logger.error(f"All {retries} attempts failed. Last error: {e}")
                
                except HueValidationError as e:
                    # Don't retry validation errors
                    logger.error(f"Validation error: {e}")
                    raise
                
                except Exception as e:
                    logger.error(f"Unexpected error: {e}")
                    raise HueError(f"Unexpected error: {e}") from e
            
            # All retries failed
            raise HueConnectionError(f"Failed after {retries} attempts: {last_exception}")
        
        return wrapper
    return decorator

# Usage in MCP tools
@mcp.tool()
@with_hue_error_handling(retries=3, backoff_factor=1.5)
async def robust_hue_control_light(light_id: int, action: str) -> str:
    """Robust light control with automatic retries."""
    # Implementation here...
    pass
```

### Concurrent Operations Pattern
```python
import asyncio
from typing import List, Dict, Any, Callable

class ConcurrentHueOperations:
    """Manage concurrent Hue operations with rate limiting."""
    
    def __init__(self, max_concurrent: int = 5):
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.rate_limiter = HueRateLimiter()
    
    async def execute_concurrent_light_operations(
        self,
        operations: List[Dict[str, Any]],
        progress_callback: Optional[Callable] = None
    ) -> List[Dict[str, Any]]:
        """Execute multiple light operations concurrently."""
        
        async def execute_single_operation(op: Dict[str, Any], index: int) -> Dict[str, Any]:
            async with self.semaphore:
                try:
                    # Apply rate limiting
                    await self.rate_limiter.acquire_light_token()
                    
                    # Execute operation
                    result = await self._execute_operation(op)
                    
                    # Report progress
                    if progress_callback:
                        await progress_callback(index + 1, len(operations))
                    
                    return {
                        "operation": op,
                        "result": result,
                        "success": True,
                        "index": index
                    }
                    
                except Exception as e:
                    logger.error(f"Operation {index} failed: {e}")
                    return {
                        "operation": op,
                        "error": str(e),
                        "success": False,
                        "index": index
                    }
        
        # Create tasks for all operations
        tasks = [
            asyncio.create_task(execute_single_operation(op, i))
            for i, op in enumerate(operations)
        ]
        
        # Execute all operations concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        successful = [r for r in results if isinstance(r, dict) and r.get("success")]
        failed = [r for r in results if isinstance(r, dict) and not r.get("success")]
        
        logger.info(f"Concurrent operations completed: {len(successful)} successful, {len(failed)} failed")
        
        return results
    
    async def _execute_operation(self, operation: Dict[str, Any]) -> Any:
        """Execute single Hue operation."""
        op_type = operation.get("type")
        
        if op_type == "control_light":
            return await self._control_light_operation(operation)
        elif op_type == "get_light_state":
            return await self._get_light_state_operation(operation)
        else:
            raise ValueError(f"Unknown operation type: {op_type}")
    
    async def _control_light_operation(self, operation: Dict[str, Any]) -> Dict[str, Any]:
        """Execute light control operation."""
        async with get_hue_manager() as manager:
            async with manager.get_client() as client:
                response = await client.put(
                    f"{HUE_BASE_URL}/lights/{operation['light_id']}/state",
                    json=operation['state']
                )
                response.raise_for_status()
                return response.json()

# Usage in room control tool
@mcp.tool()
async def hue_control_room_concurrent(
    room: str,
    action: str,
    brightness: Optional[int] = 200,
    ctx: Optional[mcp.Context] = None
) -> str:
    """Control room lights with optimized concurrent operations."""
    
    if room not in ROOM_MAPPINGS:
        raise HueValidationError(f"Unknown room: {room}")
    
    light_ids = ROOM_MAPPINGS[room]
    
    # Build operations list
    operations = []
    for light_id in light_ids:
        state = {"on": action == "on"}
        if action == "on" and brightness:
            state["bri"] = brightness
        
        operations.append({
            "type": "control_light",
            "light_id": light_id,
            "state": state
        })
    
    # Progress reporting callback
    async def progress_callback(completed: int, total: int):
        if ctx:
            await ctx.report_progress(completed / total, 1.0, f"Controlled {completed}/{total} lights")
    
    # Execute concurrent operations
    concurrent_ops = ConcurrentHueOperations(max_concurrent=5)
    results = await concurrent_ops.execute_concurrent_light_operations(
        operations,
        progress_callback
    )
    
    # Process results
    successful = [r for r in results if r.get("success")]
    failed = [r for r in results if not r.get("success")]
    
    response = HueResponse(
        success=len(failed) == 0,
        message=f"Controlled {len(successful)}/{len(light_ids)} lights in {room}",
        lights_affected=light_ids,
        data={
            "successful_operations": len(successful),
            "failed_operations": len(failed),
            "details": results
        }
    )
    
    return response.model_dump_json()
```

### Rate Limiting Implementation
```python
import time
import asyncio
from collections import defaultdict

class HueRateLimiter:
    """Advanced rate limiter for Hue API compliance."""
    
    def __init__(self):
        # Token bucket for lights (10/second)
        self.light_tokens = 10
        self.light_max_tokens = 10
        self.light_refill_rate = 10  # tokens per second
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
            self.light_tokens = min(self.light_max_tokens, self.light_tokens + tokens_to_add)
            self.light_last_refill = now
            
            # Wait if no tokens available
            while self.light_tokens < 1:
                wait_time = 1.0 / self.light_refill_rate
                await asyncio.sleep(wait_time)
                
                # Try to refill again
                now = time.time()
                elapsed = now - self.light_last_refill
                tokens_to_add = elapsed * self.light_refill_rate
                self.light_tokens = min(self.light_max_tokens, self.light_tokens + tokens_to_add)
                self.light_last_refill = now
            
            # Consume token
            self.light_tokens -= 1
    
    async def acquire_group_token(self):
        """Acquire token for group operation."""
        async with self.group_lock:
            now = time.time()
            time_since_last = now - self.group_last_call
            
            if time_since_last < 1.0:
                # Wait until 1 second has passed
                wait_time = 1.0 - time_since_last
                await asyncio.sleep(wait_time)
            
            self.group_last_call = time.time()
```

### Performance Monitoring Pattern
```python
import time
import psutil
from collections import defaultdict
from typing import Dict, List, Any

class MCPPerformanceMonitor:
    """Monitor MCP tool performance and resource usage."""
    
    def __init__(self):
        self.metrics: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.active_operations = 0
        self._lock = asyncio.Lock()
    
    async def track_operation(self, operation_name: str, func: Callable, *args, **kwargs):
        """Track performance of MCP operation."""
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss
        
        async with self._lock:
            self.active_operations += 1
        
        try:
            result = await func(*args, **kwargs)
            
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss
            
            # Record metrics
            async with self._lock:
                self.metrics[operation_name].append({
                    'duration': end_time - start_time,
                    'memory_delta': end_memory - start_memory,
                    'timestamp': end_time,
                    'success': True
                })
                self.active_operations -= 1
            
            return result
            
        except Exception as e:
            end_time = time.time()
            async with self._lock:
                self.metrics[operation_name].append({
                    'duration': end_time - start_time,
                    'timestamp': end_time,
                    'success': False,
                    'error': str(e)
                })
                self.active_operations -= 1
            raise
    
    def get_stats(self, operation_name: str) -> Dict[str, Any]:
        """Get performance statistics."""
        if operation_name not in self.metrics:
            return {}
        
        metrics = self.metrics[operation_name]
        durations = [m['duration'] for m in metrics if m.get('success')]
        
        if not durations:
            return {'operation': operation_name, 'no_data': True}
        
        return {
            'operation': operation_name,
            'total_calls': len(metrics),
            'successful_calls': len(durations),
            'avg_duration': sum(durations) / len(durations),
            'min_duration': min(durations),
            'max_duration': max(durations),
            'active_operations': self.active_operations
        }

# Global performance monitor
performance_monitor = MCPPerformanceMonitor()

def track_performance(operation_name: str):
    """Decorator to track MCP tool performance."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await performance_monitor.track_operation(
                operation_name, func, *args, **kwargs
            )
        return wrapper
    return decorator

# Usage
@mcp.tool()
@track_performance("hue_control_light")
async def monitored_hue_control_light(light_id: int, action: str) -> str:
    """Light control with performance monitoring."""
    # Implementation here...
    pass
```

### Server Startup and Shutdown Pattern
```python
def main():
    """Main entry point for MCP server."""
    import signal
    import sys
    
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        sys.exit(0)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        logger.info("Starting Hue MCP server...")
        
        # Run the server
        mcp.run()
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)
    finally:
        logger.info("Hue MCP server shutdown complete")

if __name__ == "__main__":
    main()
```

This comprehensive guide provides production-ready patterns for FastMCP server development with proper async handling, error management, resource cleanup, and performance optimization specifically designed for external API integration like Philips Hue control.