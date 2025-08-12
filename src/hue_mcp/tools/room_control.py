"""MCP tools for room-based light control with concurrent operations."""

import logging
from typing import Optional

from pydantic import ValidationError

from ..config import ROOM_MAPPINGS
from ..hue_client import HueError
from ..light_manager import HueResponse, LightManager, RoomControlRequest

# Import the shared MCP instance
from ..mcp_instance import mcp

logger = logging.getLogger(__name__)


@mcp.tool()
async def hue_control_room(
    room: str,
    action: str,
    brightness: Optional[int] = 200,
    color_temp: Optional[int] = 366,
    red: Optional[int] = None,
    green: Optional[int] = None,
    blue: Optional[int] = None,
    hue: Optional[int] = None,
    saturation: Optional[int] = None,
) -> str:
    """
    Control all lights in a room concurrently with color support.

    Args:
        room: Room name (kitchen, bedroom, office, basement, living_room, all)
        action: "on", "off", or "toggle"
        brightness: Brightness level (1-254), default 200
        color_temp: Color temperature (154-500), default 366
        red: Red component (0-255) for RGB color
        green: Green component (0-255) for RGB color
        blue: Blue component (0-255) for RGB color
        hue: Hue value (0-65535) for HSB color
        saturation: Saturation (0-254) for HSB color

    Returns:
        JSON string with operation result and lights affected
        
    Note:
        Color priority: RGB > hue/saturation > color_temp
        RGB requires all three components (red, green, blue)
        HSB requires both hue and saturation
    """
    try:
        # Validate room name
        if room not in ROOM_MAPPINGS:
            available_rooms = list(ROOM_MAPPINGS.keys())
            raise ValueError(
                f"Unknown room '{room}'. Available rooms: {available_rooms}"
            )

        # Input validation with Pydantic
        request = RoomControlRequest(
            room=room, 
            action=action, 
            brightness=brightness, 
            color_temp=color_temp,
            red=red,
            green=green,
            blue=blue,
            hue=hue,
            saturation=saturation,
        )

        # Business logic delegation to manager
        manager = LightManager()
        result = await manager.control_room(request)

        lights_count = len(ROOM_MAPPINGS[room]) if room != "all" else "all"
        logger.info(
            f"Room control tool executed: {room} ({lights_count} lights) {action}"
        )

        return result.model_dump_json()

    except ValueError as e:
        error_response = HueResponse(
            success=False, message=str(e), data={"error_type": "ValidationError"}
        )
        return error_response.model_dump_json()

    except ValidationError as e:
        error_response = HueResponse(
            success=False,
            message=f"Invalid parameters: {e}",
            data={"validation_errors": e.errors()},
        )
        return error_response.model_dump_json()

    except HueError as e:
        error_response = HueResponse(
            success=False, message=str(e), data={"error_type": type(e).__name__}
        )
        return error_response.model_dump_json()

    except Exception as e:
        logger.error(f"Unexpected error in hue_control_room: {e}")
        error_response = HueResponse(
            success=False,
            message="An unexpected error occurred",
            data={"error_type": "UnexpectedError"},
        )
        return error_response.model_dump_json()
