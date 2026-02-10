from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlalchemy import text
from ev_charging_system.core.ocpp_server import ocpp_server, connected_charge_points
from ev_charging_system.data.database import get_db
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/", response_class=HTMLResponse, summary="Root endpoint")
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

@router.get("/api/health", summary="Health check")
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
