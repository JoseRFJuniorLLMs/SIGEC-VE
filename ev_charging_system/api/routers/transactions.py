from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ev_charging_system.data.database import get_db
from ev_charging_system.business_logic.device_management_service import DeviceManagementService
from ev_charging_system.data.repositories import ChargePointRepository, TransactionRepository, UserRepository
import logging

router = APIRouter(prefix="/api/transactions", tags=["Transactions"])
logger = logging.getLogger(__name__)

def get_device_management_service(db: Session = Depends(get_db)) -> DeviceManagementService:
    cp_repo = ChargePointRepository(db)
    trx_repo = TransactionRepository(db)
    user_repo = UserRepository(db)
    return DeviceManagementService(cp_repo, trx_repo, user_repo)

@router.get("/", response_model=list, summary="List all transactions")
async def list_transactions(
        service: DeviceManagementService = Depends(get_device_management_service)
):
    transactions = service.get_all_transactions()
    return [{
        "transaction_id": trx.transaction_id,
        "charge_point_id": trx.charge_point_id,
        "connector_id": trx.connector_id,
        "id_tag": trx.id_tag,
        "meter_start": trx.meter_start,
        "meter_stop": trx.meter_stop,
        "start_time": trx.start_time,
        "stop_time": trx.stop_time,
        "status": trx.status,
        "kwh_consumed": trx.kwh_consumed,
        "price": trx.price,
        "session_id": trx.session_id,
        "reason": trx.reason,
        "created_at": trx.created_at,
        "updated_at": trx.updated_at,
    } for trx in transactions]

@router.get("/{transaction_id}", response_model=dict, summary="Get transaction details")
async def get_transaction_details(
        transaction_id: str,
        service: DeviceManagementService = Depends(get_device_management_service)
):
    trx = service.get_transaction_by_id(transaction_id)
    if not trx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    return {
        "transaction_id": trx.transaction_id,
        "charge_point_id": trx.charge_point_id,
        "connector_id": trx.connector_id,
        "id_tag": trx.id_tag,
        "meter_start": trx.meter_start,
        "meter_stop": trx.meter_stop,
        "start_time": trx.start_time,
        "stop_time": trx.stop_time,
        "status": trx.status,
        "kwh_consumed": trx.kwh_consumed,
        "price": trx.price,
        "session_id": trx.session_id,
        "reason": trx.reason,
        "created_at": trx.created_at,
        "updated_at": trx.updated_at,
    }
