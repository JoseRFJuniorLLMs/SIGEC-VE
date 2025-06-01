# ev_charging_system/core/ocpp_handlers.py

import logging
from datetime import datetime
from typing import Dict, Any, Optional

# OCPP 2.0.1 imports
from ocpp.v201 import call as ocpp_call_v201
from ocpp.v201 import call_result as ocpp_call_result_v201
from ocpp.v201 import enums as ocpp_enums_v201
from ocpp.v201 import datatypes as ocpp_datatypes_v201
from ocpp.routing import on

logger = logging.getLogger(__name__)


class OCPP201Handlers:
    """OCPP 2.0.1 Message Handlers"""

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @on('BootNotification')
    async def on_boot_notification(self, charge_point_id: str, **kwargs):
        """Handle BootNotification from charge point"""
        self.logger.info(f"📡 BootNotification received from {charge_point_id}")
        self.logger.info(f"Boot data: {kwargs}")

        # Extract boot notification data
        charging_station = kwargs.get('charging_station', {})
        reason = kwargs.get('reason', 'Unknown')

        self.logger.info(f"Charging Station Info: {charging_station}")
        self.logger.info(f"Boot Reason: {reason}")

        # Return BootNotificationResponse
        return ocpp_call_result_v201.BootNotificationPayload(
            current_time=datetime.utcnow().isoformat(),
            interval=300,  # Heartbeat interval in seconds
            status=ocpp_enums_v201.RegistrationStatusEnumType.accepted
        )

    @on('Heartbeat')
    async def on_heartbeat(self, charge_point_id: str, **kwargs):
        """Handle Heartbeat from charge point"""
        self.logger.debug(f"💓 Heartbeat received from {charge_point_id}")

        return ocpp_call_result_v201.HeartbeatPayload(
            current_time=datetime.utcnow().isoformat()
        )

    @on('StatusNotification')
    async def on_status_notification(self, charge_point_id: str, **kwargs):
        """Handle StatusNotification from charge point"""
        timestamp = kwargs.get('timestamp')
        connector_status = kwargs.get('connector_status')
        evse_id = kwargs.get('evse_id')
        connector_id = kwargs.get('connector_id')

        self.logger.info(f"🔌 Status update from {charge_point_id}")
        self.logger.info(f"EVSE {evse_id}, Connector {connector_id}: {connector_status} at {timestamp}")

        # Update database with status
        await self._update_connector_status(charge_point_id, evse_id, connector_id, connector_status)

        return ocpp_call_result_v201.StatusNotificationPayload()

    @on('TransactionEvent')
    async def on_transaction_event(self, charge_point_id: str, **kwargs):
        """Handle TransactionEvent from charge point"""
        event_type = kwargs.get('event_type')
        timestamp = kwargs.get('timestamp')
        transaction_info = kwargs.get('transaction_info', {})
        trigger_reason = kwargs.get('trigger_reason')

        transaction_id = transaction_info.get('transaction_id')

        self.logger.info(f"🔄 Transaction event from {charge_point_id}")
        self.logger.info(f"Event: {event_type}, Transaction: {transaction_id}")
        self.logger.info(f"Trigger: {trigger_reason}, Time: {timestamp}")

        # Process transaction event
        await self._process_transaction_event(
            charge_point_id, event_type, transaction_info, trigger_reason, timestamp
        )

        return ocpp_call_result_v201.TransactionEventPayload()

    @on('Authorize')
    async def on_authorize(self, charge_point_id: str, **kwargs):
        """Handle Authorize request from charge point"""
        id_token = kwargs.get('id_token', {})
        token_value = id_token.get('id_token', 'Unknown')
        token_type = id_token.get('type', 'Unknown')

        self.logger.info(f"🔐 Authorization request from {charge_point_id}")
        self.logger.info(f"Token: {token_value} (Type: {token_type})")

        # Verify token authorization
        is_authorized = await self._verify_token_authorization(token_value)

        id_token_info = ocpp_datatypes_v201.IdTokenInfoType(
            status=ocpp_enums_v201.AuthorizationStatusEnumType.accepted if is_authorized
            else ocpp_enums_v201.AuthorizationStatusEnumType.invalid
        )

        return ocpp_call_result_v201.AuthorizePayload(
            id_token_info=id_token_info
        )

    @on('MeterValues')
    async def on_meter_values(self, charge_point_id: str, **kwargs):
        """Handle MeterValues from charge point"""
        evse_id = kwargs.get('evse_id')
        meter_value = kwargs.get('meter_value', [])

        self.logger.info(f"⚡ Meter values from {charge_point_id}, EVSE {evse_id}")

        for mv in meter_value:
            timestamp = mv.get('timestamp')
            sampled_value = mv.get('sampled_value', [])

            for sv in sampled_value:
                value = sv.get('value')
                measurand = sv.get('measurand', 'Unknown')
                unit = sv.get('unit', 'Unknown')

                self.logger.debug(f"📊 {measurand}: {value} {unit} at {timestamp}")

        # Store meter values
        await self._store_meter_values(charge_point_id, evse_id, meter_value)

        return ocpp_call_result_v201.MeterValuesPayload()

    @on('DataTransfer')
    async def on_data_transfer(self, charge_point_id: str, **kwargs):
        """Handle DataTransfer from charge point"""
        vendor_id = kwargs.get('vendor_id')
        message_id = kwargs.get('message_id')
        data = kwargs.get('data')

        self.logger.info(f"📡 Data transfer from {charge_point_id}")
        self.logger.info(f"Vendor: {vendor_id}, Message: {message_id}")
        self.logger.info(f"Data: {data}")

        return ocpp_call_result_v201.DataTransferPayload(
            status=ocpp_enums_v201.DataTransferStatusEnumType.accepted
        )

    @on('FirmwareStatusNotification')
    async def on_firmware_status_notification(self, charge_point_id: str, **kwargs):
        """Handle FirmwareStatusNotification from charge point"""
        status = kwargs.get('status')
        request_id = kwargs.get('request_id')

        self.logger.info(f"🔧 Firmware status from {charge_point_id}: {status}")
        if request_id:
            self.logger.info(f"Request ID: {request_id}")

        return ocpp_call_result_v201.FirmwareStatusNotificationPayload()

    @on('LogStatusNotification')
    async def on_log_status_notification(self, charge_point_id: str, **kwargs):
        """Handle LogStatusNotification from charge point"""
        status = kwargs.get('status')
        request_id = kwargs.get('request_id')

        self.logger.info(f"📝 Log status from {charge_point_id}: {status}")
        if request_id:
            self.logger.info(f"Request ID: {request_id}")

        return ocpp_call_result_v201.LogStatusNotificationPayload()

    # Helper methods
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


# Create handlers instance
handlers = OCPP201Handlers()

# Export handler methods for route mapping
ocpp_handlers = {
    'BootNotification': handlers.on_boot_notification,
    'Heartbeat': handlers.on_heartbeat,
    'StatusNotification': handlers.on_status_notification,
    'TransactionEvent': handlers.on_transaction_event,
    'Authorize': handlers.on_authorize,
    'MeterValues': handlers.on_meter_values,
    'DataTransfer': handlers.on_data_transfer,
    'FirmwareStatusNotification': handlers.on_firmware_status_notification,
    'LogStatusNotification': handlers.on_log_status_notification
}