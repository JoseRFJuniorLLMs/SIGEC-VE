# ev_charging_system/core/ocpp_handlers.py

import logging
from ocpp.v16 import ChargePoint as OCPPCp
from ocpp.v16 import call_result
# Removido 'ErrorCode' daqui. Ele não está disponível para importação direta em ocpp.v16.enums
from ocpp.v16.enums import RegistrationStatus, AuthorizationStatus, Action, ChargePointStatus
from ocpp.routing import on
from datetime import datetime

# IMPORTANTE: Importe os modelos da sua ÚNICA FONTE DE VERDADE: ev_charging_system/data/models.py
from ev_charging_system.data.models import ChargePoint, Connector, Transaction, User
# Importe as dependências de serviço e repositório
from ev_charging_system.data.database import get_db
from ev_charging_system.business_logic.device_management_service import DeviceManagementService
from ev_charging_system.business_logic.transaction_service import TransactionService

logger = logging.getLogger(__name__)


# Função auxiliar para obter o serviço e a sessão do DB
def get_service_and_db_session():
    db_session = next(get_db())
    # O DeviceManagementService e TransactionService precisam dos repositórios
    # Para simplicidade aqui, vamos instanciar os repositórios diretamente com a sessão.
    from ev_charging_system.data.repositories import ChargePointRepository, TransactionRepository, UserRepository
    cp_repo = ChargePointRepository(db_session)
    tx_repo = TransactionRepository(db_session)
    user_repo = UserRepository(db_session)

    device_service = DeviceManagementService(cp_repo, tx_repo, user_repo)
    transaction_service = TransactionService(db_session)
    return device_service, transaction_service, db_session


# --- Handlers para mensagens OCPP ---

@on(Action.boot_notification)
async def on_boot_notification(charge_point: OCPPCp, charge_point_model: str, charge_point_vendor: str, **kwargs):
    """
    Handle a BootNotification request from a Charge Point.
    This is the first message a CP sends after booting up.
    """
    logger.info(f"BootNotification from {charge_point.id} (Model: {charge_point_model}, Vendor: {charge_point_vendor})")

    device_service, transaction_service, db_session = get_service_and_db_session()
    try:
        existing_cp = device_service.get_charge_point_by_id(charge_point.id)
        if not existing_cp:
            # Add new Charge Point to DB if it doesn't exist
            num_connectors = kwargs.get('num_connectors', 1)
            device_service.add_charge_point(
                cp_id=charge_point.id,
                vendor=charge_point_vendor,
                model=charge_point_model,
                num_connectors=num_connectors
            )
            logger.info(f"New Charge Point {charge_point.id} added to DB.")
        else:
            # Update existing CP status
            device_service.update_charge_point_status(charge_point.id, "Online")
            logger.info(f"Charge Point {charge_point.id} status updated to Online.")

        # Return a BootNotification confirmation
        return call_result.BootNotification(
            current_time=datetime.utcnow().isoformat(),
            interval=300,  # Heartbeat interval in seconds
            status=RegistrationStatus.accepted
        )
    except Exception as e:
        logger.error(f"Error handling BootNotification for {charge_point.id}: {e}", exc_info=True)
        return call_result.BootNotification(
            current_time=datetime.utcnow().isoformat(),
            interval=300,
            status=RegistrationStatus.rejected
        )
    finally:
        db_session.close()


@on(Action.heartbeat)
async def on_heartbeat(charge_point: OCPPCp):
    """
    Handle a Heartbeat request from a Charge Point.
    """
    logger.debug(f"Heartbeat from {charge_point.id}")
    device_service, transaction_service, db_session = get_service_and_db_session()
    try:
        device_service.update_charge_point_last_heartbeat(charge_point.id)
        return call_result.Heartbeat(current_time=datetime.utcnow().isoformat())
    except Exception as e:
        logger.error(f"Error handling Heartbeat for {charge_point.id}: {e}", exc_info=True)
        return call_result.Heartbeat(current_time=datetime.utcnow().isoformat())
    finally:
        db_session.close()


@on(Action.status_notification)
async def on_status_notification(charge_point: OCPPCp, connector_id: int, status: str, **kwargs):
    """
    Handle a StatusNotification request from a Charge Point.
    This informs the CSMS about status changes of connectors or the CP itself.
    """
    logger.info(f"StatusNotification from {charge_point.id} - Connector {connector_id}: {status}")

    device_service, transaction_service, db_session = get_service_and_db_session()
    try:
        if connector_id == 0:  # ConnectorId 0 usually refers to the CP itself
            device_service.update_charge_point_status(charge_point.id, status)
        else:
            device_service.update_connector_status(charge_point.id, connector_id, status)
        return call_result.StatusNotification()
    except Exception as e:
        logger.error(f"Error handling StatusNotification for {charge_point.id}, connector {connector_id}: {e}",
                     exc_info=True)
        return call_result.StatusNotification()  # StatusNotification does not return errors
    finally:
        db_session.close()


