# ev_charging_system/api/rest_api.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
import logging
from datetime import datetime

# Importa os serviços e modelos necessários
from ev_charging_system.business_logic.device_management_service import DeviceManagementService
from ev_charging_system.business_logic.transaction_service import TransactionService
from ev_charging_system.business_logic.user_service import UserService
from ev_charging_system.data.database import get_db
from ev_charging_system.models.charge_point import ChargePoint, ChargePointConnector
from ev_charging_system.models.user import User as DBUser
from ev_charging_system.models.transaction import Transaction as DBTransaction
from ev_charging_system.core.ocpp_server import send_ocpp_command_to_cp
from ocpp.v16.enums import RemoteStartStopStatus, ResetType, ChargePointStatus  # Adicionado ResetType

# Schemas Pydantic para validação de entrada/saída da API
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter()


# --- Schemas Pydantic ---
class ChargePointConnectorBase(BaseModel):
    id: int
    status: str
    type: str
    power_kw: float
    current_transaction_id: Optional[str] = None

    class Config:
        from_attributes = True  # updated from orm_mode = True


class ChargePointBase(BaseModel):
    id: str
    vendor_name: str
    model: str
    location: str
    firmware_version: str
    status: str
    last_boot_time: Optional[datetime] = None
    last_heartbeat_time: Optional[datetime] = None
    configuration: Optional[Dict] = {}  # Pode ser uma string JSON ou Dict
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    connectors: List[ChargePointConnectorBase] = []  # Inclui os conectores

    class Config:
        from_attributes = True  # updated from orm_mode = True


class UserCreate(BaseModel):
    id: str  # Pode ser email
    auth_tag: str
    name: str
    email: str
    balance: float = 0.0
    preferences: Optional[Dict] = {}


class UserPublic(BaseModel):
    id: str
    name: str
    email: str
    balance: float
    preferences: Optional[Dict] = {}

    class Config:
        from_attributes = True  # updated from orm_mode = True


class TransactionCreate(BaseModel):
    charge_point_id: str
    connector_id: int
    user_id: str
    start_meter_value: float


class TransactionPublic(BaseModel):
    id: str
    charge_point_id: str
    connector_id: int
    user_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    start_meter_value: float
    end_meter_value: Optional[float] = None
    total_energy_kwh: Optional[float] = None
    status: str
    tariff_applied: Optional[str] = None
    cost: Optional[float] = None
    stop_reason: Optional[str] = None

    class Config:
        from_attributes = True  # updated from orm_mode = True


class StartTransactionRequest(BaseModel):
    charge_point_id: str
    connector_id: int
    id_tag: str


class StopTransactionRequest(BaseModel):
    charge_point_id: str
    transaction_id: str  # OCPP TransactionId (não o do DB)
    meter_stop: float
    reason: Optional[str] = None


class RemoteCommandResponse(BaseModel):
    status: str
    message: Optional[str] = None


# --- Health Check Endpoint (NOVO!) ---
@router.get("/health")
async def health_check():
    """Retorna o status da API para verificação de saúde."""
    logger.info("API Health Check requested.")
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat() + "Z"}


# --- Endpoints para Gerenciamento de Charge Points ---

@router.get("/charge_points", response_model=List[ChargePointBase])
async def list_charge_points(db: Session = Depends(get_db)):
    """Lista todos os Charge Points registrados."""
    device_service = DeviceManagementService(db)
    charge_points = device_service.list_all_charge_points()
    return charge_points


@router.get("/charge_points/{cp_id}", response_model=ChargePointBase)
async def get_charge_point_details(cp_id: str, db: Session = Depends(get_db)):
    """Obtém detalhes de um Charge Point específico."""
    device_service = DeviceManagementService(db)
    cp = device_service.get_charge_point_details(cp_id)
    if not cp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Charge Point not found")
    return cp


@router.post("/charge_points/{cp_id}/reset", response_model=RemoteCommandResponse)
async def reset_charge_point(cp_id: str, db: Session = Depends(get_db)):
    """Envia um comando de reset para um Charge Point."""
    logger.info(f"API: Recebida solicitação de reset para CP '{cp_id}'")

    # Verifica se o CP existe e está online (opcional, mas boa prática)
    device_service = DeviceManagementService(db)
    cp = device_service.get_charge_point_details(cp_id)
    if not cp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Charge Point '{cp_id}' not found.")

    # OCPPCp.reset() na biblioteca python-ocpp espera um tipo de reset (Soft/Hard)
    # Vamos usar um reset Soft por padrão
    success = await send_ocpp_command_to_cp(cp_id, "Reset", {"type": ResetType.soft})

    if success:
        return {"status": "success", "message": f"Reset command sent to Charge Point '{cp_id}'."}
    else:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Failed to send reset command to Charge Point '{cp_id}'. It might be offline.")


# --- Endpoints para Gerenciamento de Usuários ---

