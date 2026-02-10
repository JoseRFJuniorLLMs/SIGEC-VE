# ev_charging_system/main.py

from fastapi import FastAPI
from sqlalchemy.orm import Session
import uvicorn
import asyncio
import logging
import contextlib

# Import database
from ev_charging_system.data.models import Base
from ev_charging_system.data.database import engine

# Import OCPP server
from ev_charging_system.core.ocpp_server import ocpp_server

# Import routers
from ev_charging_system.api.routers import system, charge_points, transactions, users, events

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

# Include Routers
app.include_router(system.router)
app.include_router(charge_points.router)
app.include_router(transactions.router)
app.include_router(users.router)
app.include_router(events.router)

# --- Execução da Aplicação ---
if __name__ == "__main__":
    logger.info("INFO: Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)")
    uvicorn.run(app, host="0.0.0.0", port=8000)
