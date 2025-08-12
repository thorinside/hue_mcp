"""Light control manager with room mappings and business logic."""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .config import LIGHT_MAPPING, ROOM_MAPPINGS
from .hue_client import AsyncHueClient, HueValidationError

logger = logging.getLogger(__name__)


class LightControlRequest(BaseModel):
    """Request model for individual light control."""

    light_id: int = Field(ge=1, le=17, description="Light ID (1-17)")
    action: str = Field(description="Light action: on, off, toggle")
    brightness: Optional[int] = Field(
        default=200, ge=1, le=254, description="Brightness (1-254)"
    )
    color_temp: Optional[int] = Field(
        default=366, ge=154, le=500, description="Color temperature"
    )
    # RGB color support
    red: Optional[int] = Field(
        default=None, ge=0, le=255, description="Red component (0-255)"
    )
    green: Optional[int] = Field(
        default=None, ge=0, le=255, description="Green component (0-255)"
    )
    blue: Optional[int] = Field(
        default=None, ge=0, le=255, description="Blue component (0-255)"
    )
    # Hue/Saturation color support
    hue: Optional[int] = Field(
        default=None, ge=0, le=65535, description="Hue (0-65535)"
    )
    saturation: Optional[int] = Field(
        default=None, ge=0, le=254, description="Saturation (0-254)"
    )


class RoomControlRequest(BaseModel):
    """Request model for room control."""

    room: str = Field(description="Room name")
    action: str = Field(description="Room action: on, off, toggle")
    brightness: Optional[int] = Field(
        default=200, ge=1, le=254, description="Brightness (1-254)"
    )
    color_temp: Optional[int] = Field(
        default=366, ge=154, le=500, description="Color temperature"
    )
    # RGB color support
    red: Optional[int] = Field(
        default=None, ge=0, le=255, description="Red component (0-255)"
    )
    green: Optional[int] = Field(
        default=None, ge=0, le=255, description="Green component (0-255)"
    )
    blue: Optional[int] = Field(
        default=None, ge=0, le=255, description="Blue component (0-255)"
    )
    # Hue/Saturation color support
    hue: Optional[int] = Field(
        default=None, ge=0, le=65535, description="Hue (0-65535)"
    )
    saturation: Optional[int] = Field(
        default=None, ge=0, le=254, description="Saturation (0-254)"
    )


class HueResponse(BaseModel):
    """Standard response model for Hue operations."""

    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    lights_affected: Optional[List[int]] = None


