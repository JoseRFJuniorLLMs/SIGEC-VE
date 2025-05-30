# ev_charging_system/core/ocpp_handlers.py

from datetime import datetime
import logging
from ocpp.routing import on
from ocpp.v16.enums import RegistrationStatus, ChargePointStatus # Remover Action daqui!
from ocpp.v16 import call_result
from ocpp.v16.datatypes import IdTagInfo # Importação correta!

# Importe sua base de dados e serviços
from ev_charging_system.data.database import SessionLocal, get_db
from ev_charging_system.business_logic.device_management_service import DeviceManagementService
from ev_charging_system.business_logic.transaction_service import TransactionService # NOVO IMPORT
from ev_charging_system.models.charge_point import ChargePointConnector

logger = logging.getLogger(__name__)


# --- Handlers OCPP ---

@on("BootNotification")
async def handle_boot_notification(
    charge_point_id: str,
    vendor_name: str,
    model: str,
    firmware_version: str,
    **kwargs,  # Captura quaisquer outros argumentos enviados
):
    """
    Handler para a mensagem BootNotification.
    Quando um CP inicia, ele envia esta mensagem para se registrar.
    """
    logger.info(
        f"BootNotification from CP: {charge_point_id} - Vendor: {vendor_name}, Model: {model}, FW: {firmware_version}"
    )

    db_session = next(get_db())  # Obtém uma nova sessão de BD
    device_service = DeviceManagementService(db_session)

    try:
        connectors_data = []

        charge_point = device_service.register_or_update_charge_point(
            cp_id=charge_point_id,
            vendor_name=vendor_name,
            model=model,
            firmware_version=firmware_version,
            status="Online",
            connectors_data=connectors_data,
            location=kwargs.get("charge_point_location"),
            latitude=kwargs.get("charge_point_latitude"),
            longitude=kwargs.get("charge_point_longitude"),
        )
        charge_point.last_boot_time = datetime.utcnow()
        charge_point.last_heartbeat_time = datetime.utcnow()
        device_service.charge_point_repo.update_charge_point(
            charge_point
        )

        logger.info(f"Charge Point {charge_point_id} registered/updated successfully.")
        return call_result.BootNotification(
            status=RegistrationStatus.accepted, interval=300
        )
    except Exception as e:
        logger.error(f"Error handling BootNotification for {charge_point_id}: {e}")
        return call_result.BootNotification(status=RegistrationStatus.rejected, interval=300)
    finally:
        db_session.close()


@on("Heartbeat")
async def handle_heartbeat(charge_point_id: str):
    """
    Handler para a mensagem Heartbeat.
    Usado para manter a conexão ativa e informar que o CP está online.
    """
    logger.debug(f"Heartbeat from CP: {charge_point_id}")

    db_session = next(get_db())
    device_service = DeviceManagementService(db_session)

    try:
        charge_point = device_service.get_charge_point_details(charge_point_id)
        if charge_point:
            charge_point.last_heartbeat_time = datetime.utcnow()
            device_service.charge_point_repo.update_charge_point(charge_point)
            logger.debug(f"Updated last_heartbeat_time for {charge_point_id}")
        else:
            logger.warning(f"Heartbeat from unknown CP: {charge_point_id}. Consider forcing a BootNotification.")
        return call_result.Heartbeat(current_time=datetime.utcnow().isoformat())
    except Exception as e:
        logger.error(f"Error handling Heartbeat for {charge_point_id}: {e}")
        return call_result.Heartbeat(current_time=datetime.utcnow().isoformat())
    finally:
        db_session.close()


