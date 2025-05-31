# ev_charging_system/core/ocpp_server.py

import asyncio
import logging
import websockets
from typing import Dict, Optional, Callable
from datetime import datetime
from ocpp.routing import create_route_map
from ocpp.v16 import ChargePoint as OCPPCp
from ocpp.exceptions import NotSupportedError, ProtocolError
import json

logger = logging.getLogger(__name__)

# Global dictionary to maintain all connected Charge Points
connected_charge_points: Dict[str, OCPPCp] = {}


class OCPPServer:
    """
    Main OCPP WebSocket Server class that handles all OCPP connections and message routing.
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 9000):
        self.host = host
        self.port = port
        self.server = None
        self._running = False

    async def start(self):
        """Start the OCPP WebSocket server."""
        if self._running:
            logger.warning("OCPP Server is already running")
            return

        logger.info(f"Starting OCPP server on ws://{self.host}:{self.port}")

        self.server = await websockets.serve(
            self._handle_connection,
            self.host,
            self.port,
            subprotocols=['ocpp1.6']
        )

        self._running = True
        logger.info(f"OCPP WebSocket Server started successfully on ws://{self.host}:{self.port}")

        # Keep the server running
        await self.server.wait_closed()

    async def stop(self):
        """Stop the OCPP WebSocket server."""
        if not self._running:
            return

        logger.info("Stopping OCPP WebSocket Server...")

        # Disconnect all charge points gracefully
        for cp_id in list(connected_charge_points.keys()):
            await self._disconnect_charge_point(cp_id)

        if self.server:
            self.server.close()
            await self.server.wait_closed()

        self._running = False
        logger.info("OCPP WebSocket Server stopped")

    async def _handle_connection(self, websocket, path):
        """
        Handle new WebSocket connections from Charge Points.

        Args:
            websocket: The WebSocket connection
            path: URL path containing the Charge Point ID (e.g., '/CP001')
        """
        # Extract Charge Point ID from path
        charge_point_id = path.strip('/')
        if not charge_point_id:
            logger.warning("Connection attempt with empty charge point ID. Closing connection.")
            await websocket.close()
            return

        logger.info(f"New connection from Charge Point: {charge_point_id}")

        # Check if already connected
        if charge_point_id in connected_charge_points:
            logger.warning(f"Charge Point {charge_point_id} already connected. Replacing connection.")
            await self._disconnect_charge_point(charge_point_id)

        # Import handlers here to avoid circular imports
        from ev_charging_system.core import ocpp_handlers

        # Create OCPP ChargePoint instance with message handlers
        charge_point = OCPPCp(
            charge_point_id,
            websocket,
            create_route_map(ocpp_handlers)
        )

        # Register the charge point
        connected_charge_points[charge_point_id] = charge_point

        # Update database status to online
        await self._update_cp_status_in_db(charge_point_id, "Online")

        try:
            # Start the charge point message processing loop
            await charge_point.start()

        except websockets.exceptions.ConnectionClosedOK:
            logger.info(f"Charge Point {charge_point_id} disconnected normally")

        except websockets.exceptions.ConnectionClosed as e:
            logger.warning(f"Charge Point {charge_point_id} connection closed: {e}")

        except Exception as e:
            logger.error(f"Error with Charge Point {charge_point_id}: {e}", exc_info=True)

        finally:
            # Clean up when connection is lost
            await self._disconnect_charge_point(charge_point_id)

    async def _disconnect_charge_point(self, charge_point_id: str):
        """Disconnect a charge point and clean up resources."""
        if charge_point_id not in connected_charge_points:
            return

        logger.info(f"Disconnecting Charge Point {charge_point_id}")

        # Remove from connected list
        cp_instance = connected_charge_points.pop(charge_point_id, None)

        # Update database status to offline
        await self._update_cp_status_in_db(charge_point_id, "Offline")

        # Close the connection if it's still open
        if cp_instance and hasattr(cp_instance, '_connection'):
            try:
                await cp_instance._connection.close()
            except Exception as e:
                logger.error(f"Error closing connection for {charge_point_id}: {e}")

    async def _update_cp_status_in_db(self, charge_point_id: str, status: str):
        """Update charge point status in database."""
        try:
            from ev_charging_system.data.database import get_db
            from ev_charging_system.data.repositories import ChargePointRepository, TransactionRepository, \
                UserRepository
            from ev_charging_system.business_logic.device_management_service import DeviceManagementService

            db_session = next(get_db())
            try:
                cp_repo = ChargePointRepository(db_session)
                tx_repo = TransactionRepository(db_session)
                user_repo = UserRepository(db_session)

                device_service = DeviceManagementService(cp_repo, tx_repo, user_repo)
                device_service.update_charge_point_status(charge_point_id, status)

                logger.debug(f"Updated Charge Point {charge_point_id} status to {status} in database")

            finally:
                db_session.close()

        except Exception as e:
            logger.error(f"Error updating CP {charge_point_id} status in DB: {e}")

    def get_connected_charge_points(self) -> Dict[str, OCPPCp]:
        """Get all currently connected charge points."""
        return connected_charge_points.copy()

    def is_connected(self, charge_point_id: str) -> bool:
        """Check if a charge point is currently connected."""
        return charge_point_id in connected_charge_points

    def get_charge_point(self, charge_point_id: str) -> Optional[OCPPCp]:
        """Get a specific charge point instance."""
        return connected_charge_points.get(charge_point_id)


# OCPP Command Sending Functions
async def send_ocpp_command(charge_point_id: str, command_name: str, **kwargs) -> dict:
    """
    Send an OCPP command to a specific charge point.

    Args:
        charge_point_id: Target charge point ID
        command_name: OCPP command name
        **kwargs: Command parameters

    Returns:
        Dict with command result
    """
    if charge_point_id not in connected_charge_points:
        logger.warning(f"Charge Point {charge_point_id} not connected. Cannot send {command_name}")
        return {
            "status": "failed",
            "reason": "Charge Point not connected",
            "timestamp": datetime.utcnow().isoformat()
        }

    cp = connected_charge_points[charge_point_id]

    try:
        logger.info(f"Sending {command_name} to {charge_point_id} with params: {kwargs}")

        # Map command names to charge point methods
        command_methods = {
            "RemoteStartTransaction": cp.remote_start_transaction,
            "RemoteStopTransaction": cp.remote_stop_transaction,
            "UnlockConnector": cp.unlock_connector,
            "Reset": cp.reset,
            "GetConfiguration": cp.get_configuration,
            "ChangeConfiguration": cp.change_configuration,
            "TriggerMessage": cp.trigger_message,
        }

        if command_name not in command_methods:
            logger.error(f"Unsupported command: {command_name}")
            return {
                "status": "failed",
                "reason": f"Unsupported command: {command_name}",
                "timestamp": datetime.utcnow().isoformat()
            }

        # Execute the command
        response = await command_methods[command_name](**kwargs)

        logger.info(f"Response from {charge_point_id} for {command_name}: {response}")

        return {
            "status": "success",
            "response": response,
            "timestamp": datetime.utcnow().isoformat()
        }

    except NotSupportedError as e:
        logger.warning(f"Command {command_name} not supported by {charge_point_id}: {e}")
        return {
            "status": "failed",
            "reason": f"Command not supported: {e}",
            "timestamp": datetime.utcnow().isoformat()
        }

    except ProtocolError as e:
        logger.error(f"Protocol error sending {command_name} to {charge_point_id}: {e}")
        return {
            "status": "failed",
            "reason": f"Protocol error: {e}",
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error sending {command_name} to {charge_point_id}: {e}", exc_info=True)
        return {
            "status": "failed",
            "reason": f"Internal error: {e}",
            "timestamp": datetime.utcnow().isoformat()
        }


async def broadcast_command(command_name: str, **kwargs) -> Dict[str, dict]:
    """
    Broadcast a command to all connected charge points.

    Args:
        command_name: OCPP command name
        **kwargs: Command parameters

    Returns:
        Dict mapping charge_point_id to response
    """
    if not connected_charge_points:
        logger.warning("No charge points connected for broadcast")
        return {}

    logger.info(f"Broadcasting {command_name} to {len(connected_charge_points)} charge points")

    results = {}
    tasks = []

    # Create tasks for all connected charge points
    for cp_id in connected_charge_points.keys():
        task = send_ocpp_command(cp_id, command_name, **kwargs)
        tasks.append((cp_id, task))

    # Execute all tasks concurrently
    for cp_id, task in tasks:
        try:
            result = await task
            results[cp_id] = result
        except Exception as e:
            logger.error(f"Error broadcasting to {cp_id}: {e}")
            results[cp_id] = {
                "status": "failed",
                "reason": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    return results


# Global server instance
ocpp_server = OCPPServer()


# Compatibility functions for existing code
async def start_ocpp_server(host: str = "0.0.0.0", port: int = 9000):
    """Start the OCPP server (compatibility function)."""
    global ocpp_server
    ocpp_server = OCPPServer(host, port)
    await ocpp_server.start()


def get_connected_charge_points() -> Dict[str, OCPPCp]:
    """Get all connected charge points (compatibility function)."""
    return connected_charge_points.copy()


def is_charge_point_connected(charge_point_id: str) -> bool:
    """Check if a charge point is connected (compatibility function)."""
    return charge_point_id in connected_charge_points