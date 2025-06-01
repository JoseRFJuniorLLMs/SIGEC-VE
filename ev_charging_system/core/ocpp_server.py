# ev_charging_system/core/ocpp_server.py

import asyncio
import logging
import websockets
from typing import Dict, Optional, Callable
from datetime import datetime
from ocpp.routing import create_route_map

# OCPP 2.0.1 imports
from ocpp.v201 import ChargePoint as OCPPCp
from ocpp.v201 import call as ocpp_call_v201
from ocpp.v201 import enums as ocpp_enums_v201
from ocpp.v201 import datatypes as ocpp_datatypes_v201
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
            subprotocols=['ocpp2.0', 'ocpp2.0.1']
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

        logger.info(f"🔌 New connection from Charge Point: {charge_point_id}")
        logger.info(f"Subprotocol selected: {websocket.subprotocol}")

        # Check if already connected
        if charge_point_id in connected_charge_points:
            logger.warning(f"Charge Point {charge_point_id} already connected. Replacing connection.")
            await self._disconnect_charge_point(charge_point_id)

        try:
            # Import handlers here to avoid circular imports
            # Correctly import the 'handlers' instance from ocpp_handlers.py
            from ev_charging_system.core.ocpp_handlers import handlers as ocpp_message_handlers

            # Create route map from the handlers instance
            route_map = create_route_map(ocpp_message_handlers)
            # This line will now show what handlers were actually registered:
            logger.info(f"📋 Generated Route Map (found {len(route_map)} handlers): {list(route_map.keys())}")

            # Create OCPP ChargePoint instance
            charge_point = OCPPCp(
                charge_point_id,
                websocket,
                route_map
            )

            # Register the charge point
            connected_charge_points[charge_point_id] = charge_point
            logger.info(f"✅ Registered Charge Point: {charge_point_id}")

            # Update database status to online
            await self._update_cp_status_in_db(charge_point_id, "Online")

            # Start the charge point message processing loop
            logger.info(f"🚀 Starting message processing for {charge_point_id}")
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

    async def _update_cp_status_in_db(self, charge_point_id: str, status: str):
        """Update charge point status in database."""
        try:
            # Import database components
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
            logger.error(f"Error updating CP {charge_point_id} status in DB: {e}", exc_info=True)

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
        command_name: OCPP command name (e.g., "RemoteStartTransaction")
        **kwargs: Command parameters specific to the OCPP 2.0.1 payload.

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
        logger.info(f"📤 Sending {command_name} to {charge_point_id} with params: {kwargs}")

        response = None

        # Command mapping for OCPP 2.0.1
        if command_name == "RemoteStartTransaction":
            id_token_value = kwargs.get("id_tag")
            connector_id = kwargs.get("connector_id", 1)
            remote_start_id = kwargs.get("remote_start_id", 1)

            if not id_token_value:
                raise ValueError("id_tag is required for RemoteStartTransaction")

            id_token = ocpp_datatypes_v201.IdTokenType(
                id_token=id_token_value,
                type=ocpp_enums_v201.IdTokenEnumType.iso14443
            )

            payload = ocpp_call_v201.RemoteStartTransactionPayload(
                id_token=id_token,
                remote_start_id=remote_start_id,
                evse_id=connector_id
            )
            response = await cp.remote_start_transaction(payload)

        elif command_name == "RemoteStopTransaction":
            transaction_id = kwargs.get("transaction_id")
            if not transaction_id:
                raise ValueError("transaction_id is required for RemoteStopTransaction")

            payload = ocpp_call_v201.RemoteStopTransactionPayload(
                transaction_id=transaction_id
            )
            response = await cp.remote_stop_transaction(payload)

        elif command_name == "UnlockConnector":
            evse_id = kwargs.get("connector_id", 1)
            connector_id = kwargs.get("connector_id", 1)

            payload = ocpp_call_v201.UnlockConnectorPayload(
                evse_id=evse_id,
                connector_id=connector_id
            )
            response = await cp.unlock_connector(payload)

        elif command_name == "Reset":
            type_str = kwargs.get("type", "Soft")

            try:
                reset_type_enum = ocpp_enums_v201.ResetEnumType(type_str.lower())
            except ValueError:
                raise ValueError(f"Invalid Reset type: {type_str}. Must be 'Hard' or 'Soft'.")

            payload = ocpp_call_v201.ResetPayload(type=reset_type_enum)
            response = await cp.reset(payload)

        elif command_name == "GetVariables":
            variable_names = kwargs.get("variable_names", [])

            get_variable_data = []
            for var_name in variable_names:
                get_variable_data.append(
                    ocpp_datatypes_v201.GetVariableDataType(
                        component=ocpp_datatypes_v201.ComponentType(name=var_name),
                        variable=ocpp_datatypes_v201.VariableType(name="Actual")
                    )
                )

            payload = ocpp_call_v201.GetVariablesPayload(
                get_variable_data=get_variable_data
            )
            response = await cp.get_variables(payload)

        elif command_name == "SetVariables":
            key = kwargs.get("key")
            value = kwargs.get("value")

            if not key or value is None:
                raise ValueError("key and value are required for SetVariables")

            set_variable_data = ocpp_datatypes_v201.SetVariableDataType(
                component=ocpp_datatypes_v201.ComponentType(name=key),
                variable=ocpp_datatypes_v201.VariableType(name="Actual"),
                attribute_value=str(value)
            )

            payload = ocpp_call_v201.SetVariablesPayload(
                set_variable_data=[set_variable_data]
            )
            response = await cp.set_variables(payload)

        elif command_name == "ClearCache":
            payload = ocpp_call_v201.ClearCachePayload()
            response = await cp.clear_cache(payload)

        elif command_name == "DataTransfer":
            vendor_id = kwargs.get("vendor_id")
            message_id = kwargs.get("message_id")
            data = kwargs.get("data")

            if not vendor_id or not message_id:
                raise ValueError("vendor_id and message_id are required for DataTransfer")

            payload = ocpp_call_v201.DataTransferPayload(
                vendor_id=vendor_id,
                message_id=message_id,
                data=data
            )
            response = await cp.data_transfer(payload)

        elif command_name == "TriggerMessage":
            requested_message_str = kwargs.get("requested_message")
            evse_id = kwargs.get("evse_id")

            if not requested_message_str:
                raise ValueError("requested_message is required for TriggerMessage")

            try:
                requested_message_enum = ocpp_enums_v201.MessageTriggerEnumType(requested_message_str)
            except ValueError:
                raise ValueError(f"Invalid requested_message: {requested_message_str}")

            payload = ocpp_call_v201.TriggerMessagePayload(
                requested_message=requested_message_enum,
                evse_id=evse_id
            )
            response = await cp.trigger_message(payload)

        else:
            logger.error(f"Unsupported command: {command_name} for OCPP 2.0.1")
            return {
                "status": "failed",
                "reason": f"Unsupported command: {command_name}",
                "timestamp": datetime.utcnow().isoformat()
            }

        logger.info(f"✅ Response from {charge_point_id} for {command_name}: {response}")

        # Convert response to serializable format
        return {
            "status": "success",
            "response": response.__dict__ if hasattr(response, '__dict__') else str(response),
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
    except ValueError as e:
        logger.error(f"Validation error for command {command_name} to {charge_point_id}: {e}")
        return {
            "status": "failed",
            "reason": f"Invalid command parameters: {e}",
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

    logger.info(f"📡 Broadcasting {command_name} to {len(connected_charge_points)} charge points")

    results = {}
    tasks = []

    # Create tasks for all connected charge points
    for cp_id in list(connected_charge_points.keys()):
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