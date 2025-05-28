# ev_charging_system/core/ocpp_handlers.py

from datetime import datetime
import logging
from ocpp.routing import on
from ocpp.v16.enums import Action, RegistrationStatus, ChargePointStatus
from ocpp.v16 import call_result
from ocpp.exceptions import NotSupportedError

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
        # Extrai informações dos conectores, se disponíveis no payload (OCPP 2.0.1 pode ter mais detalhes aqui)
        # Para OCPP 1.6, a info de conectores pode não vir no BootNotification, mas sim em StatusNotification ou via GetConfiguration
        # Vamos assumir que, para o 1.6, podemos adicionar um conector padrão se não houver um existente
        connectors_data = [] # Por enquanto, assumimos que BootNotification 1.6 não envia detalhes completos de conectores
        # Você pode ter um mecanismo para buscar ou inicializar conectores após o boot

        charge_point = device_service.register_or_update_charge_point(
            cp_id=charge_point_id,
            vendor_name=vendor_name,
            model=model,
            firmware_version=firmware_version,
            status="Online", # Define o status inicial como Online
            connectors_data=connectors_data,
            # Campos adicionais como location, latitude, longitude, configuration podem ser passados via kwargs
            # ou obtidos de uma fonte de configuração inicial, ou atualizados posteriormente.
            location=kwargs.get('charge_point_location'), # Exemplo se você enviar isso via BootNotification estendido
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
        # Em caso de erro, você pode decidir se aceita ou rejeita
        return call_result.BootNotification(
            status=RegistrationStatus.rejected,
            interval=300
        )
    finally:
        db_session.close() # Garante que a sessão do banco de dados seja fechada

@on(Action.Heartbeat)
async def handle_heartbeat(charge_point_id: str):
    """
    Handler para a mensagem Heartbeat.
    Usado para manter a conexão ativa e informar que o CP está online.
    """
    logger.debug(f"Heartbeat from CP: {charge_point_id}") # Nível de debug para não poluir logs

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
            # Você pode optar por rejeitar ou solicitar um BootNotification aqui.
            # Por simplicidade, aceitamos, mas avisamos.

        return call_result.Heartbeat(current_time=datetime.utcnow().isoformat())
    except Exception as e:
        logger.error(f"Error handling Heartbeat for {charge_point_id}: {e}")
        # A resposta de erro para Heartbeat é limitada pelo OCPP, apenas logamos.
        return call_result.Heartbeat(current_time=datetime.utcnow().isoformat())
    finally:
        db_session.close()

@on(Action.StatusNotification)
async def handle_status_notification(
    charge_point_id: str,
    connector_id: int,
    status: str, # ChargePointStatus ou ConnectorStatus (OCPP 1.6 vs 2.0.1)
    # OCPP 1.6: status é ChargePointStatus para CP, ou para Conector.
    # OCPP 2.0.1: explicitamente ComponentStatus e ConnectorStatus
    **kwargs # Captura quaisquer outros argumentos como error_code, info
):
    """
    Handler para a mensagem StatusNotification.
    Informa sobre mudanças de status do CP ou de um conector.
    """
    logger.info(f"StatusNotification from CP: {charge_point_id}, Connector: {connector_id}, Status: {status}")

    db_session = next(get_db())
    device_service = DeviceManagementService(db_session)

    try:
        # Atualiza o status do conector específico
        updated_connector = device_service.update_connector_status(
            cp_id=charge_point_id,
            connector_id=connector_id,
            status=status,
            current_transaction_id=kwargs.get('transaction_id') # Se for enviado para status Occupied/Charging
        )
        if updated_connector:
            logger.info(f"Connector {charge_point_id}-{connector_id} status updated to {status}.")
        else:
            logger.warning(f"StatusNotification for unknown connector {charge_point_id}-{connector_id}.")

        # Para o status geral do Charge Point (connector_id = 0 para o CP)
        if connector_id == 0: # OCPP convention for overall Charge Point status
            device_service.update_charge_point_status(charge_point_id, status)
            logger.info(f"Charge Point {charge_point_id} overall status updated to {status}.")

        return call_result.StatusNotification()
    except Exception as e:
        logger.error(f"Error handling StatusNotification for {charge_point_id}-{connector_id}: {e}")
        return call_result.StatusNotification() # Não há status de erro para StatusNotification
    finally:
        db_session.close()

# Você pode adicionar mais handlers para outras ações OCPP aqui, como Authorize, StartTransaction, etc.
# Exemplo (apenas rascunho, a lógica virá de outros serviços):
# @on(Action.Authorize)
# async def handle_authorize(charge_point_id: str, id_tag: str):
#     # Lógica de autenticação viria do auth_service
#     logger.info(f"Authorize request from {charge_point_id} for ID Tag: {id_tag}")
#     return call_result.Authorize(id_tag_info={"status": IdTagInfoStatus.accepted})

# @on(Action.StartTransaction)
# async def handle_start_transaction(charge_point_id: str, connector_id: int, id_tag: str, meter_start: int, **kwargs):
#     # Lógica de iniciar transação viria do transaction_service
#     logger.info(f"StartTransaction from {charge_point_id} on connector {connector_id} for ID Tag: {id_tag}")
#     return call_result.StartTransaction(id_tag_info={"status": IdTagInfoStatus.accepted}, transaction_id=123)