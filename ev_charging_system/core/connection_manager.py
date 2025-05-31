# ev_charging_system/core/connection_manager.py

import asyncio
import logging
from typing import Dict, Optional, Callable, Any
from threading import Lock
from datetime import datetime
from ocpp.v16 import ChargePoint as OCPPChargePoint
from ocpp.exceptions import NotSupportedError, ProtocolError

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Centralized connection manager for all OCPP Charge Points.
    Handles connection lifecycle, command sending, and state management.
    """

    def __init__(self):
        self._connected_charge_points: Dict[str, OCPPChargePoint] = {}
        self._connection_lock = Lock()
        self._connection_callbacks: Dict[str, Callable] = {}

    def register_connection_callback(self, event: str, callback: Callable):
        """Register callbacks for connection events (connect, disconnect)."""
        self._connection_callbacks[event] = callback

    async def register_charge_point(self, charge_point_id: str, cp_instance: OCPPChargePoint) -> bool:
        """
        Register a new charge point connection.

        Args:
            charge_point_id: Unique identifier for the charge point
            cp_instance: OCPP ChargePoint instance

        Returns:
            bool: True if registration successful, False if already exists
        """
        with self._connection_lock:
            if charge_point_id in self._connected_charge_points:
                logger.warning(f"Charge Point {charge_point_id} already registered. Replacing existing connection.")
                # Close existing connection gracefully
                await self._disconnect_charge_point(charge_point_id)

            self._connected_charge_points[charge_point_id] = cp_instance
            logger.info(f"Charge Point {charge_point_id} registered successfully")

            # Trigger connection callback if registered
            if 'connect' in self._connection_callbacks:
                try:
                    await self._connection_callbacks['connect'](charge_point_id, cp_instance)
                except Exception as e:
                    logger.error(f"Error in connection callback for {charge_point_id}: {e}")

            return True

    async def unregister_charge_point(self, charge_point_id: str) -> bool:
        """
        Unregister a charge point connection.

        Args:
            charge_point_id: Unique identifier for the charge point

        Returns:
            bool: True if unregistration successful, False if not found
        """
        with self._connection_lock:
            if charge_point_id not in self._connected_charge_points:
                logger.warning(f"Attempted to unregister unknown Charge Point: {charge_point_id}")
                return False

            cp_instance = self._connected_charge_points.pop(charge_point_id)
            logger.info(f"Charge Point {charge_point_id} unregistered")

            # Trigger disconnection callback if registered
            if 'disconnect' in self._connection_callbacks:
                try:
                    await self._connection_callbacks['disconnect'](charge_point_id, cp_instance)
                except Exception as e:
                    logger.error(f"Error in disconnection callback for {charge_point_id}: {e}")

            return True

    def get_charge_point(self, charge_point_id: str) -> Optional[OCPPChargePoint]:
        """Get a charge point instance by ID."""
        return self._connected_charge_points.get(charge_point_id)

    def is_connected(self, charge_point_id: str) -> bool:
        """Check if a charge point is currently connected."""
        return charge_point_id in self._connected_charge_points

    def get_connected_charge_points(self) -> Dict[str, OCPPChargePoint]:
        """Get all connected charge points."""
        return self._connected_charge_points.copy()

    def get_connection_count(self) -> int:
        """Get the total number of connected charge points."""
        return len(self._connected_charge_points)

    async def send_command_to_cp(self, charge_point_id: str, command_name: str, **kwargs) -> Dict[str, Any]:
        """
        Send an OCPP command to a specific charge point.

        Args:
            charge_point_id: Target charge point ID
            command_name: OCPP command name (e.g., 'remote_start_transaction')
            **kwargs: Command parameters

        Returns:
            Dict containing response status and data
        """
        if not self.is_connected(charge_point_id):
            logger.warning(f"Charge Point {charge_point_id} not connected. Cannot send command {command_name}")
            return {"status": "failed", "reason": "Charge Point not connected"}

        cp_instance = self.get_charge_point(charge_point_id)

        try:
            # Get the command method from the charge point instance
            if not hasattr(cp_instance, command_name):
                logger.error(f"Command '{command_name}' not supported by charge point {charge_point_id}")
                return {"status": "failed", "reason": f"Command '{command_name}' not supported"}

            command_method = getattr(cp_instance, command_name)
            logger.info(f"Sending {command_name} to {charge_point_id} with params: {kwargs}")

            # Execute the command
            response = await command_method(**kwargs)

            logger.info(f"Response from {charge_point_id} for {command_name}: {response}")
            return {
                "status": "success",
                "response": response,
                "timestamp": datetime.utcnow().isoformat()
            }

        except NotSupportedError as e:
            logger.warning(f"Command {command_name} not supported by {charge_point_id}: {e}")
            return {"status": "failed", "reason": f"Command not supported: {e}"}

        except ProtocolError as e:
            logger.error(f"Protocol error sending {command_name} to {charge_point_id}: {e}")
            return {"status": "failed", "reason": f"Protocol error: {e}"}

        except Exception as e:
            logger.error(f"Unexpected error sending {command_name} to {charge_point_id}: {e}", exc_info=True)
            return {"status": "failed", "reason": f"Internal error: {e}"}

    async def _disconnect_charge_point(self, charge_point_id: str):
        """Internal method to gracefully disconnect a charge point."""
        try:
            cp_instance = self._connected_charge_points.get(charge_point_id)
            if cp_instance and hasattr(cp_instance, 'close'):
                await cp_instance.close()
        except Exception as e:
            logger.error(f"Error closing connection for {charge_point_id}: {e}")

    async def broadcast_command(self, command_name: str, **kwargs) -> Dict[str, Dict[str, Any]]:
        """
        Broadcast a command to all connected charge points.

        Args:
            command_name: OCPP command name
            **kwargs: Command parameters

        Returns:
            Dict mapping charge_point_id to response
        """
        results = {}
        connected_cps = list(self._connected_charge_points.keys())

        logger.info(f"Broadcasting {command_name} to {len(connected_cps)} charge points")

        # Send commands concurrently to all connected charge points
        tasks = []
        for cp_id in connected_cps:
            task = self.send_command_to_cp(cp_id, command_name, **kwargs)
            tasks.append((cp_id, task))

        # Wait for all commands to complete
        for cp_id, task in tasks:
            try:
                result = await task
                results[cp_id] = result
            except Exception as e:
                logger.error(f"Error broadcasting to {cp_id}: {e}")
                results[cp_id] = {"status": "failed", "reason": str(e)}

        return results

    async def shutdown(self):
        """Gracefully shutdown all connections."""
        logger.info("Shutting down connection manager...")

        connected_cps = list(self._connected_charge_points.keys())

        # Disconnect all charge points
        for cp_id in connected_cps:
            try:
                await self.unregister_charge_point(cp_id)
            except Exception as e:
                logger.error(f"Error disconnecting {cp_id} during shutdown: {e}")

        logger.info("Connection manager shutdown complete")


# Global connection manager instance
connection_manager = ConnectionManager()