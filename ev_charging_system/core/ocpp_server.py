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

logger = logging.getLogger(__name__)

# Dicionário para armazenar as instâncias de ChargePoint conectadas
# Key: charge_point_id (string), Value: OCPPCp instance
connected_charge_points = {}


async def on_connect(websocket, path):
    """
    Função chamada quando um Charge Point estabelece uma nova conexão WebSocket.
    """
    charge_point_id = path.strip('/')
    logger.info(f"Charge Point {charge_point_id} connected.")

    # Verifica se o CP já está conectado, para evitar duplicações
    if charge_point_id in connected_charge_points:
        logger.warning(f"Charge Point {charge_point_id} already connected. Closing old connection.")
        # Pode haver lógica para fechar a conexão antiga ou lidar com reconexões
        # Por simplicidade, vamos permitir a nova conexão e sobrescrever a antiga.

    db_session = next(get_db())
    device_service = DeviceManagementService(db_session)
    cp_in_db = device_service.get_charge_point_details(charge_point_id)

    if not cp_in_db:
        logger.warning(f"Unknown Charge Point {charge_point_id} connected. It must send a BootNotification.")
        # Você pode optar por rejeitar a conexão aqui se quiser
        # ou esperar pelo BootNotification para registro.
        # Por enquanto, permitimos e esperamos pelo BootNotification.
    else:
        # Se o CP for conhecido, atualize o status para "Online" se não estiver
        if cp_in_db.status != "Online":
            device_service.update_charge_point_status(charge_point_id, "Online")
            logger.info(f"Charge Point {charge_point_id} status updated to Online upon reconnection.")
    db_session.close()  # Fecha a sessão de BD

    # Cria uma instância de OCPPCp (ChargePoint da biblioteca ocpp)
    # create_route_map(ocpp_handlers) vai encontrar todos os handlers marcados com @on()
    charge_point = OCPPCp(charge_point_id, websocket, create_route_map(ocpp_handlers))
    connected_charge_points[charge_point_id] = charge_point

    try:
        # Inicia o loop de recebimento de mensagens do Charge Point
        await charge_point.start()
    except Exception as e:
        logger.error(f"Error with Charge Point {charge_point_id}: {e}")
    finally:
        logger.info(f"Charge Point {charge_point_id} disconnected.")
        # Remove o CP do dicionário de conectados
        if charge_point_id in connected_charge_points:
            del connected_charge_points[charge_point_id]

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
        subprotocols=["ocpp1.6"]  # Especifica o subprotocolo OCPP 1.6
    )

    logger.info(f"OCPP server started. Listening on ws://{host}:{port}...")
    await server.wait_closed()  # Mantém o servidor rodando até ser encerrado