# ev_charging_system/core/ocpp_server.py

import asyncio
import logging
from ocpp.routing import create_route_map
from ocpp.v16 import ChargePoint as OCPPCp
from websockets import serve as serve_websocket

# Importa os handlers que você acabou de criar
from ev_charging_system.core import ocpp_handlers
from ev_charging_system.data.database import SessionLocal, get_db
from ev_charging_system.business_logic.device_management_service import DeviceManagementService
from ev_charging_system.models.charge_point import ChargePoint

# --- INÍCIO DA ATUALIZAÇÃO CRÍTICA NESTE ARQUIVO ---
# AGORA VOCÊ VAI IMPORTAR connected_charge_points e send_ocpp_command_to_cp
# do novo módulo ocpp_central_manager.py
from ev_charging_system.core.ocpp_central_manager import connected_charge_points, send_ocpp_command_to_cp
# --- FIM DA ATUALIZAÇÃO CRÍTICA NESTE ARQUIVO ---

logger = logging.getLogger(__name__)

# --- REMOVA TODAS ESTAS LINHAS (se existirem no seu arquivo): ---
# connected_charge_points = {}
# async def send_ocpp_command_to_cp(charge_point_id: str, command_name: str, payload: dict) -> bool:
#    # ... toda a implementação desta função deve ser REMOVIDA daqui ...
# --- FIM DA REMOÇÃO ---


async def on_connect(websocket, path):
    """
    Função chamada quando um Charge Point estabelece uma nova conexão WebSocket.
    """
    charge_point_id = path.strip('/')
    logger.info(f"Charge Point {charge_point_id} connected.")

    # Verifica se o CP já está conectado, para evitar duplicações
    if charge_point_id in connected_charge_points: # Usa o dicionário IMPORTADO
        logger.warning(f"Charge Point {charge_point_id} already connected. Closing old connection.")
        pass

    # Cria uma instância de ChargePoint da biblioteca ocpp
    # create_route_map(ocpp_handlers) vai encontrar todos os handlers marcados com @on()
    charge_point = OCPPCp(charge_point_id, websocket, create_route_map(ocpp_handlers))
    connected_charge_points[charge_point_id] = charge_point # Usa o dicionário IMPORTADO

    try:
        # Inicia o loop de recebimento de mensagens do Charge Point
        await charge_point.start()
    except Exception as e:
        logger.error(f"Error with Charge Point {charge_point_id}: {e}")
    finally:
        logger.info(f"Charge Point {charge_point_id} disconnected.")
        # Remove o CP do dicionário de conectados
        if charge_point_id in connected_charge_points:
            del connected_charge_points[charge_point_id] # Usa o dicionário IMPORTADO

        # Opcional: Atualizar status do CP para offline no DB
        db_session = next(get_db())
        device_service = DeviceManagementService(db_session)
        device_service.update_charge_point_status(charge_point_id, "Offline")
        db_session.close()


async def start_ocpp_server(host: str, port: int):
    """
    Inicia o servidor OCPP WebSocket.
    """
    logger.info(f"Starting OCPP server on ws://{host}:{port}")
    server = await serve_websocket(
        on_connect,
        host,
        port,
        subprotocols=['ocpp1.6']
    )
    await server.wait_closed()