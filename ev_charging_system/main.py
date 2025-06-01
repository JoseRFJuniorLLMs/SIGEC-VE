# ev_charging_system/main.py

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
import uvicorn
import asyncio
import os
import logging
import contextlib # Importado para usar asynccontextmanager

# Import models and database
from ev_charging_system.data.models import Base, ChargePoint, Connector, Transaction, User
from ev_charging_system.data.database import engine, get_db

# Import repositories and services
from ev_charging_system.data.repositories import ChargePointRepository, TransactionRepository, UserRepository
from ev_charging_system.business_logic.device_management_service import DeviceManagementService

# Import OCPP server components
from ev_charging_system.core.ocpp_server import ocpp_server, connected_charge_points, send_ocpp_command

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

        # Test database connection
        with next(get_db()) as db:
            db.execute(text("SELECT 1"))
        logger.info("Database connection established successfully")

    except Exception as e:
        logger.critical(f"Database initialization failed: {e}")
        # Levantar a exceção para impedir que o aplicativo inicie em caso de falha no DB
        raise

    # --- Start OCPP Server ---
    logger.info("Starting OCPP server...")

    try:
        ocpp_port = int(os.getenv("OCPP_PORT", 9000))
        ocpp_host = os.getenv("OCPP_HOST", "0.0.0.0")

        # Configure the global OCPP server
        global ocpp_server
        ocpp_server.host = ocpp_host
        ocpp_server.port = ocpp_port

        # Start OCPP server as background task
        # asyncio.create_task é mais adequado para tarefas de background que não bloqueiam o startup
        asyncio.create_task(ocpp_server.start())

        logger.info(f"OCPP server started on ws://{ocpp_host}:{ocpp_port}")

    except Exception as e:
        logger.error(f"Failed to start OCPP server: {e}")
        # Levantar a exceção para impedir que o aplicativo inicie em caso de falha no servidor OCPP
        raise

    yield # O aplicativo começa a servir requisições após o 'yield'

    # --- Application Shutdown ---
    logger.info("Shutting down SIGEC-VE application...")

    try:
        # Stop OCPP server gracefully
        await ocpp_server.stop()
        logger.info("OCPP server shutdown complete")

    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# Initialize FastAPI app with lifespan
app = FastAPI(
    title="SIGEC-VE - Sistema Integrado de Gerenciamento de Estações de Carregamento para Veículos Elétricos",
    description="API para gerenciar estações de carregamento de veículos elétricos compatíveis com OCPP 2.0",
    version="1.0.0",
    lifespan=lifespan, # Atribui o gerenciador de lifespan
)


# --- Dependency Injection ---
def get_charge_point_repo(db: Session = Depends(get_db)) -> ChargePointRepository:
    """Returns a ChargePointRepository instance."""
    return ChargePointRepository(db)


def get_transaction_repo(db: Session = Depends(get_db)) -> TransactionRepository:
    """Returns a TransactionRepository instance."""
    return TransactionRepository(db)


def get_user_repo(db: Session = Depends(get_db)) -> UserRepository:
    """Returns a UserRepository instance."""
    return UserRepository(db)


def get_device_management_service(
        charge_point_repo: ChargePointRepository = Depends(get_charge_point_repo),
        transaction_repo: TransactionRepository = Depends(get_transaction_repo),
        user_repo: UserRepository = Depends(get_user_repo)
) -> DeviceManagementService:
    """Returns a DeviceManagementService instance with repositories."""
    return DeviceManagementService(charge_point_repo, transaction_repo, user_repo)


# --- API Routes ---

@app.get("/", response_class=HTMLResponse, summary="Home Page")
async def read_root():
    """Returns a simple HTML home page."""
    connected_count = len(connected_charge_points)

    return f"""
    <html>
        <head>
            <title>SIGEC-VE API</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 2em; background-color: #f5f5f5; }}
                .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 2em; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 0.5em; }}
                .status {{ background: #e8f5e8; padding: 1em; border-radius: 4px; margin: 1em 0; }}
                .stats {{ display: flex; gap: 2em; margin: 1em 0; }}
                .stat-box {{ background: #3498db; color: white; padding: 1em; border-radius: 4px; text-align: center; }}
                .links {{ list-style: none; padding: 0; }}
                .links li {{ margin: 0.5em 0; }}
                .links a {{ color: #3498db; text-decoration: none; font-weight: bold; }}
                .links a:hover {{ text-decoration: underline; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🔌 SIGEC-VE API</h1>
                <p>Sistema Integrado de Gerenciamento de Estações de Carregamento para Veículos Elétricos</p>

                <div class="status">
                    <strong>Status:</strong> Sistema Online ✅
                </div>

                <div class="stats">
                    <div class="stat-box">
                        <h3>{connected_count}</h3>
                        <p>Charge Points Conectados</p>
                    </div>
                    <div class="stat-box">
                        <h3>{ocpp_server.port}</h3>
                        <p>Porta OCPP</p>
                    </div>
                </div>

                <h2>📚 Documentação da API</h2>
                <ul class="links">
                    <li><a href="/docs">📖 Documentação Interativa (Swagger UI)</a></li>
                    <li><a href="/redoc">📋 Documentação ReDoc</a></li>
                    <li><a href="/charge_points/status">🔌 Status dos Charge Points</a></li>
                </ul>

                <p><small>Servidor OCPP rodando em ws://{ocpp_server.host}:{ocpp_server.port}</small></p>
            </div>
        </body>
    </html>
    """


