"""Configuration management for Hue MCP server."""

import ipaddress
import os

from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator

load_dotenv()


class HueConfig(BaseModel):
    """Configuration for Hue bridge connection."""

    bridge_ip: str = Field(
        default="192.168.1.64", description="IP address of the Hue bridge"
    )
    username: str = Field(
        default="cJdzxhKlxr2h92jwDkTv-DvpOxglPxn147UEg1Gp",
        description="Hue bridge username",
    )
    log_level: str = Field(default="INFO", description="Logging level")
    timeout_connect: float = Field(
        default=5.0, ge=1.0, le=30.0, description="Connection timeout in seconds"
    )
    timeout_read: float = Field(
        default=10.0, ge=1.0, le=60.0, description="Read timeout in seconds"
    )
    max_connections: int = Field(
        default=10, ge=1, le=50, description="Maximum HTTP connections"
    )
    max_keepalive_connections: int = Field(
        default=5, ge=1, le=20, description="Maximum keepalive connections"
    )
    light_rate_limit: int = Field(
        default=10, ge=1, le=100, description="Light operations per second"
    )
    group_rate_limit: float = Field(
        default=1.0, ge=0.1, le=10.0, description="Group operations per second"
    )

    @field_validator("bridge_ip")
    @classmethod
    def validate_ip(cls, v):
        """Validate IP address format."""
        try:
            ipaddress.ip_address(v)
            return v
        except ValueError as e:
            raise ValueError(f"Invalid IP address: {v}") from e

    @field_validator("username")
    @classmethod
    def validate_username(cls, v):
        """Validate username format."""
        if not v or len(v) < 10:
            raise ValueError("Username must be at least 10 characters long")
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()

    @classmethod
    def from_env(cls) -> "HueConfig":
        """Create configuration from environment variables."""
        return cls(
            bridge_ip=os.getenv("HUE_BRIDGE_IP", "192.168.1.64"),
            username=os.getenv(
                "HUE_USERNAME", "cJdzxhKlxr2h92jwDkTv-DvpOxglPxn147UEg1Gp"
            ),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            timeout_connect=float(os.getenv("HUE_TIMEOUT_CONNECT", "5.0")),
            timeout_read=float(os.getenv("HUE_TIMEOUT_READ", "10.0")),
            max_connections=int(os.getenv("HUE_MAX_CONNECTIONS", "10")),
            max_keepalive_connections=int(os.getenv("HUE_MAX_KEEPALIVE", "5")),
            light_rate_limit=int(os.getenv("HUE_LIGHT_RATE_LIMIT", "10")),
            group_rate_limit=float(os.getenv("HUE_GROUP_RATE_LIMIT", "1.0")),
        )

    @property
    def base_url(self) -> str:
        """Get the base URL for Hue API."""
        return f"http://{self.bridge_ip}/api/{self.username}"


# Global configuration instance
config = HueConfig.from_env()


# Constants from PRD
HUE_BRIDGE_IP = config.bridge_ip
HUE_USERNAME = config.username
HUE_BASE_URL = config.base_url

# Room mappings from PRD specification
ROOM_MAPPINGS = {
    "kitchen": [10, 12, 13, 17],  # stove_1, toaster_1, toaster_2, stove_2
    "bedroom": [1, 4],  # neals_lamp, bonnies_lamp
    "office": [7],  # office
    "basement": [
        5,
        6,
        14,
        15,
        16,
    ],  # basement_e, basement_w, stairway, batcave_color_1, batcave_color_2
    "living_room": [3],  # small_reading_lamp
    "all": 0,  # Special group ID for all lights
}

# Light name mappings
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
    "stove_2": 17,
}
