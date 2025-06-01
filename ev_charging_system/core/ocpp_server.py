# ev_charging_system/core/ocpp_server.py

import asyncio
import logging
import websockets
from typing import Dict, Optional, Callable
from datetime import datetime
from ocpp.routing import on

# OCPP 2.0.1 imports
from ocpp.v201 import ChargePoint as OCPPCp
from ocpp.v201 import call as ocpp_call_v201
from ocpp.v201 import call_result as ocpp_call_result_v201
from ocpp.v201 import enums as ocpp_enums_v201
from ocpp.v201 import datatypes as ocpp_datatypes_v201
from ocpp.exceptions import NotSupportedError, ProtocolError

import json

logger = logging.getLogger(__name__)

# Global dictionary to maintain all connected Charge Points
connected_charge_points: Dict[str, OCPPCp] = {}


# --- Nova classe CustomChargePoint com handlers integrados ---
class CustomChargePoint(OCPPCp):
    """
    Custom Charge Point class with integrated OCPP 2.0.1 message handlers.
    """
    def __init__(self, charge_point_id: str, connection: websockets.WebSocketServerProtocol):
        # Call parent constructor with only the required arguments
        super().__init__(charge_point_id, connection)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.logger.info(f"CustomChargePoint {self.id} initialized. Route map: {list(self.route_map.keys())}")

    @on('BootNotification')
    async def on_boot_notification(self, **kwargs):
        """Handle BootNotification from charge point"""
        self.logger.info(f"📡 BootNotification received from {self.id}")
        self.logger.info(f"Boot data: {kwargs}")

        # Extract boot notification data
        charging_station = kwargs.get('charging_station', {})
        reason = kwargs.get('reason', 'Unknown')

        self.logger.info(f"Charging Station Info: {charging_station}")
        self.logger.info(f"Boot Reason: {reason}")

        # Return BootNotificationResponse
        self.logger.info(f"BootNotification handler for {self.id} is preparing response.")
        payload = ocpp_call_result_v201.BootNotificationPayload(
            current_time=datetime.utcnow().isoformat(),
            interval=300,  # Heartbeat interval in seconds
            status=ocpp_enums_v201.RegistrationStatusType.accepted
        )

        # Fix: Use vars() or __dict__ instead of to_json()
        try:
            payload_dict = vars(payload)  # or payload.__dict__
            self.logger.info(f"BootNotification handler for {self.id} returning payload: {payload_dict}")
        except Exception as e:
            self.logger.info(
                f"BootNotification handler for {self.id} returning payload (dict conversion failed): {payload}")

        return payload

    @on('Heartbeat')
    async def on_heartbeat(self, **kwargs):
        """Handle Heartbeat from charge point"""
        self.logger.debug(f"💓 Heartbeat received from {self.id}")

        return ocpp_call_result_v201.HeartbeatPayload(
            current_time=datetime.utcnow().isoformat()
        )

    @on('StatusNotification')
    async def on_status_notification(self, **kwargs):
        """Handle StatusNotification from charge point"""
        timestamp = kwargs.get('timestamp')
        connector_status = kwargs.get('connector_status')
        evse_id = kwargs.get('evse_id')
        connector_id = kwargs.get('connector_id')

        self.logger.info(f"🔌 Status update from {self.id}")
        self.logger.info(f"EVSE {evse_id}, Connector {connector_id}: {connector_status} at {timestamp}")

        # Update database with status
        await self._update_connector_status(self.id, evse_id, connector_id, connector_status)

        return ocpp_call_result_v201.StatusNotificationPayload()

    @on('TransactionEvent')
    async def on_transaction_event(self, **kwargs):
        """Handle TransactionEvent from charge point"""
        event_type = kwargs.get('event_type')
        timestamp = kwargs.get('timestamp')
        transaction_info = kwargs.get('transaction_info', {})
        trigger_reason = kwargs.get('trigger_reason')

        transaction_id = transaction_info.get('transaction_id')

        self.logger.info(f"🔄 Transaction event from {self.id}")
        self.logger.info(f"Event: {event_type}, Transaction: {transaction_id}")
        self.logger.info(f"Trigger: {trigger_reason}, Time: {timestamp}")

        # Process transaction event
        await self._process_transaction_event(
            self.id, event_type, transaction_info, trigger_reason, timestamp
        )

        return ocpp_call_result_v201.TransactionEventPayload()

    @on('Authorize')
    async def on_authorize(self, **kwargs):
        """Handle Authorize request from charge point"""
        id_token = kwargs.get('id_token', {})
        token_value = id_token.get('id_token', 'Unknown')
        token_type = id_token.get('type', 'Unknown')

        self.logger.info(f"🔐 Authorization request from {self.id}")
        self.logger.info(f"Token: {token_value} (Type: {token_type})")

        # Verify token authorization
        is_authorized = await self._verify_token_authorization(token_value)

        id_token_info = ocpp_datatypes_v201.IdTokenInfoType(
            status=ocpp_enums_v201.AuthorizationStatusType.accepted if is_authorized  # Fixed: AuthorizationStatusType
            else ocpp_enums_v201.AuthorizationStatusType.invalid
        )

        return ocpp_call_result_v201.AuthorizePayload(
            id_token_info=id_token_info
        )

    @on('MeterValues')
    async def on_meter_values(self, **kwargs):
        """Handle MeterValues from charge point"""
        evse_id = kwargs.get('evse_id')
        meter_value = kwargs.get('meter_value', [])

        self.logger.info(f"⚡ Meter values from {self.id}, EVSE {evse_id}")

        for mv in meter_value:
            timestamp = mv.get('timestamp')
            sampled_value = mv.get('sampled_value', [])

            for sv in sampled_value:
                value = sv.get('value')
                measurand = sv.get('measurand', 'Unknown')
                unit = sv.get('unit', 'Unknown')

                self.logger.debug(f"📊 {measurand}: {value} {unit} at {timestamp}")

        # Store meter values
        await self._store_meter_values(self.id, evse_id, meter_value)

        return ocpp_call_result_v201.MeterValuesPayload()

    @on('DataTransfer')
    async def on_data_transfer(self, **kwargs):
        """Handle DataTransfer from charge point"""
        vendor_id = kwargs.get('vendor_id')
        message_id = kwargs.get('message_id')
        data = kwargs.get('data')

        self.logger.info(f"📡 Data transfer from {self.id}")
        self.logger.info(f"Vendor: {vendor_id}, Message: {message_id}")
        self.logger.info(f"Data: {data}")

        return ocpp_call_result_v201.DataTransferPayload(
            status=ocpp_enums_v201.DataTransferStatusType.accepted  # Fixed: DataTransferStatusType
        )

    @on('FirmwareStatusNotification')
    async def on_firmware_status_notification(self, **kwargs):
        """Handle FirmwareStatusNotification from charge point"""
        status = kwargs.get('status')
        request_id = kwargs.get('request_id')

        self.logger.info(f"🔧 Firmware status from {self.id}: {status}")
        if request_id:
            self.logger.info(f"Request ID: {request_id}")

        return ocpp_call_result_v201.FirmwareStatusNotificationPayload()

    @on('LogStatusNotification')
    async def on_log_status_notification(self, **kwargs):
        """Handle LogStatusNotification from charge point"""
        status = kwargs.get('status')
        request_id = kwargs.get('request_id')

        self.logger.info(f"📝 Log status from {self.id}: {status}")
        if request_id:
            self.logger.info(f"Request ID: {request_id}")

        return ocpp_call_result_v201.LogStatusNotificationPayload()

    # Helper methods (moved from ocpp_handlers.py)
    async def _update_connector_status(self, charge_point_id: str, evse_id: int,
                                       connector_id: int, status: str):
        """Update connector status in database"""
        try:
            # Import here to avoid circular imports
            from ev_charging_system.data.database import get_db
            from ev_charging_system.data.repositories import ChargePointRepository

            db_session = next(get_db())
            try:
                cp_repo = ChargePointRepository(db_session)
                # Update connector status logic here
                self.logger.debug(f"Updated connector status for {charge_point_id}")
            finally:
                db_session.close()
        except Exception as e:
            self.logger.error(f"Error updating connector status: {e}")

    async def _process_transaction_event(self, charge_point_id: str, event_type: str,
                                         transaction_info: Dict, trigger_reason: str,
                                         timestamp: str):
        """Process transaction event"""
        try:
            transaction_id = transaction_info.get('transaction_id')

            if event_type == 'Started':
                self.logger.info(f"Transaction {transaction_id} started on {charge_point_id}")
            elif event_type == 'Updated':
                self.logger.info(f"Transaction {transaction_id} updated on {charge_point_id}")
            elif event_type == 'Ended':
                self.logger.info(f"Transaction {transaction_id} ended on {charge_point_id}")

            # Store transaction data in database
            from ev_charging_system.data.database import get_db
            from ev_charging_system.data.repositories import TransactionRepository

            db_session = next(get_db())
            try:
                tx_repo = TransactionRepository(db_session)
                # Transaction processing logic here
                self.logger.debug(f"Processed transaction event for {charge_point_id}")
            finally:
                db_session.close()

        except Exception as e:
            self.logger.error(f"Error processing transaction event: {e}")

    async def _verify_token_authorization(self, token_value: str) -> bool:
        """Verify if token is authorized"""
        try:
            # Import here to avoid circular imports
            from ev_charging_system.data.database import get_db
            from ev_charging_system.data.repositories import UserRepository

            db_session = next(get_db())
            try:
                user_repo = UserRepository(db_session)
                # Token verification logic here
                # For now, return True for testing
                return True
            finally:
                db_session.close()
        except Exception as e:
            self.logger.error(f"Error verifying token: {e}")
            return False

    async def _store_meter_values(self, charge_point_id: str, evse_id: int,
                                  meter_values: list):
        """Store meter values in database"""
        try:
            # Store meter values logic here
            self.logger.debug(f"Stored meter values for {charge_point_id}")
        except Exception as e:
            self.logger.error(f"Error storing meter values: {e}")


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
            # --- Instanciar CustomChargePoint com argumentos corretos ---
            charge_point = CustomChargePoint(
                charge_point_id,
                websocket
            )
            logger.info(f"OCPP server: CustomChargePoint instance created for {charge_point_id}.")

            # Register the charge point
            connected_charge_points[charge_point_id] = charge_point
            logger.info(f"✅ Registered Charge Point: {charge_point_id}")

            # Update database status to online
            await self._update_cp_status_in_db(charge_point_id, "Online")

            # Start the charge point message processing loop
            logger.info(f"🚀 Starting message processing for {charge_point_id}")
            await charge_point.start() # This call blocks until the connection is closed

        except websockets.exceptions.ConnectionClosedOK:
            logger.info(f"Charge Point {charge_point_id} disconnected normally (ConnectionClosedOK).")

        except websockets.exceptions.ConnectionClosed as e:
            logger.warning(f"Charge Point {charge_point_id} connection closed: {e}")

        except Exception as e:
            logger.error(f"Error with Charge Point {charge_point_id}: {e}", exc_info=True)

        finally:
            # Clean up when connection is lost
            logger.info(f"OCPP server: Entering finally block for {charge_point_id}. Disconnecting charge point.")
            await self._disconnect_charge_point(charge_point_id)

    async def _disconnect_charge_point(self, charge_point_id: str):
        """Disconnect a charge point and clean up resources."""
        if charge_point_id not in connected_charge_points:
            logger.debug(f"OCPP server: Attempted to disconnect {charge_point_id} but not in connected list.")
            return

        logger.info(f"🔌 Disconnecting Charge Point {charge_point_id}")

        # Remove from connected list
        cp_instance = connected_charge_points.pop(charge_point_id, None)

        # Update database status to offline
        await self._update_cp_status_in_db(charge_point_id, "Offline")

        # Close the connection if it's still open
        if cp_instance and hasattr(cp_instance, '_connection'):
            try:
                logger.info(f"OCPP server: Attempting to close websocket for {charge_point_id}.")
                await cp_instance._connection.close()
                logger.info(f"OCPP server: Websocket for {charge_point_id} closed.")
            except Exception as e:
                logger.error(f"Error closing connection for {charge_point_id}: {e}", exc_info=True)
        else:
            logger.warning(f"OCPP server: ChargePoint {charge_point_id} has no '_connection' attribute or instance is None.")


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
                type=ocpp_enums_v201.IdTokenType.iso14443  # Fixed: IdTokenType instead of IdTokenEnumType
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
                reset_type_enum = ocpp_enums_v201.ResetType(type_str.lower())  # Fixed: ResetType instead of ResetEnumType
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
                requested_message_enum = ocpp_enums_v201.MessageTriggerType(requested_message_str)  # Fixed: MessageTriggerType
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