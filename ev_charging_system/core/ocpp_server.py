# ev_charging_system/core/ocpp_server.py

import asyncio
import logging
import websockets
from typing import Dict, Optional, Callable
from datetime import datetime, timezone
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
        self.logger.info(f"CustomChargePoint {self.id} initialized. Handlers registered.")

    async def _handle_call(self, msg):
        action = msg.action
        unique_id = msg.unique_id
        self.logger.info(f"{self.id}: received message {msg}")

        handler = self._route_map.get(action)
        if handler:
            try:
                response_payload = await handler(self, **msg.payload)
                response = ocpp_call_result_v201.RPCMethod(
                    unique_id=unique_id,
                    action=action,
                    payload=response_payload
                )
                self.logger.info(f"Response for {action}: {response_payload}")
                await self.send_response(response)
            except ProtocolError as e:
                self.logger.error(f"Protocol error handling {action} from {self.id}: {e}")
                error_msg = ocpp_call_v201.RPCError(
                    unique_id=unique_id,
                    error_code=ocpp_enums_v201.ErrorEnumType.protocol_error,
                    error_description=str(e),
                    error_details={}
                )
                await self.send_error(error_msg)
            except NotSupportedError as e:
                self.logger.error(f"Action '{action}' not supported by {self.id}: {e}")
                error_msg = ocpp_call_v201.RPCError(
                    unique_id=unique_id,
                    error_code=ocpp_enums_v201.ErrorEnumType.not_supported,
                    error_description=str(e),
                    error_details={}
                )
                await self.send_error(error_msg)
            except Exception as e:
                self.logger.error(f"Error while handling request '{msg}'")
                self.logger.exception(e)
                error_msg = ocpp_call_v201.RPCError(
                    unique_id=unique_id,
                    error_code=ocpp_enums_v201.ErrorEnumType.internal_error,
                    error_description=f"An unexpected error occurred. {e}",
                    error_details={}
                )
                await self.send_error(error_msg)
        else:
            self.logger.warning(f"No handler registered for action '{action}'. Sending NotSupported error.")
            error_msg = ocpp_call_v201.RPCError(
                unique_id=unique_id,
                error_code=ocpp_enums_v201.ErrorEnumType.not_supported,
                error_description=f"Action '{action}' is not supported.",
                error_details={}
            )
            await self.send_error(error_msg)

    async def send_response(self, call_result):
        """
        Sends a CallResult to the connected charge point.
        """
        response_json = json.dumps([
            3,
            call_result.unique_id,
            call_result.payload
        ])
        self.logger.info(f"{self.id}: send {response_json}")
        await self._connection.send(response_json)

    async def send_error(self, call_error):
        """
        Sends a CallError to the connected charge point.
        """
        error_json = json.dumps([
            4,
            call_error.unique_id,
            call_error.error_code.value,
            call_error.error_description,
            call_error.error_details
        ])
        self.logger.info(f"{self.id}: send {error_json}")
        await self._connection.send(error_json)

    @on('BootNotification')
    async def on_boot_notification(self,
            charging_station: ocpp_datatypes_v201.ChargingStationType,
            reason: ocpp_enums_v201.BootReasonEnumType,
            **kwargs
    ):
        self.logger.info(f"📡 BootNotification received from {self.id}")
        self.logger.info(f"Boot data: {kwargs}")
        self.logger.info(f"Charging Station Info: {charging_station}")
        self.logger.info(f"Boot Reason: {reason}")

        self.logger.info(f"BootNotification handler for {self.id} is preparing response.")
        payload = ocpp_call_result_v201.BootNotification(
            current_time=datetime.utcnow().isoformat(),
            interval=300,
            status=ocpp_enums_v201.RegistrationStatusEnumType.accepted
        )
        return payload

    @on('Heartbeat')
    async def on_heartbeat(self, **kwargs):
        self.logger.debug(f"💖 Heartbeat received from {self.id}")
        return ocpp_call_result_v201.Heartbeat(
            current_time=datetime.utcnow().isoformat()
        )

    @on('StatusNotification')
    async def on_status_notification(self,
            connector_id: int,
            connector_status: ocpp_enums_v201.ConnectorStatusEnumType,
            evse_id: int,
            **kwargs
    ):
        self.logger.info(f"📊 StatusNotification received from {self.id}: Connector {connector_id} on EVSE {evse_id} is {connector_status}")
        # Lógica para atualizar o status do conector no seu banco de dados, se aplicável
        # await self._update_connector_status(self.id, evse_id, connector_id, connector_status) # Temporarily commented out
        return ocpp_call_result_v201.StatusNotification()

    @on('TransactionEvent')
    async def on_transaction_event(self,
            event_type: ocpp_enums_v201.TransactionEventEnumType,
            timestamp: str,
            trigger_reason: ocpp_enums_v201.TriggerReasonEnumType,
            seq_no: int,
            transaction_info: ocpp_datatypes_v201.TransactionType,
            **kwargs
    ):
        self.logger.info(f"🔄 TransactionEvent received from {self.id}: Type={event_type}, Trigger={trigger_reason}, TransactionID={transaction_info.transaction_id}")
        # Lógica para processar eventos de transação (início, atualização, fim)
        # await self._process_transaction_event( # Temporarily commented out
        #     self.id, event_type, transaction_info, trigger_reason, timestamp
        # )
        return ocpp_call_result_v201.TransactionEvent()

    @on('Authorize')
    async def on_authorize(self,
            id_token: ocpp_datatypes_v201.IdTokenType,
            **kwargs
    ):
        self.logger.info(f"🔑 Authorize request received from {self.id} for ID Token: {id_token.id_token}")
        # Lógica para autorizar o ID Token
        # is_authorized = await self._verify_token_authorization(id_token.id_token) # Temporarily commented out
        is_authorized = True # Assume authorized for testing
        id_token_info = ocpp_datatypes_v201.IdTokenInfoType(
            status=ocpp_enums_v201.AuthorizationStatusEnumType.accepted if is_authorized
            else ocpp_enums_v201.AuthorizationStatusEnumType.invalid
        )
        return ocpp_call_result_v201.Authorize(
            id_token_info=id_token_info
        )

    @on('MeterValues')
    async def on_meter_values(self,
            evse_id: int,
            meter_value: list[ocpp_datatypes_v201.MeterValueType],
            **kwargs
    ):
        self.logger.info(f"⚡ MeterValues received from {self.id} for EVSE {evse_id}. Values: {meter_value}")
        # Lógica para processar e armazenar os valores do medidor
        # await self._store_meter_values(self.id, evse_id, meter_value) # Temporarily commented out
        return ocpp_call_result_v201.MeterValues()

    @on('DataTransfer')
    async def on_data_transfer(self,
            vendor_id: str,
            message_id: Optional[str] = None,
            data: Optional[str] = None,
            **kwargs
    ):
        self.logger.info(f"📦 DataTransfer received from {self.id} (Vendor: {vendor_id}, MessageId: {message_id}): {data}")
        # Lógica para lidar com transferências de dados personalizadas
        return ocpp_call_result_v201.DataTransfer(
            status=ocpp_enums_v201.DataTransferStatusEnumType.accepted
        )

    @on('FirmwareStatusNotification')
    async def on_firmware_status_notification(self,
            status: ocpp_enums_v201.FirmwareStatusEnumType,
            **kwargs
    ):
        self.logger.info(f"🔄 FirmwareStatusNotification received from {self.id}: {status}")
        return ocpp_call_result_v201.FirmwareStatusNotification()

    @on('LogStatusNotification')
    async def on_log_status_notification(self,
            status: ocpp_enums_v201.LogStatusEnumType,
            **kwargs
    ):
        self.logger.info(f"📝 LogStatusNotification received from {self.id}: {status}")
        return ocpp_call_result_v201.LogStatusNotification()

    # Helper methods (moved from ocpp_handlers.py in the previous full version)
    async def _update_connector_status(self, charge_point_id: str, evse_id: int,
                                       connector_id: int, status: str):
        """Update connector status in database"""
        self.logger.info(f"DATABASE_MOCK: Updating connector status for {charge_point_id} to {status}")
        # try:
        #     from ev_charging_system.data.database import get_db
        #     from ev_charging_system.data.repositories import ChargePointRepository
        #     db_session = next(get_db())
        #     try:
        #         cp_repo = ChargePointRepository(db_session)
        #         # Update connector status logic here
        #         self.logger.debug(f"Updated connector status for {charge_point_id}")
        #     finally:
        #         db_session.close()
        # except Exception as e:
        #     self.logger.error(f"Error updating connector status: {e}")

    async def _process_transaction_event(self, charge_point_id: str, event_type: str,
                                         transaction_info: Dict, trigger_reason: str,
                                         timestamp: str):
        """Process transaction event"""
        self.logger.info(f"DATABASE_MOCK: Processing transaction event for {charge_point_id}, type {event_type}")
        # try:
        #     transaction_id = transaction_info.get('transaction_id')
        #     if event_type == 'Started':
        #         self.logger.info(f"Transaction {transaction_id} started on {charge_point_id}")
        #     elif event_type == 'Updated':
        #         self.logger.info(f"Transaction {transaction_id} updated on {charge_point_id}")
        #     elif event_type == 'Ended':
        #         self.logger.info(f"Transaction {transaction_id} ended on {charge_point_id}")
        #     from ev_charging_system.data.database import get_db
        #     from ev_charging_system.data.repositories import TransactionRepository
        #     db_session = next(get_db())
        #     try:
        #         tx_repo = TransactionRepository(db_session)
        #         # Transaction processing logic here
        #         self.logger.debug(f"Processed transaction event for {charge_point_id}")
        #     finally:
        #         db_session.close()
        # except Exception as e:
        #     self.logger.error(f"Error processing transaction event: {e}")

    async def _verify_token_authorization(self, token_value: str) -> bool:
        """Verify if token is authorized"""
        self.logger.info(f"DATABASE_MOCK: Verifying token authorization for {token_value}")
        # try:
        #     from ev_charging_system.data.database import get_db
        #     from ev_charging_system.data.repositories import UserRepository
        #     db_session = next(get_db())
        #     try:
        #         user_repo = UserRepository(db_session)
        #         # Token verification logic here
        #         return True
        #     finally:
        #         db_session.close()
        # except Exception as e:
        #     self.logger.error(f"Error verifying token: {e}")
        return True # Always return True for testing when mocked

    async def _store_meter_values(self, charge_point_id: str, evse_id: int,
                                  meter_values: list):
        """Store meter values in database"""
        self.logger.info(f"DATABASE_MOCK: Storing meter values for {charge_point_id}")
        # try:
        #     # Store meter values logic here
        #     self.logger.debug(f"Stored meter values for {charge_point_id}")
        # except Exception as e:
        #     self.logger.error(f"Error storing meter values: {e}")


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
        charge_point_id = path.strip('/')
        if not charge_point_id:
            logger.warning("Connection attempt with empty charge point ID. Closing connection.")
            await websocket.close()
            return

        logger.info(f"🔌 New connection from Charge Point: {charge_point_id}")
        logger.info(f"Subprotocol selected: {websocket.subprotocol}")

        if charge_point_id in connected_charge_points:
            logger.warning(f"Charge Point {charge_point_id} already connected. Replacing connection.")
            await self._disconnect_charge_point(charge_point_id)

        try:
            charge_point = CustomChargePoint(
                charge_point_id,
                websocket
            )
            logger.info(f"OCPP server: CustomChargePoint instance created for {charge_point_id}.")

            connected_charge_points[charge_point_id] = charge_point
            logger.info(f"✅ Registered Charge Point: {charge_point_id}")

            # Update database status to online - TEMPORARILY COMMENTED OUT
            # await self._update_cp_status_in_db(charge_point_id, "Online")

            logger.info(f"🚀 Starting message processing for {charge_point_id}")
            await charge_point.start() # This call blocks until the connection is closed

        except websockets.exceptions.ConnectionClosedOK:
            logger.info(f"Charge Point {charge_point_id} disconnected normally (ConnectionClosedOK).")
        except websockets.exceptions.ConnectionClosed as e:
            logger.warning(f"Charge Point {charge_point_id} connection closed: {e}")
        except Exception as e:
            logger.error(f"Error with Charge Point {charge_point_id}: {e}", exc_info=True)
        finally:
            logger.info(f"OCPP server: Entering finally block for {charge_point_id}. Disconnecting charge point.")
            await self._disconnect_charge_point(charge_point_id)

    async def _disconnect_charge_point(self, charge_point_id: str):
        """Disconnect a charge point and clean up resources."""
        if charge_point_id not in connected_charge_points:
            logger.debug(f"OCPP server: Attempted to disconnect {charge_point_id} but not in connected list.")
            return

        logger.info(f"🔌 Disconnecting Charge Point {charge_point_id}")

        cp_instance = connected_charge_points.pop(charge_point_id, None)

        # Update database status to offline - TEMPORARILY COMMENTED OUT
        # await self._update_cp_status_in_db(charge_point_id, "Offline")

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
        self.logger.info(f"DATABASE_MOCK: Updating CP {charge_point_id} status to {status}")
        # try:
        #     from ev_charging_system.data.database import get_db
        #     from ev_charging_system.data.repositories import ChargePointRepository, TransactionRepository, \
        #         UserRepository
        #     from ev_charging_system.business_logic.device_management_service import DeviceManagementService
        #     db_session = next(get_db())
        #     try:
        #         cp_repo = ChargePointRepository(db_session)
        #         tx_repo = TransactionRepository(db_session)
        #         user_repo = UserRepository(db_session)
        #         device_service = DeviceManagementService(cp_repo, tx_repo, user_repo)
        #         device_service.update_charge_point_status(charge_point_id, status)
        #         logger.debug(f"Updated Charge Point {charge_point_id} status to {status} in database")
        #     finally:
        #         db_session.close()
        # except Exception as e:
        #     logger.error(f"Error updating CP {charge_point_id} status in DB: {e}", exc_info=True)

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

            payload = ocpp_call_v201.RemoteStartTransaction(
                id_token=id_token,
                remote_start_id=remote_start_id,
                evse_id=connector_id
            )
            response = await cp.remote_start_transaction(payload)

        elif command_name == "RemoteStopTransaction":
            transaction_id = kwargs.get("transaction_id")
            if not transaction_id:
                raise ValueError("transaction_id is required for RemoteStopTransaction")

            payload = ocpp_call_v201.RemoteStopTransaction(
                transaction_id=transaction_id
            )
            response = await cp.remote_stop_transaction(payload)

        elif command_name == "UnlockConnector":
            evse_id = kwargs.get("connector_id", 1)
            connector_id = kwargs.get("connector_id", 1)

            payload = ocpp_call_v201.UnlockConnector(
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

            payload = ocpp_call_v201.Reset(type=reset_type_enum)
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

            payload = ocpp_call_v201.GetVariables(
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

            payload = ocpp_call_v201.SetVariables(
                set_variable_data=[set_variable_data]
            )
            response = await cp.set_variables(payload)

        elif command_name == "ClearCache":
            payload = ocpp_call_v201.ClearCache()
            response = await cp.clear_cache(payload)

        elif command_name == "DataTransfer":
            vendor_id = kwargs.get("vendor_id")
            message_id = kwargs.get("message_id")
            data = kwargs.get("data")

            if not vendor_id or not message_id:
                raise ValueError("vendor_id and message_id are required for DataTransfer")

            payload = ocpp_call_v201.DataTransfer(
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

            payload = ocpp_call_v201.TriggerMessage(
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

        if hasattr(response, 'to_json'):
            return {
                "status": "success",
                "response": response.to_json(),
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
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
    """
    if not connected_charge_points:
        logger.warning("No charge points connected for broadcast")
        return {}

    logger.info(f"📡 Broadcasting {command_name} to {len(connected_charge_points)} charge points")

    results = {}
    tasks = []

    for cp_id in list(connected_charge_points.keys()):
        task = send_ocpp_command(cp_id, command_name, **kwargs)
        tasks.append((cp_id, task))

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
ocpp_server = OCPPServer("0.0.0.0", 9000)


# Compatibility functions for existing code
async def start_ocpp_server(host: str = "0.0.0.0", port: int = 9000):
    """Start the OCPP server (compatibility function)."""
    global ocpp_server
    if ocpp_server.host != host or ocpp_server.port != port or not ocpp_server._running:
        ocpp_server = OCPPServer(host, port)
    await ocpp_server.start()


def get_connected_charge_points() -> Dict[str, OCPPCp]:
    """Get all connected charge points (compatibility function)."""
    return connected_charge_points.copy()


def is_charge_point_connected(charge_point_id: str) -> bool:
    """Check if a charge point is connected (compatibility function)."""
    return charge_point_id in connected_charge_points

# ev_charging_system/core/ocpp_server.py

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)

    async def main_server():
        await start_ocpp_server()

    try:
        asyncio.run(main_server())
    except KeyboardInterrupt:
        logger.info("Servidor OCPP interrompido manualmente.")
    except Exception as e:
        logger.error(f"Erro inesperado ao executar o servidor OCPP: {e}", exc_info=True)
