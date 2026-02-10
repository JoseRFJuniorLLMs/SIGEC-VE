from fastapi import APIRouter, Depends, HTTPException, status, Body
from typing import List
from sqlalchemy.orm import Session
from ev_charging_system.data.database import get_db
from ev_charging_system.business_logic.device_management_service import DeviceManagementService
from ev_charging_system.data.repositories import ChargePointRepository, TransactionRepository, UserRepository
from ev_charging_system.api.schemas import ChargePointCreate, ChargePointResponse, RemoteStartRequest, RemoteStopRequest, ResetRequest, ChangeAvailabilityRequest
from ev_charging_system.core.ocpp_server import connected_charge_points, send_ocpp_command
from ocpp.v201 import enums as ocpp_enums_v201
import logging

router = APIRouter(prefix="/api/charge_points", tags=["Charge Points"])
logger = logging.getLogger(__name__)

def get_device_management_service(db: Session = Depends(get_db)) -> DeviceManagementService:
    cp_repo = ChargePointRepository(db)
    trx_repo = TransactionRepository(db)
    user_repo = UserRepository(db)
    return DeviceManagementService(cp_repo, trx_repo, user_repo)

@router.post("/", response_model=ChargePointResponse, status_code=status.HTTP_201_CREATED, summary="Register a new Charge Point")
async def register_charge_point(
        cp_data: ChargePointCreate,
        service: DeviceManagementService = Depends(get_device_management_service)
):
    try:
        cp = service.register_charge_point(cp_data.charge_point_id, cp_data.vendor_name, cp_data.model)
        return cp
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/", response_model=list, summary="List all Charge Points")
async def list_charge_points(
        service: DeviceManagementService = Depends(get_device_management_service)
):
    charge_points = service.get_all_charge_points()
    # Manual conversion because of nested connectors and relationship complexity
    return [{
        "charge_point_id": cp.charge_point_id,
        "vendor_name": cp.vendor_name,
        "model": cp.model,
        "status": cp.status,
        "created_at": cp.created_at,
        "updated_at": cp.updated_at,
        "last_heartbeat": cp.last_heartbeat,
        "last_boot_notification": cp.last_boot_notification,
        "connectors": [{
            "connector_id": conn.connector_id,
            "status": conn.status,
            "error_code": conn.error_code,
            "current_transaction_id": conn.current_transaction_id,
            "updated_at": conn.updated_at
        } for conn in cp.connectors]
    } for cp in charge_points]

@router.get("/{charge_point_id}", response_model=dict, summary="Get Charge Point details")
async def get_charge_point_details(
        charge_point_id: str,
        service: DeviceManagementService = Depends(get_device_management_service)
):
    cp = service.get_charge_point_by_id(charge_point_id)
    if not cp:
        raise HTTPException(status_code=404, detail="Charge Point not found")

    return {
        "charge_point_id": cp.charge_point_id,
        "vendor_name": cp.vendor_name,
        "model": cp.model,
        "status": cp.status,
        "created_at": cp.created_at,
        "updated_at": cp.updated_at,
        "last_heartbeat": cp.last_heartbeat,
        "last_boot_notification": cp.last_boot_notification,
        "connectors": [{
            "connector_id": conn.connector_id,
            "status": conn.status,
            "error_code": conn.error_code,
            "current_transaction_id": conn.current_transaction_id,
            "updated_at": conn.updated_at
        } for conn in cp.connectors]
    }

# --- Remote Commands ---

@router.post("/{charge_point_id}/remote_start", response_model=dict, summary="Send RemoteStartTransaction to CP")
async def remote_start_transaction(
        charge_point_id: str,
        request: RemoteStartRequest,
        service: DeviceManagementService = Depends(get_device_management_service)
):
    logger.info(f"API: Received request to RemoteStartTransaction for CP {charge_point_id}")
    if charge_point_id not in connected_charge_points:
        raise HTTPException(status_code=404, detail=f"Charge Point {charge_point_id} is not connected via OCPP.")

    id_token_payload = {"idToken": request.id_token, "type": request.id_token_type}

    try:
        response = await send_ocpp_command(
            charge_point_id,
            "RemoteStartTransaction",
            id_token=id_token_payload,
            connector_id=request.connector_id
        )
        logger.info(f"API: RemoteStartTransaction sent to {charge_point_id}. Response: {response}")
        return {"message": "RemoteStartTransaction command sent.", "ocpp_response": response.to_dict()}
    except Exception as e:
        logger.error(f"Error sending RemoteStartTransaction to {charge_point_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to send RemoteStartTransaction: {e}")