@app.get("/charge_points/status", summary="Get all Charge Points status")
async def get_all_charge_points_status():
    """Get status of all charge points (connected and in database)."""
    connected_cps = list(connected_charge_points.keys())

    return {
        "connected_count": len(connected_cps),
        "connected_charge_points": connected_cps,
        "server_info": {
            "host": ocpp_server.host,
            "port": ocpp_server.port,
            "running": ocpp_server._running
        }
    }


@app.get("/charge_points/{cp_id}", response_model=dict, summary="Get Charge Point details")
async def get_charge_point(
        cp_id: str,
        service: DeviceManagementService = Depends(get_device_management_service)
):
    """Get details of a specific Charge Point by ID."""
    charge_point = service.get_charge_point_by_id(cp_id)
    if not charge_point:
        raise HTTPException(status_code=404, detail="Charge Point not found")

    is_online = cp_id in connected_charge_points

    return {
        "id": charge_point.id,
        "charge_point_id": charge_point.charge_point_id,
        "status": charge_point.status,
        "vendor": charge_point.vendor,
        "model": charge_point.model,
        "last_heartbeat": charge_point.last_heartbeat.isoformat() if charge_point.last_heartbeat else None,
        "num_connectors": charge_point.num_connectors,
        "is_online": is_online,
        "connectors": [
            {
                "id": c.id,
                "connector_id": c.connector_id,
                "status": c.status
            } for c in charge_point.connectors
        ],
        "transactions_count": len(charge_point.transactions)
    }


@app.post("/charge_points/{cp_id}/status", summary="Update Charge Point status")
async def update_cp_status(
        cp_id: str,
        status: str,
        service: DeviceManagementService = Depends(get_device_management_service)
):
    """Update the status of a Charge Point."""
    if service.update_charge_point_status(cp_id, status):
        return {"message": f"Charge Point {cp_id} status updated to {status}"}
    raise HTTPException(status_code=404, detail="Charge Point not found")


@app.post("/charge_points/{cp_id}/commands/{command_name}", summary="Send OCPP command to Charge Point")
async def send_command_to_charge_point(
        cp_id: str,
        command_name: str,
        payload: dict = None
):
    """Send an OCPP command to a specific Charge Point."""
    if not ocpp_server.is_connected(cp_id):
        raise HTTPException(
            status_code=404,
            detail=f"Charge Point {cp_id} is not connected"
        )

    try:
        result = await send_ocpp_command(cp_id, command_name, **(payload or {}))
        return result
    except Exception as e:
        logger.error(f"Error sending command {command_name} to {cp_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send command: {str(e)}"
        )


@app.post("/users/", response_model=dict, status_code=status.HTTP_201_CREATED, summary="Register new user")
async def register_user(
        user_id: str,
        name: str,
        email: str,
        id_tag: str,
        phone: str = None,
        service: DeviceManagementService = Depends(get_device_management_service)
):
    """Register a new user in the system."""
    try:
        new_user = service.add_user(
            user_id=user_id,
            name=name,
            email=email,
            id_tag=id_tag,
            phone=phone
        )
        return {
            "id": new_user.id,
            "user_id": new_user.user_id,
            "name": new_user.name,
            "email": new_user.email,
            "id_tag": new_user.id_tag,
            "is_active": new_user.is_active
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@app.get("/users/{user_id}", response_model=dict, summary="Get user details")
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
@app.get("/health", summary="Health check")
async def health_check():
    """Application health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": "2024-01-01T00:00:00Z",  # You can use datetime.utcnow().isoformat()
        "services": {
            "database": "connected",
            "ocpp_server": "running" if ocpp_server._running else "stopped",
            "connected_charge_points": len(connected_charge_points)
        }
    }