@on("StatusNotification")
async def handle_status_notification(
    charge_point_id: str,
    connector_id: int,
    status: str,
    **kwargs,
):
    """
    Handler para a mensagem StatusNotification.
    Informa sobre mudanças de status do CP ou de um conector.
    """
    logger.info(f"StatusNotification from CP: {charge_point_id}, Connector: {connector_id}, Status: {status}")

    db_session = next(get_db())
    device_service = DeviceManagementService(db_session)

    try:
        updated_connector = device_service.update_connector_status(
            cp_id=charge_point_id,
            connector_id=connector_id,
            status=status,
            current_transaction_id=kwargs.get("transaction_id"),
        )
        if updated_connector:
            logger.info(f"Connector {charge_point_id}-{connector_id} status updated to {status}.")
        else:
            logger.warning(f"StatusNotification for unknown connector {charge_point_id}-{connector_id}.")

        if connector_id == 0:
            device_service.update_charge_point_status(charge_point_id, status)
            logger.info(f"Charge Point {charge_point_id} overall status updated to {status}.")

        return call_result.StatusNotification()
    except Exception as e:
        logger.error(f"Error handling StatusNotification for {charge_point_id}-{connector_id}: {e}")
        return call_result.StatusNotification()
    finally:
        db_session.close()


@on("Authorize")
async def handle_authorize(charge_point_id: str, id_tag: str):
    logger.info(f"Authorize request from {charge_point_id} for ID Tag: {id_tag}")
    return call_result.Authorize(id_tag_info={"status": IdTagInfo.Accepted})


@on("StartTransaction")
async def handle_start_transaction(
    charge_point_id: str, connector_id: int, id_tag: str, meter_start: int, timestamp: str, transaction_id: int, **kwargs
):
    """
    Handler para a mensagem StartTransaction.
    O Charge Point inicia uma transação e notifica o CSMS.
    """
    logger.info(
        f"StartTransaction from CP: {charge_point_id} - Connector: {connector_id}, ID Tag: {id_tag}, "
        f"Meter Start: {meter_start}, Timestamp: {timestamp}, Transaction ID (CP): {transaction_id}"
    )

    db_session = next(get_db())
    try:
        transaction_service = TransactionService(db_session)
        # Chama o serviço de transação para persistir os detalhes
        await transaction_service.handle_start_transaction_from_cp(
            charge_point_id=charge_point_id,
            connector_id=connector_id,
            id_tag=id_tag,
            meter_start=meter_start,
            start_timestamp=datetime.fromisoformat(timestamp.replace('Z', '+00:00')), # Adapta para datetime com fuso horário
            ocpp_transaction_id=transaction_id # ID da transação que o CP está reportando
        )
        # Retorna Accepted para o Charge Point
        return call_result.StartTransaction(id_tag_info={"status": IdTagInfo.Accepted}, transaction_id=transaction_id)
    except Exception as e:
        logger.error(f"Error handling StartTransaction for {charge_point_id}: {e}", exc_info=True)
        # Em caso de erro, pode retornar um status diferente, mas Accepted é comum para evitar reenvios.
        return call_result.StartTransaction(id_tag_info={"status": IdTagInfo.Blocked}, transaction_id=transaction_id)
    finally:
        db_session.close()


@on("StopTransaction")
async def handle_stop_transaction(
    charge_point_id: str, transaction_id: int, meter_stop: int, timestamp: str, reason: str, **kwargs
):
    """
    Handler para a mensagem StopTransaction.
    O Charge Point finaliza uma transação e notifica o CSMS.
    """
    logger.info(
        f"StopTransaction from CP: {charge_point_id} - Transaction ID (CP): {transaction_id}, "
        f"Meter Stop: {meter_stop}, Timestamp: {timestamp}, Reason: {reason}"
    )

    db_session = next(get_db())
    try:
        transaction_service = TransactionService(db_session)
        # Chama o serviço de transação para finalizar os detalhes
        await transaction_service.handle_stop_transaction_from_cp(
            charge_point_id=charge_point_id,
            ocpp_transaction_id=transaction_id,
            meter_stop=meter_stop,
            stop_timestamp=datetime.fromisoformat(timestamp.replace('Z', '+00:00')), # Adapta para datetime com fuso horário
            reason=reason
        )
        # Retorna Accepted para o Charge Point
        return call_result.StopTransaction()
    except Exception as e:
        logger.error(f"Error handling StopTransaction for {charge_point_id}: {e}", exc_info=True)
        return call_result.StopTransaction() # Em caso de erro, ainda responde
    finally:
        db_session.close()