@router.post("/{charge_point_id}/remote_stop", response_model=dict, summary="Send RemoteStopTransaction to CP")
async def remote_stop_transaction(
        charge_point_id: str,
        request: RemoteStopRequest,
        service: DeviceManagementService = Depends(get_device_management_service)
):
    logger.info(f"API: Received request to RemoteStopTransaction for CP {charge_point_id}, transaction {request.transaction_id}")
    if charge_point_id not in connected_charge_points:
        raise HTTPException(status_code=404, detail=f"Charge Point {charge_point_id} is not connected via OCPP.")

    try:
        response = await send_ocpp_command(
            charge_point_id,
            "RemoteStopTransaction",
            transaction_id=request.transaction_id
        )
        logger.info(f"API: RemoteStopTransaction sent to {charge_point_id}. Response: {response}")
        return {"message": "RemoteStopTransaction command sent.", "ocpp_response": response.to_dict()}
    except Exception as e:
        logger.error(f"Error sending RemoteStopTransaction to {charge_point_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to send RemoteStopTransaction: {e}")

@router.post("/{charge_point_id}/reset", response_model=dict, summary="Send Reset command to CP")
async def reset_charge_point(
        charge_point_id: str,
        request: ResetRequest,
        service: DeviceManagementService = Depends(get_device_management_service)
):
    logger.info(f"API: Received request to Reset CP {charge_point_id} with type {request.reset_type}")
    if charge_point_id not in connected_charge_points:
        raise HTTPException(status_code=404, detail=f"Charge Point {charge_point_id} is not connected via OCPP.")

    try:
        if request.reset_type.upper() not in [e.value for e in ocpp_enums_v201.ResetEnumType]:
            raise HTTPException(status_code=400,
                                detail=f"Invalid reset_type. Must be one of: {', '.join([e.value for e in ocpp_enums_v201.ResetEnumType])}")

        response = await send_ocpp_command(
            charge_point_id,
            "Reset",
            type=request.reset_type.upper()
        )
        logger.info(f"API: Reset command sent to {charge_point_id}. Response: {response}")
        return {"message": "Reset command sent.", "ocpp_response": response.to_dict()}
    except Exception as e:
        logger.error(f"Error sending Reset to {charge_point_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to send Reset command: {e}")

@router.post("/{charge_point_id}/change_availability", response_model=dict, summary="Send ChangeAvailability command to CP")
async def change_availability_charge_point(
        charge_point_id: str,
        request: ChangeAvailabilityRequest,
        service: DeviceManagementService = Depends(get_device_management_service)
):
    logger.info(f"API: Received request to ChangeAvailability for CP {charge_point_id}, connector {request.connector_id} to {request.operational_status}")
    if charge_point_id not in connected_charge_points:
        raise HTTPException(status_code=404, detail=f"Charge Point {charge_point_id} is not connected via OCPP.")

    try:
        if request.operational_status.upper() not in [e.value for e in ocpp_enums_v201.OperationalStatusEnumType]:
            raise HTTPException(status_code=400,
                                detail=f"Invalid operational_status. Must be one of: {', '.join([e.value for e in ocpp_enums_v201.OperationalStatusEnumType])}")

        response = await send_ocpp_command(
            charge_point_id,
            "ChangeAvailability",
            evse_id=request.connector_id,
            connector_id=request.connector_id,
            operational_status=request.operational_status.upper()
        )
        logger.info(f"API: ChangeAvailability command sent to {charge_point_id}. Response: {response}")
        return {"message": "ChangeAvailability command sent.", "ocpp_response": response.to_dict()}
    except Exception as e:
        logger.error(f"Error sending ChangeAvailability to {charge_point_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to send ChangeAvailability command: {e}")
