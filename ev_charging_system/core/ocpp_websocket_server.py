# ev_charging_system/core/ocpp_websocket_server.py

import asyncio
import websockets
import logging
from ocpp.v16 import ChargePoint as OCPPCp
from ocpp.v16 import call
import json

# Importe o ocpp_central_manager para usar a lista de CPs conectados e lidar com mensagens
from ev_charging_system.core.ocpp_central_manager import process_ocpp_message, connected_charge_points, handle_ocpp_connection

logger = logging.getLogger(__name__)

class OCPPWebSocketServer:
    def __init__(self, host: str, port: int, on_connect=None):
        self.host = host
        self.port = port
        self.on_connect = on_connect # Callback para novas conexões (pode ser o on_connect do ocpp_server.py)
        self.server = None

    async def start(self):
        """Inicia o servidor WebSocket OCPP."""
        # 'handle_connection' é o que 'websockets' espera como callback para novas conexões.
        # Ele chamará o 'on_connect' passado no construtor para o OCPP ChargePoint específico.
        self.server = await websockets.serve(
            self.handle_connection,
            self.host,
            self.port,
            subprotocols=['ocpp2.0', 'ocpp2.0.1']# Define o subprotocolo OCPP 1.6
        )
        logger.info(f"OCPP WebSocket Server started on ws://{self.host}:{self.port}")
        await self.server.wait_closed() # Mantém o servidor rodando até ser fechado explicitamente

    async def handle_connection(self, websocket, path):
        """
        Lida com cada nova conexão WebSocket de um Charge Point.
        A 'path' geralmente contém o ID do Charge Point (e.g., /CP001).
        """
        # Extrai o ID do Charge Point do caminho da URL (e.g., '/CP001' -> 'CP001')
        charge_point_id = path.strip('/')
        if not charge_point_id:
            logger.warning("Connection attempt with empty charge point ID in path. Closing.")
            return

        logger.info(f"New connection from Charge Point: {charge_point_id}")

        # Cria uma instância do ChargePoint da biblioteca OCPP
        cp = OCPPCp(charge_point_id, websocket)

        # Adiciona o Charge Point à lista de conectados no manager central
        connected_charge_points[charge_point_id] = cp

        # Chama o callback de conexão (provavelmente o on_connect de ocpp_server.py)
        # que registrará os handlers de mensagens para este CP.
        if self.on_connect:
            await self.on_connect(websocket, path)

        try:
            # Loop para receber e processar mensagens do Charge Point
            while True:
                try:
                    message = await websocket.recv()
                    logger.debug(f"Received message from {charge_point_id}: {message}")
                    # Processa a mensagem usando a lógica do ocpp_central_manager
                    await process_ocpp_message(cp, message)
                except websockets.exceptions.ConnectionClosedOK:
                    logger.info(f"Connection with Charge Point {charge_point_id} closed normally.")
                    break
                except websockets.exceptions.ConnectionClosed as e:
                    logger.warning(f"Connection with Charge Point {charge_point_id} closed abnormally: {e}")
                    break
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON received from {charge_point_id}: {message}")
                except Exception as e:
                    logger.error(f"Error processing message from {charge_point_id}: {e}", exc_info=True)
                    # Dependendo do erro, você pode querer enviar um CallError de volta ao CP
                    # await cp.send_call_error(msg_id, ErrorCode.internal_error, str(e))
        finally:
            # Quando a conexão é encerrada, remove o Charge Point da lista
            if charge_point_id in connected_charge_points:
                logger.info(f"Removing Charge Point {charge_point_id} from connected list.")
                connected_charge_points.pop(charge_point_id, None)

    async def stop(self):
        """Para o servidor WebSocket OCPP."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logger.info("OCPP WebSocket Server stopped.")