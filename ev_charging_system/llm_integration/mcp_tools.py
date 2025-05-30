# ev_charging_system/llm_integration/mcp_tools.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
import logging

# Importa o serviço de gerenciamento de dispositivos para a lógica de negócio
from ev_charging_system.business_logic.device_management_service import DeviceManagementService
# Importa a função para obter a sessão do banco de dados
from ev_charging_system.data.database import get_db

logger = logging.getLogger(__name__)

# Crie uma instância do APIRouter para as ferramentas MCP
router = APIRouter()


# --- Ferramentas (Actions) que o LLM pode chamar via MCP ---

@router.post("/reset_charge_point")
async def reset_charge_point(
        charge_point_id: str,
        db: Session = Depends(get_db)
):
    """
    Ferramenta para solicitar o reset remoto de um Charge Point.
    O LLM pode chamar isso para reiniciar um posto com problemas.
    """
    logger.info(f"MCP Tool: Received request to reset Charge Point '{charge_point_id}'")
    device_service = DeviceManagementService(db)

    cp = device_service.get_charge_point_details(charge_point_id)
    if not cp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Charge Point '{charge_point_id}' not found.")

    # TODO: Implementar a lógica para enviar o comando OCPP "Reset" para o CP real.
    # Isso exigiria uma forma de acessar o objeto ChargePoint WebSocket conectado
    # (ex: do dicionário connected_charge_points no ocpp_server.py)
    # e enviar o comando OCPP.
    # Exemplo (se a lógica de envio estiver no ocpp_server e for acessível):
    # from ev_charging_system.core.ocpp_server import send_ocpp_command_to_cp
    # success = await send_ocpp_command_to_cp(charge_point_id, "Reset", {"type": "Hard"})
    # if not success:
    #     raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to send Reset command to CP.")

    # Por agora, apenas logamos a intenção e atualizamos o status no DB para "Resetting"
    # O CP real reportaria "BootNotification" após o reset.
    device_service.update_charge_point_status(charge_point_id, "Resetting")

    return {
        "message": f"Reset command initiated for Charge Point '{charge_point_id}'. Actual OCPP command sending needs integration."}


@router.post("/update_charge_point_configuration")
async def update_charge_point_configuration(
        charge_point_id: str,
        configuration_data: Dict[str, Any],  # Ex: {"key": "HeartbeatInterval", "value": "300"}
        db: Session = Depends(get_db)
):
    """
    Ferramenta para atualizar a configuração de um Charge Point.
    Permite ao LLM ajustar parâmetros operacionais.
    """
    logger.info(
        f"MCP Tool: Received request to update config for Charge Point '{charge_point_id}' with {configuration_data}")
    device_service = DeviceManagementService(db)

    cp = device_service.get_charge_point_details(charge_point_id)
    if not cp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Charge Point '{charge_point_id}' not found.")

    # TODO: Implementar a lógica para enviar o comando OCPP "ChangeConfiguration" para o CP real.
    # Você precisaria iterar sobre configuration_data e enviar comandos individuais
    # ou um comando de "SetChargingProfile".

    return {
        "message": f"Configuration update initiated for Charge Point '{charge_point_id}'. Data: {configuration_data}. Actual OCPP command sending needs integration."}


@router.post("/start_ocpp_transaction")
async def start_ocpp_transaction(
        charge_point_id: str,
        connector_id: int,
        id_tag: str,
        meter_start: Optional[int] = 0,  # Valor inicial do medidor
        db: Session = Depends(get_db)
):
    """
    Ferramenta para iniciar uma transação de carregamento OCPP em um conector específico.
    """
    logger.info(
        f"MCP Tool: Request to start transaction on CP '{charge_point_id}', conn '{connector_id}' for ID Tag '{id_tag}'")
    device_service = DeviceManagementService(db)

    # Verifica se o CP e o conector existem
    connector = device_service.charge_point_repo.get_connector_by_id(connector_id, charge_point_id)
    if not connector:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Connector {connector_id} on CP {charge_point_id} not found.")

    if connector.status != "Available":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail=f"Connector {connector_id} on CP {charge_point_id} is not available (status: {connector.status}).")

    # TODO: Implementar a lógica para enviar o comando OCPP "RemoteStartTransaction"
    # Este comando seria enviado do CSMS para o Charge Point.
    # Ex: await send_ocpp_command_to_cp(charge_point_id, "RemoteStartTransaction", {"connectorId": connector_id, "idTag": id_tag})

    # No mundo real, o CP responderia com um StartTransaction.conf e StatusNotification
    # Aqui, estamos apenas simulando a intenção.
    return {
        "message": f"RemoteStartTransaction initiated for CP '{charge_point_id}', Connector '{connector_id}', ID Tag '{id_tag}'. Status: Pending CP response."}


@router.post("/stop_ocpp_transaction")
async def stop_ocpp_transaction(
        transaction_id: int,
        charge_point_id: str,  # Para identificar qual CP enviar o comando
        db: Session = Depends(get_db)
):
    """
    Ferramenta para parar uma transação de carregamento OCPP em andamento.
    """
    logger.info(f"MCP Tool: Request to stop transaction '{transaction_id}' on CP '{charge_point_id}'")

    # TODO: Implementar a lógica para buscar a transação pelo ID
    # e então enviar o comando OCPP "RemoteStopTransaction" para o Charge Point associado.
    # Ex: await send_ocpp_command_to_cp(charge_point_id, "RemoteStopTransaction", {"transactionId": transaction_id})

    return {
        "message": f"RemoteStopTransaction initiated for Transaction '{transaction_id}' on Charge Point '{charge_point_id}'. Status: Pending CP response."}


@router.post("/set_connector_status")
async def set_connector_status(
        charge_point_id: str,
        connector_id: int,
        new_status: str,  # Ex: "Available", "Unavailable", "Faulted" (OCPP.v16.enums.ChargePointStatus)
        db: Session = Depends(get_db)
):
    """
    Ferramenta para alterar o status operacional de um conector.
    Pode ser usado para marcar como disponível/indisponível ou defeituoso.
    """
    logger.info(
        f"MCP Tool: Request to set status for CP '{charge_point_id}', Connector '{connector_id}' to '{new_status}'")
    device_service = DeviceManagementService(db)

    connector = device_service.update_connector_status(cp_id=charge_point_id, connector_id=connector_id,
                                                       status=new_status)
    if not connector:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Connector {connector_id} on CP {charge_point_id} not found.")

    # TODO: Se 'new_status' for "Unavailable" ou "Operative", você pode querer enviar um ChangeAvailability
    # OCPP Command para o Charge Point para que ele realmente mude seu estado físico.

    return {"message": f"Connector {charge_point_id}-{connector_id} status updated to '{new_status}' in CSMS."}

# Você pode adicionar mais ferramentas conforme a necessidade do seu projeto!