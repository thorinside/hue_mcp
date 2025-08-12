"""Main MCP server for Philips Hue control."""

import logging
import signal
import sys

from .config import config
from .hue_client import AsyncHueClient

# Import the shared MCP instance
from .mcp_instance import mcp

# Import tool modules to register them with FastMCP
from .tools import discovery, light_control, room_control

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def test_bridge_connection():
    """Test connection to Hue bridge during startup."""
    try:
        async with AsyncHueClient() as client:
            success = await client.test_connection()
            if success:
                logger.info(
                    f"Successfully connected to Hue bridge at {config.bridge_ip}"
                )
            else:
                logger.warning(f"Failed to connect to Hue bridge at {config.bridge_ip}")
                logger.warning("Server will start but tools may not work properly")
    except Exception as e:
        logger.error(f"Error testing bridge connection: {e}")
        logger.warning("Server will start but tools may not work properly")


def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown."""

    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def main():
    """Main entry point for MCP server."""
    setup_signal_handlers()

    try:
        logger.info("Starting Hue MCP server...")
        logger.info(f"Bridge IP: {config.bridge_ip}")
        logger.info(f"Log level: {config.log_level}")

        # Test bridge connection before starting server
        import asyncio

        asyncio.run(test_bridge_connection())

        # Run the server with streamable-http transport
        mcp.run(transport="streamable-http", host="0.0.0.0")

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)
    finally:
        logger.info("Hue MCP server shutdown complete")


if __name__ == "__main__":
    main()
