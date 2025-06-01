# start_server.py - Simple script to start the OCPP server

import asyncio
import logging
import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def main():
    """Start the OCPP server"""
    try:
        # Debug: Print current working directory and Python path
        logger.info(f"Current working directory: {os.getcwd()}")
        logger.info(f"Project root: {project_root}")
        logger.info(f"Python path includes: {sys.path[:3]}...")

        # Try to list the contents of the project root
        if project_root.exists():
            contents = list(project_root.iterdir())
            logger.info(f"Project root contents: {[p.name for p in contents]}")

        # Import your OCPP server
        from ev_charging_system.core.ocpp_server import OCPPServer

        logger.info("✅ Successfully imported OCPP server")
        logger.info("Starting OCPP Server on 0.0.0.0:9000...")

        # Create and start the server
        server = OCPPServer(host="0.0.0.0", port=9000)
        await server.start()

    except ImportError as e:
        logger.error(f"❌ Failed to import OCPP server: {e}")
        logger.error("Directory structure diagnosis:")

        # Show current directory structure
        current_dir = Path.cwd()
        logger.error(f"Current directory: {current_dir}")

        # Look for ev_charging_system module
        possible_paths = [
            current_dir / "ev_charging_system",
            current_dir.parent / "ev_charging_system",
            project_root / "ev_charging_system"
        ]

        for path in possible_paths:
            if path.exists():
                logger.error(f"Found ev_charging_system at: {path}")
                # Check if it has the expected structure
                core_path = path / "core"
                server_path = core_path / "ocpp_server.py"
                logger.error(f"  - core directory exists: {core_path.exists()}")
                logger.error(f"  - ocpp_server.py exists: {server_path.exists()}")
            else:
                logger.error(f"Not found at: {path}")

        # Suggest solutions
        logger.error("\n💡 Possible solutions:")
        logger.error("1. Run from the project root directory (where ev_charging_system folder is)")
        logger.error("2. Create the missing ev_charging_system/core/ocpp_server.py file")
        logger.error("3. Check if your project structure matches the expected layout")

    except Exception as e:
        logger.error(f"❌ Error starting OCPP server: {e}", exc_info=True)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Server stopped by user")
    except Exception as e:
        logger.error(f"💥 Server failed: {e}", exc_info=True)