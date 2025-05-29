# ev_charging_system/core/ocpp_handlers.py

from datetime import datetime
import logging
from ocpp.routing import on
from ocpp.v16.enums import Action, RegistrationStatus, ChargePointStatus
from ocpp.v16 import call_result
from ocpp.v16.datatypes import IdTagInfo # <--- ESSA É A IMPORTAÇÃO CORRETA AGORA!

# Importe sua base de dados e serviços
from ev_charging_system.data.database import SessionLocal, get_db
from ev_charging_system.business_logic.device_management_service import DeviceManagementService
from ev_charging_system.models.charge_point import ChargePointConnector

logger = logging.getLogger(__name__)

# --- Handlers OCPP ---

# A decorator @on(Action.BootNotification) mapeia essa função para a ação BootNotification do OCPP
@on(Action.BootNotification)
async def handle_boot_notification(
    charge_point_id: str,
    vendor_name: str,
    model: str,
    firmware_version: str,
    **kwargs # Captura quaisquer outros argumentos enviados
):
    """
    Handler para a mensagem BootNotification.
    Quando um CP inicia, ele envia esta mensagem para se registrar.
    """
    logger.info(f"BootNotification from CP: {charge_point_id} - Vendor: {vendor_name}, Model: {model}, FW: {firmware_version}")

    db_session = next(get_db()) # Obtém uma nova sessão de BD
    device_service = DeviceManagementService(db_session)

    try:
        connectors_data = [] # Por enquanto, assumimos que BootNotification 1.6 não envia detalhes completos de conectores

        charge_point = device_service.register_or_update_charge_point(
            cp_id=charge_point_id,
            vendor_name=vendor_name,
            model=model,
            firmware_version=firmware_version,
            status="Online", # Define o status inicial como Online
            connectors_data=connectors_data,
            location=kwargs.get('charge_point_location'),
            latitude=kwargs.get('charge_point_latitude'),
            longitude=kwargs.get('charge_point_longitude')
        )
        # Atualiza o last_boot_time após o sucesso do registro/atualização
        charge_point.last_boot_time = datetime.utcnow()
        charge_point.last_heartbeat_time = datetime.utcnow() # Também atualiza o heartbeat
        device_service.charge_point_repo.update_charge_point(charge_point) # Salva a atualização do tempo

        logger.info(f"Charge Point {charge_point_id} registered/updated successfully.")
        # Retorna uma resposta de sucesso para o Charge Point
        return call_result.BootNotification(
            status=RegistrationStatus.accepted,
            interval=300 # Intervalo para Heartbeat em segundos (5 minutos)
        )
    except Exception as e:
        logger.error(f"Error handling BootNotification for {charge_point_id}: {e}")
        return call_result.BootNotification(
            status=RegistrationStatus.rejected,
            interval=300
        )
    finally:
        db_session.close()

@on(Action.Heartbeat)
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

@on(Action.StatusNotification)
async def handle_status_notification(
    charge_point_id: str,
    connector_id: int,
    status: str,
    **kwargs
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
            current_transaction_id=kwargs.get('transaction_id')
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

@on(Action.Authorize)
async def handle_authorize(charge_point_id: str, id_tag: str):
    logger.info(f"Authorize request from {charge_point_id} for ID Tag: {id_tag}")
    # Use IdTagInfo.Accepted, não IdTagInfoStatus.accepted
    return call_result.Authorize(id_tag_info={"status": IdTagInfo.Accepted})

@on(Action.StartTransaction)
async def handle_start_transaction(charge_point_id: str, connector_id: int, id_tag: str, meter_start: int, **kwargs):
    logger.info(f"StartTransaction from {charge_point_id} on connector {connector_id} for ID Tag: {id_tag}")
    # Use IdTagInfo.Accepted, não IdTagInfoStatus.accepted
    return call_result.StartTransaction(id_tag_info={"status": IdTagInfo.Accepted}, transaction_id=123)