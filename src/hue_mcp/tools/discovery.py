"""MCP tools for light discovery and bridge connectivity."""

import logging

from ..hue_client import HueError
from ..light_manager import HueResponse, LightManager

# Import the shared MCP instance
from ..mcp_instance import mcp

logger = logging.getLogger(__name__)


@mcp.tool()
async def hue_list_lights() -> str:
    """
    List all Hue lights and their current states.

    Returns:
        JSON string with all lights and their information
    """
    try:
        # Business logic delegation to manager
        manager = LightManager()
        result = await manager.list_all_lights()

        logger.info("Light discovery tool executed: listed all lights")

        return result.model_dump_json()

    except HueError as e:
        error_response = HueResponse(
            success=False, message=str(e), data={"error_type": type(e).__name__}
        )
        return error_response.model_dump_json()

    except Exception as e:
        logger.error(f"Unexpected error in hue_list_lights: {e}")
        error_response = HueResponse(
            success=False,
            message="An unexpected error occurred",
            data={"error_type": "UnexpectedError"},
        )
        return error_response.model_dump_json()


@mcp.tool()
async def hue_discover_bridge() -> str:
    """
    Test connectivity to the Hue bridge and return bridge information.

    Returns:
        JSON string with bridge connectivity status and information
    """
    try:
        # Business logic delegation to manager
        manager = LightManager()
        result = await manager.discover_bridge()

        logger.info("Bridge discovery tool executed: tested bridge connectivity")

        return result.model_dump_json()

    except HueError as e:
        error_response = HueResponse(
            success=False, message=str(e), data={"error_type": type(e).__name__}
        )
        return error_response.model_dump_json()

    except Exception as e:
        logger.error(f"Unexpected error in hue_discover_bridge: {e}")
        error_response = HueResponse(
            success=False,
            message="An unexpected error occurred",
            data={"error_type": "UnexpectedError"},
        )
        return error_response.model_dump_json()
