"""Philips Hue MCP Server - Model Context Protocol server for Hue light control."""

from .hue_client import (
    AsyncHueClient,
    HueConnectionError,
    HueError,
    HueRateLimitError,
    HueTimeoutError,
    HueValidationError,
)
from .light_manager import (
    HueResponse,
    LightControlRequest,
    LightManager,
    RoomControlRequest,
)

__version__ = "1.0.0"
__author__ = "Claude Code"
__description__ = (
    "MCP server for controlling Philips Hue lights through natural language"
)

__all__ = [
    "HueResponse",
    "LightControlRequest",
    "RoomControlRequest",
    "AsyncHueClient",
    "LightManager",
    "HueError",
    "HueConnectionError",
    "HueTimeoutError",
    "HueValidationError",
    "HueRateLimitError",
]
