from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ev_charging_system.data.database import get_db
from ev_charging_system.business_logic.device_management_service import DeviceManagementService
from ev_charging_system.data.repositories import ChargePointRepository, TransactionRepository, UserRepository
from ev_charging_system.api.schemas import UserCreate, UserResponse
import logging

router = APIRouter(prefix="/api/users", tags=["Users"])
logger = logging.getLogger(__name__)

def get_device_management_service(db: Session = Depends(get_db)) -> DeviceManagementService:
    cp_repo = ChargePointRepository(db)
    trx_repo = TransactionRepository(db)
    user_repo = UserRepository(db)
    return DeviceManagementService(cp_repo, trx_repo, user_repo)

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="Create a new user")
async def create_user(
        user_data: UserCreate,
        service: DeviceManagementService = Depends(get_device_management_service)
):
    try:
        new_user = service.create_user(
            user_data.user_id,
            user_data.name,
            user_data.email,
            user_data.phone,
            user_data.id_tag,
            user_data.is_active
        )
        return new_user
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/{user_id}", response_model=UserResponse, summary="Get user details")
async def get_user_details(
        user_id: str,
        service: DeviceManagementService = Depends(get_device_management_service)
):
    user = service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