@router.post("/users", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
async def create_user_api(user: UserCreate, db: Session = Depends(get_db)):
    """Cria um novo usuário."""
    user_service = UserService(db)
    # Verificar se o usuário ou auth_tag já existe antes de criar
    existing_user_by_id = user_service.get_user_by_id(user.id)
    existing_user_by_auth_tag = user_service.get_user_by_auth_tag(user.auth_tag)
    if existing_user_by_id or existing_user_by_auth_tag:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User with this ID or Auth Tag already exists")

    db_user = DBUser(
        id=user.id,
        auth_tag=user.auth_tag,
        name=user.name,
        email=user.email,
        balance=user.balance,
        preferences=user.preferences
    )
    created_user = user_service.create_user(db_user)
    return created_user


@router.get("/users/{user_id}", response_model=UserPublic)
async def get_user_details(user_id: str, db: Session = Depends(get_db)):
    """Obtém detalhes de um usuário específico."""
    user_service = UserService(db)
    user = user_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


# --- Endpoints para Gerenciamento de Transações (via API do CSMS) ---

@router.post("/transactions/start", response_model=Dict[str, str])
async def start_charging_transaction(req: StartTransactionRequest, db: Session = Depends(get_db)):
    """
    Inicia uma transação de carregamento.
    Isso envolve registrar a transação no CSMS e enviar um RemoteStartTransaction para o CP.
    """
    logger.info(
        f"API: Recebida solicitação para iniciar transação para CP '{req.charge_point_id}', Conector {req.connector_id}, ID Tag: {req.id_tag}")

    device_service = DeviceManagementService(db)
    user_service = UserService(db)
    transaction_service = TransactionService(db)

    # 1. Verificar se o Charge Point e o Conector existem e estão disponíveis
    cp = device_service.get_charge_point_details(req.charge_point_id)
    if not cp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Charge Point '{req.charge_point_id}' not found.")

    connector = next((c for c in cp.connectors if c.id == req.connector_id), None)
    if not connector:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Connector {req.connector_id} not found on CP {req.charge_point_id}.")

    # OCPP 1.6: RemoteStartTransaction deve ser enviado para o CP
    # O Charge Point simulado irá responder com StartTransaction.conf
    # A lógica de iniciar a transação real no DB será no handler StartTransaction do CSMS (ocpp_handlers.py)

    response_status = await send_ocpp_command_to_cp(
        req.charge_point_id,
        "RemoteStartTransaction",
        {"connectorId": req.connector_id, "idTag": req.id_tag}
    )

    if response_status == RemoteStartStopStatus.accepted:
        # A resposta do comando remoto foi aceita pelo CP
        # A transação será criada no DB quando o CP enviar StartTransaction.req
        return {"status": "pending_cp_response",
                "message": f"RemoteStartTransaction sent to CP '{req.charge_point_id}'. Awaiting StartTransaction.conf from CP."}
    else:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail=f"Charge Point '{req.charge_point_id}' refused RemoteStartTransaction: {response_status}")


@router.post("/transactions/stop", response_model=Dict[str, str])
async def stop_charging_transaction(req: StopTransactionRequest, db: Session = Depends(get_db)):
    """
    Para uma transação de carregamento em andamento.
    Isso envolve enviar um RemoteStopTransaction para o CP.
    """
    logger.info(
        f"API: Recebida solicitação para parar transação '{req.transaction_id}' para CP '{req.charge_point_id}'")

    device_service = DeviceManagementService(db)
    transaction_service = TransactionService(db)

    # 1. Verificar se o Charge Point existe
    cp = device_service.get_charge_point_details(req.charge_point_id)
    if not cp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Charge Point '{req.charge_point_id}' not found.")

    # 2. Encontrar a transação no DB pelo transaction_id (OCPP ID)
    db_transaction = transaction_service.get_transaction_by_ocpp_id(req.transaction_id)
    if not db_transaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Transaction '{req.transaction_id}' not found in CSMS database.")

    # 3. Enviar RemoteStopTransaction para o CP
    response_status = await send_ocpp_command_to_cp(
        req.charge_point_id,
        "RemoteStopTransaction",
        {"transactionId": int(req.transaction_id)}  # O OCPP espera um int para transactionId
    )

    if response_status == RemoteStartStopStatus.accepted:
        # A resposta do comando remoto foi aceita pelo CP
        # A transação será finalizada no DB quando o CP enviar StopTransaction.req
        return {"status": "pending_cp_response",
                "message": f"RemoteStopTransaction sent to CP '{req.charge_point_id}'. Awaiting StopTransaction.conf from CP."}
    else:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail=f"Charge Point '{req.charge_point_id}' refused RemoteStopTransaction: {response_status}")


@router.get("/transactions/{transaction_id}", response_model=TransactionPublic)
async def get_transaction_details(transaction_id: str, db: Session = Depends(get_db)):
    """Obtém detalhes de uma transação específica."""
    transaction_service = TransactionService(db)
    # Assumimos que o transaction_id passado aqui é o ID interno do DB (UUID ou string)
    # Se for o OCPP transactionId (que é um int), você precisará ajustar o serviço
    transaction = transaction_service.get_transaction_by_ocpp_id(
        transaction_id)  # Usando o novo método para o ID do OCPP
    if not transaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    return transaction


@router.get("/charge_points/{cp_id}/status_summary", response_model=Dict[str, int])
async def get_charge_point_status_summary(db: Session = Depends(get_db)):
    """Retorna um resumo da contagem de CPs por status."""
    device_service = DeviceManagementService(db)
    summary = device_service.get_charge_point_status_summary()
    return summary