class LightManager:
    """Manager for Hue light control operations."""

    def __init__(self):
        self.room_mappings = ROOM_MAPPINGS
        self.light_mapping = LIGHT_MAPPING

    def _validate_light_id(self, light_id: int) -> None:
        """Validate light ID is in valid range."""
        if light_id < 1 or light_id > 17:
            raise HueValidationError(f"Light ID {light_id} is not valid. Must be 1-17.")

    def _validate_room(self, room: str) -> None:
        """Validate room name."""
        if room not in self.room_mappings:
            available_rooms = list(self.room_mappings.keys())
            raise HueValidationError(
                f"Unknown room '{room}'. Available rooms: {available_rooms}"
            )

    def _supports_color_temp(self, light_info: Dict[str, Any]) -> bool:
        """Check if light supports color temperature."""
        # Check the light type
        light_type = light_info.get("type", "").lower()

        # Common light types that support color temperature
        color_temp_types = [
            "color temperature light",
            "extended color light",
            "color light",
            "tunable white light",
        ]

        # Check if type matches known color temp supporting types
        if any(ct_type in light_type for ct_type in color_temp_types):
            return True

        # Check capabilities if available
        capabilities = light_info.get("capabilities", {})
        control = capabilities.get("control", {})

        # Check if ct (color temperature) is in the control capabilities
        if "ct" in control:
            return True

        return False

    def _supports_color(self, light_info: Dict[str, Any]) -> bool:
        """Check if light supports color (RGB/HSB)."""
        # Check the light type
        light_type = light_info.get("type", "").lower()

        # Common light types that support color
        color_types = [
            "extended color light",
            "color light",
        ]

        # Check if type matches known color supporting types
        if any(color_type in light_type for color_type in color_types):
            return True

        # Check capabilities if available
        capabilities = light_info.get("capabilities", {})
        control = capabilities.get("control", {})

        # Check if xy, hue, or sat are in the control capabilities
        if any(key in control for key in ["xy", "hue", "sat"]):
            return True

        return False

    def _rgb_to_xy(self, red: int, green: int, blue: int) -> tuple[float, float]:
        """Convert RGB values to Hue xy color space."""
        # Normalize RGB values to 0-1
        r = red / 255.0
        g = green / 255.0
        b = blue / 255.0

        # Apply gamma correction
        r = pow((r + 0.055) / 1.055, 2.4) if r > 0.04045 else r / 12.92
        g = pow((g + 0.055) / 1.055, 2.4) if g > 0.04045 else g / 12.92
        b = pow((b + 0.055) / 1.055, 2.4) if b > 0.04045 else b / 12.92

        # Convert to XYZ color space
        X = r * 0.4124564 + g * 0.3575761 + b * 0.1804375
        Y = r * 0.2126729 + g * 0.7151522 + b * 0.0721750
        Z = r * 0.0193339 + g * 0.1191920 + b * 0.9503041

        # Convert to xy chromaticity coordinates
        if (X + Y + Z) == 0:
            return (0.0, 0.0)
        
        x = X / (X + Y + Z)
        y = Y / (X + Y + Z)

        # Ensure values are within Hue's acceptable range
        x = max(0.0, min(1.0, x))
        y = max(0.0, min(1.0, y))

        return (x, y)

    def _build_light_state(
        self,
        action: str,
        brightness: Optional[int] = None,
        color_temp: Optional[int] = None,
        red: Optional[int] = None,
        green: Optional[int] = None,
        blue: Optional[int] = None,
        hue: Optional[int] = None,
        saturation: Optional[int] = None,
        light_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Build light state dictionary from parameters."""
        state = {}

        if action == "on":
            state["on"] = True
            if brightness is not None:
                state["bri"] = brightness
            
            # Handle color settings - priority: RGB > hue/sat > color_temp
            if light_info is not None and self._supports_color(light_info):
                # RGB color takes priority
                if red is not None and green is not None and blue is not None:
                    x, y = self._rgb_to_xy(red, green, blue)
                    state["xy"] = [x, y]
                # Hue/saturation color
                elif hue is not None and saturation is not None:
                    state["hue"] = hue
                    state["sat"] = saturation
                # Fallback to color temperature if supported
                elif (
                    color_temp is not None
                    and self._supports_color_temp(light_info)
                ):
                    state["ct"] = color_temp
            # Non-color lights can still use color temperature
            elif (
                color_temp is not None
                and light_info is not None
                and self._supports_color_temp(light_info)
            ):
                state["ct"] = color_temp
        elif action == "off":
            state["on"] = False
        elif action == "toggle":
            # For toggle, we'll need to get current state first
            # This will be handled in the control methods
            pass
        else:
            raise HueValidationError(
                f"Invalid action '{action}'. Must be 'on', 'off', or 'toggle'."
            )

        return state

    async def control_light(self, request: LightControlRequest) -> HueResponse:
        """Control individual light."""
        try:
            self._validate_light_id(request.light_id)

            async with AsyncHueClient() as client:
                # Get light info to determine type and capabilities
                light_info = await client.get_light_state(request.light_id)

                # Handle toggle action - need current state
                if request.action == "toggle":
                    current_on = light_info.get("state", {}).get("on", False)
                    new_action = "off" if current_on else "on"
                    state = self._build_light_state(
                        new_action, 
                        request.brightness, 
                        request.color_temp, 
                        request.red,
                        request.green,
                        request.blue,
                        request.hue,
                        request.saturation,
                        light_info
                    )
                else:
                    state = self._build_light_state(
                        request.action,
                        request.brightness,
                        request.color_temp,
                        request.red,
                        request.green,
                        request.blue,
                        request.hue,
                        request.saturation,
                        light_info,
                    )

                # Execute light control
                result = await client.control_light(request.light_id, state)

                logger.info(
                    f"Successfully controlled light {request.light_id}: {request.action}"
                )

                return HueResponse(
                    success=True,
                    message=f"Light {request.light_id} {request.action} successfully",
                    data=result,
                    lights_affected=[request.light_id],
                )

        except Exception as e:
            logger.error(f"Failed to control light {request.light_id}: {e}")
            return HueResponse(
                success=False, message=str(e), data={"error_type": type(e).__name__}
            )

    async def control_room(self, request: RoomControlRequest) -> HueResponse:
        """Control all lights in a room concurrently."""
        try:
            self._validate_room(request.room)

            if request.room == "all":
                # Use group 0 for all lights (more efficient)
                return await self._control_all_lights_group(request)

            light_ids = self.room_mappings[request.room]

            # Control lights concurrently with semaphore to limit concurrent operations
            semaphore = asyncio.Semaphore(5)

            async def control_single_light(light_id: int):
                async with semaphore:
                    try:
                        light_request = LightControlRequest(
                            light_id=light_id,
                            action=request.action,
                            brightness=request.brightness,
                            color_temp=request.color_temp,
                            red=request.red,
                            green=request.green,
                            blue=request.blue,
                            hue=request.hue,
                            saturation=request.saturation,
                        )
                        result = await self.control_light(light_request)
                        return {
                            "light_id": light_id,
                            "result": result,
                            "success": result.success,
                        }
                    except Exception as e:
                        logger.error(f"Failed to control light {light_id}: {e}")
                        return {"light_id": light_id, "error": str(e), "success": False}

            # Execute all operations concurrently
            tasks = [control_single_light(light_id) for light_id in light_ids]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            successful = [
                r for r in results if isinstance(r, dict) and r.get("success", False)
            ]
            failed = [
                r
                for r in results
                if isinstance(r, dict) and not r.get("success", False)
            ]

            success_count = len(successful)
            total_count = len(light_ids)

            logger.info(
                f"Room control completed: {success_count}/{total_count} lights successful"
            )

            return HueResponse(
                success=len(failed) == 0,
                message=f"Controlled {success_count}/{total_count} lights in {request.room}",
                lights_affected=light_ids,
                data={
                    "successful_operations": success_count,
                    "failed_operations": len(failed),
                    "details": results,
                },
            )

        except Exception as e:
            logger.error(f"Failed to control room {request.room}: {e}")
            return HueResponse(
                success=False, message=str(e), data={"error_type": type(e).__name__}
            )

    async def _control_all_lights_group(
        self, request: RoomControlRequest
    ) -> HueResponse:
        """Control all lights using group 0 (more efficient)."""
        try:
            async with AsyncHueClient() as client:
                # Build action for group control
                action = {}

                if request.action == "on":
                    action["on"] = True
                    if request.brightness is not None:
                        action["bri"] = request.brightness
                    
                    # Handle color settings - priority: RGB > hue/sat > color_temp
                    if request.red is not None and request.green is not None and request.blue is not None:
                        x, y = self._rgb_to_xy(request.red, request.green, request.blue)
                        action["xy"] = [x, y]
                    elif request.hue is not None and request.saturation is not None:
                        action["hue"] = request.hue
                        action["sat"] = request.saturation
                    elif request.color_temp is not None:
                        action["ct"] = request.color_temp
                elif request.action == "off":
                    action["on"] = False
                elif request.action == "toggle":
                    # For toggle, we'll turn off all lights for simplicity
                    # In a more advanced implementation, we could check each light's state
                    action["on"] = False

                result = await client.control_group(0, action)

                logger.info(f"Successfully controlled all lights: {request.action}")

                return HueResponse(
                    success=True,
                    message=f"All lights {request.action} successfully",
                    data=result,
                    lights_affected=list(range(1, 18)),  # All possible light IDs
                )

        except Exception as e:
            logger.error(f"Failed to control all lights: {e}")
            return HueResponse(
                success=False, message=str(e), data={"error_type": type(e).__name__}
            )

    async def get_light_status(self, light_id: int) -> HueResponse:
        """Get status of a specific light."""
        try:
            self._validate_light_id(light_id)

            async with AsyncHueClient() as client:
                state = await client.get_light_state(light_id)

                return HueResponse(
                    success=True,
                    message=f"Retrieved status for light {light_id}",
                    data=state,
                )

        except Exception as e:
            logger.error(f"Failed to get light {light_id} status: {e}")
            return HueResponse(
                success=False, message=str(e), data={"error_type": type(e).__name__}
            )

    async def list_all_lights(self) -> HueResponse:
        """List all lights and their states."""
        try:
            async with AsyncHueClient() as client:
                lights = await client.get_lights()

                return HueResponse(
                    success=True, message=f"Retrieved {len(lights)} lights", data=lights
                )

        except Exception as e:
            logger.error(f"Failed to list lights: {e}")
            return HueResponse(
                success=False, message=str(e), data={"error_type": type(e).__name__}
            )

    async def discover_bridge(self) -> HueResponse:
        """Test bridge connectivity and get bridge info."""
        try:
            async with AsyncHueClient() as client:
                config_data = await client.get_config()

                bridge_info = {
                    "name": config_data.get("name", "Unknown"),
                    "swversion": config_data.get("swversion", "Unknown"),
                    "apiversion": config_data.get("apiversion", "Unknown"),
                    "mac": config_data.get("mac", "Unknown"),
                    "bridge_id": config_data.get("bridgeid", "Unknown"),
                    "model_id": config_data.get("modelid", "Unknown"),
                }

                return HueResponse(
                    success=True,
                    message="Bridge connection successful",
                    data=bridge_info,
                )

        except Exception as e:
            logger.error(f"Failed to discover bridge: {e}")
            return HueResponse(
                success=False, message=str(e), data={"error_type": type(e).__name__}
            )
