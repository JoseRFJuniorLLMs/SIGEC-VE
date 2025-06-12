# ev_charging_system/main.py

from fastapi import FastAPI, Depends, HTTPException, status, Body
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
import uvicorn
import asyncio
import os
import logging
import contextlib

from typing import Dict, Optional

# Import models and database
from ev_charging_system.data.models import Base, ChargePoint, Connector, Transaction, User
from ev_charging_system.data.database import engine, get_db

# Import repositories and services
from ev_charging_system.data.repositories import ChargePointRepository, TransactionRepository, UserRepository
from ev_charging_system.business_logic.device_management_service import DeviceManagementService

# Import OCPP server components
from ev_charging_system.core.ocpp_server import ocpp_server, connected_charge_points, send_ocpp_command
# Importar os enums do OCPP 2.0.1 para usar nas respostas da API
from ocpp.v201 import enums as ocpp_enums_v201

# Importar Pydantic para definir modelos de requisição
from pydantic import BaseModel

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# --- Definição dos modelos Pydantic para eventos EV ---
class EVPlugIn(BaseModel):
    ev_id: str
    charge_point_id: str
    connector_id: int

class EVUnPlug(BaseModel):
    ev_id: str
    charge_point_id: str
    connector_id: int
    transaction_id: str

# --- Lifespan Context Manager ---
@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events.
    Sets up database and starts OCPP server on startup,
    and gracefully shuts down OCPP server on shutdown.
    """
    logger.info("Starting SIGEC-VE application...")

    try:
        # --- Database Setup ---
        logger.info("Setting up database...")
        Base.metadata.create_all(bind=engine)

        # --- Start OCPP Server ---
        logger.info("Starting OCPP server...")
        asyncio.create_task(ocpp_server.start())
        logger.info("OCPP server started in background.")

        yield
    finally:
        logger.info("Shutting down SIGEC-VE application...")
        # --- Shutdown OCPP Server ---
        logger.info("Stopping OCPP server...")
        await ocpp_server.stop()
        logger.info("OCPP server stopped.")
        engine.dispose()
        logger.info("Database engine disposed.")


app = FastAPI(
    title="SIGEC-VE CSMS API",
    description="Central System Management System (CSMS) for Electric Vehicle Charging, implementing OCPP 2.0.1.",
    version="1.0.0",
    lifespan=lifespan
)


# Dependency to get DeviceManagementService
def get_device_management_service(db: Session = Depends(get_db)) -> DeviceManagementService:
    cp_repo = ChargePointRepository(db)
    trx_repo = TransactionRepository(db)
    user_repo = UserRepository(db)
    return DeviceManagementService(cp_repo, trx_repo, user_repo)


@app.get("/", response_class=HTMLResponse, summary="Root endpoint")
async def read_root():
    """Root endpoint for the API."""
    return """
    <html>
        <head>
            <title>SIGEC-VE CSMS API</title>
        </head>
        <body>
            <h1>Welcome to the SIGEC-VE CSMS API</h1>
            <p>Go to <a href="/docs">/docs</a> for the API documentation.</p>
        </body>
    </html>
    """

# --- Charge Point Management ---
@app.post("/api/charge_points", response_model=dict, status_code=status.HTTP_201_CREATED,
          summary="Register a new Charge Point")
async def register_charge_point(
        charge_point_id: str = Body(..., description="Unique ID of the Charge Point"),
        vendor_name: str = Body("Unknown", description="Vendor name of the Charge Point"),
        model: str = Body("Unknown", description="Model of the Charge Point"),
        service: DeviceManagementService = Depends(get_device_management_service)
):
    """
    Registers a new Charge Point in the system.
    """
    try:
        cp = service.register_charge_point(charge_point_id, vendor_name, model)
        return {
            "charge_point_id": cp.charge_point_id,
            "vendor_name": cp.vendor_name,
            "model": cp.model,
            "status": cp.status,
            "created_at": cp.created_at.isoformat()
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@app.get("/api/charge_points", response_model=list, summary="List all Charge Points")
async def list_charge_points(
        service: DeviceManagementService = Depends(get_device_management_service)
):
    """
    Retrieves a list of all registered Charge Points.
    """
    charge_points = service.get_all_charge_points()
    return [{
        "charge_point_id": cp.charge_point_id,
        "vendor_name": cp.vendor_name,
        "model": cp.model,
        "status": cp.status,
        "created_at": cp.created_at.isoformat() if cp.created_at else None,
        "updated_at": cp.updated_at.isoformat() if cp.updated_at else None,
        "last_heartbeat": cp.last_heartbeat.isoformat() if cp.last_heartbeat else None,
        "last_boot_notification": cp.last_boot_notification.isoformat() if cp.last_boot_notification else None,
        "connectors": [{
            "connector_id": conn.connector_id,
            "status": conn.status,
            "error_code": conn.error_code,
            "current_transaction_id": conn.current_transaction_id,
            "updated_at": conn.updated_at.isoformat() if conn.updated_at else None
        } for conn in cp.connectors]
    } for cp in charge_points]


@app.get("/api/charge_points/{charge_point_id}", response_model=dict, summary="Get Charge Point details")
async def get_charge_point_details(
        charge_point_id: str,
        service: DeviceManagementService = Depends(get_device_management_service)
):
    """
    Retrieves details of a specific Charge Point by its ID.
    """
    cp = service.get_charge_point_by_id(charge_point_id)
    if not cp:
        raise HTTPException(status_code=404, detail="Charge Point not found")

    return {
        "charge_point_id": cp.charge_point_id,
        "vendor_name": cp.vendor_name,
        "model": cp.model,
        "status": cp.status,
        "created_at": cp.created_at.isoformat() if cp.created_at else None,
        "updated_at": cp.updated_at.isoformat() if cp.updated_at else None,
        "last_heartbeat": cp.last_heartbeat.isoformat() if cp.last_heartbeat else None,
        "last_boot_notification": cp.last_boot_notification.isoformat() if cp.last_boot_notification else None,
        "connectors": [{
            "connector_id": conn.connector_id,
            "status": conn.status,
            "error_code": conn.error_code,
            "current_transaction_id": conn.current_transaction_id,
            "updated_at": conn.updated_at.isoformat() if conn.updated_at else None
        } for conn in cp.connectors]
    }

# --- Transaction Management ---
@app.get("/api/transactions", response_model=list, summary="List all transactions")
async def list_transactions(
        service: DeviceManagementService = Depends(get_device_management_service)
):
    """
    Retrieves a list of all transactions.
    """
    transactions = service.get_all_transactions()
    return [{
        "transaction_id": trx.transaction_id,
        "charge_point_id": trx.charge_point_id,
        "connector_id": trx.connector_id,
        "id_tag": trx.id_tag,
        "meter_start": trx.meter_start,
        "meter_stop": trx.meter_stop,
        "start_time": trx.start_time.isoformat() if trx.start_time else None,
        "stop_time": trx.stop_time.isoformat() if trx.stop_time else None,
        "status": trx.status,
        "kwh_consumed": trx.kwh_consumed,
        "price": trx.price,
        "session_id": trx.session_id,
        "reason": trx.reason,
        "created_at": trx.created_at.isoformat() if trx.created_at else None,
        "updated_at": trx.updated_at.isoformat() if trx.updated_at else None,
    } for trx in transactions]


@app.get("/api/transactions/{transaction_id}", response_model=dict, summary="Get transaction details")
async def get_transaction_details(
        transaction_id: str,
        service: DeviceManagementService = Depends(get_device_management_service)
):
    """
    Retrieves details of a specific transaction by its ID.
    """
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
        "start_time": trx.start_time.isoformat() if trx.start_time else None,
        "stop_time": trx.stop_time.isoformat() if trx.stop_time else None,
        "status": trx.status,
        "kwh_consumed": trx.kwh_consumed,
        "price": trx.price,
        "session_id": trx.session_id,
        "reason": trx.reason,
        "created_at": trx.created_at.isoformat() if trx.created_at else None,
        "updated_at": trx.updated_at.isoformat() if trx.updated_at else None,
    }


# --- Remote Commands to Charge Points ---
@app.post("/api/charge_points/{charge_point_id}/remote_start", response_model=dict,
          summary="Send RemoteStartTransaction to CP")
async def remote_start_transaction(
        charge_point_id: str,
        connector_id: int = Body(...),
        id_token: str = Body(...),
        id_token_type: str = Body("ISO15118Certificate"),
        service: DeviceManagementService = Depends(get_device_management_service)
):
    """
    Sends a RemoteStartTransaction command to a specific Charge Point.
    """
    logger.info(f"API: Received request to RemoteStartTransaction for CP {charge_point_id}")
    if charge_point_id not in connected_charge_points:
        raise HTTPException(status_code=404, detail=f"Charge Point {charge_point_id} is not connected via OCPP.")

    id_token_payload = {"idToken": id_token, "type": id_token_type}

    try:
        response = await send_ocpp_command(
            charge_point_id,
            "RemoteStartTransaction",
            id_token=id_token_payload,
            connector_id=connector_id
        )
        logger.info(f"API: RemoteStartTransaction sent to {charge_point_id}. Response: {response}")
        return {"message": "RemoteStartTransaction command sent.", "ocpp_response": response.to_dict()}
    except Exception as e:
        logger.error(f"Error sending RemoteStartTransaction to {charge_point_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to send RemoteStartTransaction: {e}")


@app.post("/api/charge_points/{charge_point_id}/remote_stop", response_model=dict,
          summary="Send RemoteStopTransaction to CP")
async def remote_stop_transaction(
        charge_point_id: str,
        transaction_id: str = Body(...),
        service: DeviceManagementService = Depends(get_device_management_service)
):
    """
    Sends a RemoteStopTransaction command to a specific Charge Point.
    """
    logger.info(
        f"API: Received request to RemoteStopTransaction for CP {charge_point_id}, transaction {transaction_id}")
    if charge_point_id not in connected_charge_points:
        raise HTTPException(status_code=404, detail=f"Charge Point {charge_point_id} is not connected via OCPP.")

    try:
        response = await send_ocpp_command(
            charge_point_id,
            "RemoteStopTransaction",
            transaction_id=transaction_id
        )
        logger.info(f"API: RemoteStopTransaction sent to {charge_point_id}. Response: {response}")
        return {"message": "RemoteStopTransaction command sent.", "ocpp_response": response.to_dict()}
    except Exception as e:
        logger.error(f"Error sending RemoteStopTransaction to {charge_point_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to send RemoteStopTransaction: {e}")


@app.post("/api/charge_points/{charge_point_id}/reset", response_model=dict, summary="Send Reset command to CP")
async def reset_charge_point(
        charge_point_id: str,
        reset_type: str = Body(..., description="Type of reset (Hard or Soft)"),
        service: DeviceManagementService = Depends(get_device_management_service)
):
    """
    Sends a Reset command to a specific Charge Point.
    """
    logger.info(f"API: Received request to Reset CP {charge_point_id} with type {reset_type}")
    if charge_point_id not in connected_charge_points:
        raise HTTPException(status_code=404, detail=f"Charge Point {charge_point_id} is not connected via OCPP.")

    try:
        if reset_type.upper() not in [e.value for e in ocpp_enums_v201.ResetEnumType]:
            raise HTTPException(status_code=400,
                                detail=f"Invalid reset_type. Must be one of: {', '.join([e.value for e in ocpp_enums_v201.ResetEnumType])}")

        response = await send_ocpp_command(
            charge_point_id,
            "Reset",
            type=reset_type.upper()
        )
        logger.info(f"API: Reset command sent to {charge_point_id}. Response: {response}")
        return {"message": "Reset command sent.", "ocpp_response": response.to_dict()}
    except Exception as e:
        logger.error(f"Error sending Reset to {charge_point_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to send Reset command: {e}")


@app.post("/api/charge_points/{charge_point_id}/change_availability", response_model=dict,
          summary="Send ChangeAvailability command to CP")
async def change_availability_charge_point(
        charge_point_id: str,
        connector_id: int = Body(...),
        operational_status: str = Body(..., description="Availability status (Operative or Inoperative)"),
        service: DeviceManagementService = Depends(get_device_management_service)
):
    """
    Sends a ChangeAvailability command to a specific Charge Point.
    """
    logger.info(
        f"API: Received request to ChangeAvailability for CP {charge_point_id}, connector {connector_id} to {operational_status}")
    if charge_point_id not in connected_charge_points:
        raise HTTPException(status_code=404, detail=f"Charge Point {charge_point_id} is not connected via OCPP.")

    try:
        if operational_status.upper() not in [e.value for e in ocpp_enums_v201.OperationalStatusEnumType]:
            raise HTTPException(status_code=400,
                                detail=f"Invalid operational_status. Must be one of: {', '.join([e.value for e in ocpp_enums_v201.OperationalStatusEnumType])}")

        response = await send_ocpp_command(
            charge_point_id,
            "ChangeAvailability",
            evse_id=connector_id,
            connector_id=connector_id,
            operational_status=operational_status.upper()
        )
        logger.info(f"API: ChangeAvailability command sent to {charge_point_id}. Response: {response}")
        return {"message": "ChangeAvailability command sent.", "ocpp_response": response.to_dict()}
    except Exception as e:
        logger.error(f"Error sending ChangeAvailability to {charge_point_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to send ChangeAvailability command: {e}")


# --- NEW EV Event Endpoints ---
@app.post("/api/ev_events/plug_in", summary="Simulate EV Plug-in event and initiate charging")
async def ev_plug_in_event(
        event: EVPlugIn,
        csms_service: DeviceManagementService = Depends(get_device_management_service)
):
    logger.info(f"API: EV {event.ev_id} plugged into CP {event.charge_point_id}, connector {event.connector_id}")

    if event.charge_point_id not in connected_charge_points:
        raise HTTPException(status_code=404, detail=f"Charge Point {event.charge_point_id} is not connected via OCPP.")

    id_token_payload = {
        "idToken": event.ev_id,
        "type": "ISO15118Certificate"
    }

    try:
        ocpp_response = await send_ocpp_command(
            event.charge_point_id,
            "RemoteStartTransaction",
            id_token=id_token_payload,
            connector_id=event.connector_id
        )
        logger.info(
            f"OCPP Command (RemoteStartTransaction) sent to {event.charge_point_id}. Response: {ocpp_response.to_dict()}")

        if ocpp_response.status == ocpp_enums_v201.RequestStartStopStatus.Accepted:
            return {"message": "EV Plug-in event received and RemoteStartTransaction sent to CP.",
                    "ocpp_response": ocpp_response.to_dict(),
                    "transactionId": f"TEMP_{event.charge_point_id}_{event.connector_id}_{event.ev_id}"
                    }
        else:
            raise HTTPException(status_code=400,
                                detail=f"RemoteStartTransaction rejected by CP: {ocpp_response.status}")

    except Exception as e:
        logger.error(f"Failed to send RemoteStartTransaction to {event.charge_point_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to initiate charge: {e}")


@app.post("/api/ev_events/unplug", summary="Simulate EV Unplug event and stop charging")
async def ev_unplug_event(
        event: EVUnPlug,
        csms_service: DeviceManagementService = Depends(get_device_management_service)
):
    logger.info(
        f"API: EV {event.ev_id} unplugged from CP {event.charge_point_id}, connector {event.connector_id}, transaction {event.transaction_id}")

    if event.charge_point_id not in connected_charge_points:
        raise HTTPException(status_code=404, detail=f"Charge Point {event.charge_point_id} is not connected via OCPP.")

    try:
        ocpp_response = await send_ocpp_command(
            event.charge_point_id,
            "RemoteStopTransaction",
            transaction_id=event.transaction_id
        )
        logger.info(
            f"OCPP Command (RemoteStopTransaction) sent to {event.charge_point_id}. Response: {ocpp_response.to_dict()}")

        if ocpp_response.status == ocpp_enums_v201.RequestStartStopStatus.Accepted:
            return {"message": "EV Unplug event received and RemoteStopTransaction sent to CP.",
                    "ocpp_response": ocpp_response.to_dict()}
        else:
            raise HTTPException(status_code=400, detail=f"RemoteStopTransaction rejected by CP: {ocpp_response.status}")

    except Exception as e:
        logger.error(f"Failed to send RemoteStopTransaction to {event.charge_point_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to stop charge: {e}")


# --- User Management ---
@app.post("/api/users", response_model=dict, status_code=status.HTTP_201_CREATED, summary="Create a new user")
async def create_user(
        user_id: str = Body(...),
        name: str = Body(...),
        email: str = Body(...),
        phone: Optional[str] = Body(None),
        id_tag: Optional[str] = Body(None),
        is_active: bool = Body(True),
        service: DeviceManagementService = Depends(get_device_management_service)
):
    """Create a new user with provided details."""
    try:
        new_user = service.create_user(user_id, name, email, phone, id_tag, is_active)
        return {
            "user_id": new_user.user_id,
            "name": new_user.name,
            "email": new_user.email,
            "phone": new_user.phone,
            "id_tag": new_user.id_tag,
            "is_active": new_user.is_active
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@app.get("/api/users/{user_id}", response_model=dict, summary="Get user details")
async def get_user_details(
        user_id: str,
        service: DeviceManagementService = Depends(get_device_management_service)
):
    """Get details of a specific user by ID."""
    user = service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "id": user.id,
        "user_id": user.user_id,
        "name": user.name,
        "email": user.email,
        "phone": user.phone,
        "id_tag": user.id_tag,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
    }


# --- Health Check ---
@app.get("/api/health", summary="Health check")
async def health_check():
    """Application health check endpoint."""
    try:
        db = next(get_db())
        db.execute(text("SELECT 1"))
        db.close()

        is_ocpp_server_running = ocpp_server._server is not None and ocpp_server._server.sockets

        return {
            "status": "ok",
            "database_status": "connected",
            "ocpp_server_status": "running" if is_ocpp_server_running else "not running",
            "connected_charge_points": len(connected_charge_points)
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {e}")

# --- Execução da Aplicação ---
if __name__ == "__main__":
    logger.info("INFO: Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)")
    uvicorn.run(app, host="0.0.0.0", port=8000)