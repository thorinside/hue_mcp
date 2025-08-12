"""MCP tools for individual light control."""

import logging
from typing import Optional

from pydantic import ValidationError

from ..hue_client import HueError
from ..light_manager import HueResponse, LightControlRequest, LightManager

# Import the shared MCP instance
from ..mcp_instance import mcp

logger = logging.getLogger(__name__)


@mcp.tool()
async def hue_control_light(
    light_id: int,
    action: str,
    brightness: Optional[int] = 200,
    color_temp: Optional[int] = 366,
) -> str:
    """
    Control individual Hue light by ID.

    Args:
        light_id: Light ID (1-17)
        action: "on", "off", or "toggle"
        brightness: Brightness level (1-254), default 200
        color_temp: Color temperature (154-500), default 366

    Returns:
        JSON string with operation result
    """
    try:
        # Input validation with Pydantic
        request = LightControlRequest(
            light_id=light_id,
            action=action,
            brightness=brightness,
            color_temp=color_temp,
        )

        # Business logic delegation to manager
        manager = LightManager()
        result = await manager.control_light(request)

        logger.info(f"Light control tool executed: light {light_id} {action}")

        return result.model_dump_json()

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
        logger.error(f"Unexpected error in hue_control_light: {e}")
        error_response = HueResponse(
            success=False,
            message="An unexpected error occurred",
            data={"error_type": "UnexpectedError"},
        )
        return error_response.model_dump_json()


@mcp.tool()
async def hue_get_light_state(light_id: int) -> str:
    """
    Get the current state of a specific Hue light.

    Args:
        light_id: Light ID (1-17)

    Returns:
        JSON string with light state information
    """
    try:
        # Validate light ID
        if not isinstance(light_id, int) or light_id < 1 or light_id > 17:
            raise ValueError(
                f"Light ID must be an integer between 1 and 17, got {light_id}"
            )

        # Business logic delegation to manager
        manager = LightManager()
        result = await manager.get_light_status(light_id)

        logger.info(f"Light state query executed: light {light_id}")

        return result.model_dump_json()

    except ValueError as e:
        error_response = HueResponse(
            success=False, message=str(e), data={"error_type": "ValidationError"}
        )
        return error_response.model_dump_json()

    except HueError as e:
        error_response = HueResponse(
            success=False, message=str(e), data={"error_type": type(e).__name__}
        )
        return error_response.model_dump_json()

    except Exception as e:
        logger.error(f"Unexpected error in hue_get_light_state: {e}")
        error_response = HueResponse(
            success=False,
            message="An unexpected error occurred",
            data={"error_type": "UnexpectedError"},
        )
        return error_response.model_dump_json()