@on(Action.authorize)
async def on_authorize(charge_point: OCPPCp, id_tag: str):
    """
    Handle an Authorize request from a Charge Point.
    Checks if the id_tag is valid.
    """
    logger.info(f"Authorize request from {charge_point.id} for ID Tag: {id_tag}")

    device_service, transaction_service, db_session = get_service_and_db_session()
    try:
        user = device_service.get_user_by_id_tag(id_tag)
        if user and user.is_active:
            logger.info(f"ID Tag {id_tag} authorized for {user.name}.")
            return call_result.Authorize(id_tag_info={"status": AuthorizationStatus.accepted})
        else:
            logger.warning(f"ID Tag {id_tag} not authorized (user not found or inactive).")
            return call_result.Authorize(id_tag_info={"status": AuthorizationStatus.invalid})
    except Exception as e:
        logger.error(f"Error handling Authorize for {charge_point.id}, ID Tag {id_tag}: {e}", exc_info=True)
        return call_result.Authorize(id_tag_info={"status": AuthorizationStatus.invalid})
    finally:
        db_session.close()


@on(Action.start_transaction)
async def on_start_transaction(charge_point: OCPPCp, connector_id: int, id_tag: str, meter_start: int, **kwargs):
    """
    Handle a StartTransaction request from a Charge Point.
    This marks the beginning of a charging session.
    """
    logger.info(
        f"StartTransaction from {charge_point.id} - Connector {connector_id}, ID Tag: {id_tag}, Meter Start: {meter_start}")

    transaction_id = kwargs.get('transaction_id')
    if not transaction_id:
        transaction_id = f"TX-{charge_point.id}-{datetime.utcnow().timestamp()}"

    device_service, transaction_service, db_session = get_service_and_db_session()
    try:
        user = device_service.get_user_by_id_tag(id_tag)
        if not user or not user.is_active:
            logger.warning(f"StartTransaction refused for {charge_point.id} due to invalid/inactive ID Tag: {id_tag}")
            return call_result.StartTransaction(transaction_id=0, id_tag_info={"status": AuthorizationStatus.invalid})

        new_transaction = await transaction_service.start_transaction(
            charge_point_id=charge_point.id,
            connector_id=connector_id,
            id_tag=id_tag,
            meter_start=float(meter_start),
            transaction_id=transaction_id
        )

        logger.info(
            f"Transaction {new_transaction.transaction_id} successfully started for {charge_point.id}, Connector {connector_id}")
        return call_result.StartTransaction(
            transaction_id=new_transaction.id,  # O OCPP TransactionId é o ID INTERNO no CSMS
            id_tag_info={"status": AuthorizationStatus.accepted}
        )
    except ValueError as ve:
        logger.error(f"Validation error in StartTransaction for {charge_point.id}: {ve}")
        return call_result.StartTransaction(transaction_id=0, id_tag_info={"status": AuthorizationStatus.invalid})
    except Exception as e:
        logger.error(f"Error handling StartTransaction for {charge_point.id}: {e}", exc_info=True)
        return call_result.StartTransaction(transaction_id=0, id_tag_info={"status": AuthorizationStatus.invalid})
    finally:
        db_session.close()


@on(Action.stop_transaction)
async def on_stop_transaction(charge_point: OCPPCp, transaction_id: int, meter_stop: int, **kwargs):
    """
    Handle a StopTransaction request from a Charge Point.
    This marks the end of a charging session.
    """
    logger.info(f"StopTransaction from {charge_point.id} - Transaction ID: {transaction_id}, Meter Stop: {meter_stop}")

    device_service, transaction_service, db_session = get_service_and_db_session()
    try:
        existing_transaction = db_session.query(Transaction).filter(Transaction.id == transaction_id).first()

        if not existing_transaction:
            logger.warning(f"StopTransaction received for unknown Transaction ID: {transaction_id}")
            return call_result.StopTransaction(id_tag_info={"status": AuthorizationStatus.invalid})

        if existing_transaction.status == "Completed":
            logger.warning(f"StopTransaction received for already completed transaction {transaction_id}. Ignoring.")
            return call_result.StopTransaction(id_tag_info={"status": AuthorizationStatus.accepted})

        energy_transfered = float(meter_stop) - existing_transaction.meter_start
        if energy_transfered < 0:
            logger.warning(
                f"Negative energy transfered for transaction {transaction_id}. Meter start: {existing_transaction.meter_start}, Meter stop: {meter_stop}")
            energy_transfered = 0.0

        updated_transaction = await transaction_service.stop_transaction(
            transaction_id=str(existing_transaction.transaction_id),
            meter_stop=float(meter_stop),
            energy_transfered=energy_transfered
        )

        logger.info(
            f"Transaction {updated_transaction.transaction_id} stopped. Energy: {updated_transaction.energy_transfered} kWh.")
        return call_result.StopTransaction(id_tag_info={"status": AuthorizationStatus.accepted})
    except ValueError as ve:
        logger.error(f"Validation error in StopTransaction for {charge_point.id}: {ve}")
        return call_result.StopTransaction(id_tag_info={"status": AuthorizationStatus.invalid})
    except Exception as e:
        logger.error(f"Error handling StopTransaction for {charge_point.id}: {e}", exc_info=True)
        return call_result.StopTransaction(id_tag_info={"status": AuthorizationStatus.invalid})
    finally:
        db_session.close()


@on(Action.meter_values)
async def on_meter_values(charge_point: OCPPCp, connector_id: int, transaction_id: int, meter_value: list, **kwargs):
    """
    Handle MeterValues from a Charge Point.
    This provides periodic meter readings during a transaction.
    """
    logger.debug(f"MeterValues from {charge_point.id} - Conn {connector_id}, Tx {transaction_id}: {meter_value}")

    return call_result.MeterValues()