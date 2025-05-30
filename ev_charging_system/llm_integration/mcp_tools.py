# ev_charging_system/llm_integration/mcp_tools.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
import logging

# Importa o serviço de gerenciamento de dispositivos para a lógica de negócio
from ev_charging_system.business_logic.device_management_service import DeviceManagementService
# Importa a função para obter a sessão do banco de dados
from ev_charging_system.data.database import get_db
# NOVO IMPORT: Importa a função send_ocpp_command_to_cp do novo módulo central
from ev_charging_system.core.ocpp_central_manager import send_ocpp_command_to_cp

# Importe o status correto para RemoteStartStopStatus
from ocpp.v16.enums import RemoteStartStopStatus

logger = logging.getLogger(__name__)

router = APIRouter()


# (Mantenha todas as suas funções existentes: reset_charge_point, update_charge_point_configuration,
# start_ocpp_transaction, stop_ocpp_transaction, set_connector_status)

@router.post("/start_ocpp_transaction")
async def start_ocpp_transaction(
        charge_point_id: str,
        connector_id: int,
        id_tag: str,
        db: Session = Depends(get_db)
):
    logger.info(
        f"MCP Tool: Request to start transaction on CP '{charge_point_id}', conn '{connector_id}' for ID Tag '{id_tag}'")
    device_service = DeviceManagementService(db)

    connector = device_service.charge_point_repo.get_connector_by_id(connector_id, charge_point_id)
    if not connector:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Connector {connector_id} on CP {charge_point_id} not found.")

    if connector.status != "Available":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail=f"Connector {connector_id} on CP {charge_point_id} is not available (status: {connector.status}).")

    # A função send_ocpp_command_to_cp agora acessa o dicionário de CPs conectados globalmente do ocpp_central_manager
    response = await send_ocpp_command_to_cp(
        charge_point_id,
        "RemoteStartTransaction",
        {"connectorId": connector_id, "idTag": id_tag}
    )

    if response and response.status == RemoteStartStopStatus.accepted:
        return {
            "message": f"RemoteStartTransaction initiated for CP '{charge_point_id}', Connector '{connector_id}', ID Tag '{id_tag}'. Status: {response.status}. CP will send StartTransaction.req shortly."}
    else:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Failed to initiate RemoteStartTransaction for CP '{charge_point_id}'. Response: {response}")


@router.post("/plug_and_charge_connect")
async def plug_and_charge_connect(
        charge_point_id: str,
        connector_id: int,
        vehicle_contract_id: str,
        db: Session = Depends(get_db)
):
    logger.info(
        f"MCP Tool: Plug & Charge event for CP '{charge_point_id}', Connector '{connector_id}', Vehicle Contract ID: '{vehicle_contract_id}'")

    device_service = DeviceManagementService(db)

    is_authorized = True

    if not is_authorized:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail=f"Vehicle Contract ID '{vehicle_contract_id}' not authorized for Plug & Charge.")

    connector = device_service.charge_point_repo.get_connector_by_id(connector_id, charge_point_id)
    if not connector:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Connector {connector_id} on CP {charge_point_id} not found.")

    if connector.status != "Available":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail=f"Connector {connector_id} on CP {charge_point_id} is not available (status: {connector.status}).")

    # A função send_ocpp_command_to_cp agora acessa o dicionário de CPs conectados globalmente do ocpp_central_manager
    response = await send_ocpp_command_to_cp(
        charge_point_id,
        "RemoteStartTransaction",
        {"connectorId": connector_id, "idTag": vehicle_contract_id}
    )

    if response and response.status == RemoteStartStopStatus.accepted:
        return {
            "message": f"Plug & Charge session conceptually started for CP '{charge_point_id}', Connector '{connector_id}', Vehicle ID '{vehicle_contract_id}'. Status: {response.status}. CP will send StartTransaction.req shortly."
        }
    else:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Failed to initiate RemoteStartTransaction for Plug & Charge. Response: {response}")