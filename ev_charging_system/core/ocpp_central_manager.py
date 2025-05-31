# ev_charging_system/core/ocpp_central_manager.py

import logging
import json
# As exceções NotSupportedError e ProtocolError são úteis.
# CallError não está sendo importado diretamente aqui, pois causou o erro.
from ocpp.exceptions import NotSupportedError, ProtocolError

logger = logging.getLogger(__name__)

# Dicionário para manter a referência de todos os Charge Points conectados
# A chave é o ID do Charge Point e o valor é a instância do ChargePoint da biblioteca OCPP
connected_charge_points = {}

async def send_ocpp_command_to_cp(charge_point_id: str, command_name: str, payload: dict):
    """
    Envia um comando OCPP para um Charge Point específico.
    Ex: await send_ocpp_command_to_cp("CP001", "RemoteStartTransaction", {"idTag": "your-id-tag"})
    """
    if charge_point_id not in connected_charge_points:
        logger.warning(f"Charge Point {charge_point_id} not connected. Cannot send command {command_name}.")
        return {"status": "Failed", "reason": "Charge Point offline"}

    cp = connected_charge_points[charge_point_id]
    logger.info(f"Sending {command_name} to {charge_point_id} with payload: {payload}")

    try:
        # A biblioteca OCPP espera que você chame os métodos correspondentes aos comandos
        # diretamente na instância do Charge Point.
        if command_name == "RemoteStartTransaction":
            response = await cp.remote_start_transaction(**payload)
        elif command_name == "RemoteStopTransaction":
            response = await cp.remote_stop_transaction(**payload)
        elif command_name == "UnlockConnector":
            response = await cp.unlock_connector(**payload)
        elif command_name == "Reset":
            response = await cp.reset(**payload)
        # Adicione mais comandos conforme necessário
        else:
            logger.warning(f"Command '{command_name}' not implemented for direct sending.")
            return {"status": "Failed", "reason": f"Command '{command_name}' not implemented"}

        logger.info(f"Response from {charge_point_id} for {command_name}: {response}")
        return {"status": "Sent", "response": response}
    except Exception as e: # Captura a exceção genérica para não depender de CallError
        logger.error(f"Error sending command {command_name} to {charge_point_id}: {type(e).__name__} - {e}")
        return {"status": "Failed", "reason": f"OCPP Error or Internal server error: {e}"}


async def process_ocpp_message(charge_point_instance, message: str):
    """
    Processa uma mensagem OCPP recebida de um Charge Point.
    Esta função encaminha a mensagem para o roteador OCPP correto.
    """
    try:
        # A biblioteca OCPP processa automaticamente as mensagens recebidas
        # e chama o handler apropriado (@on(Action.BOOT_NOTIFICATION), etc.)
        # Este é o ponto onde a mensagem é "despachada" para o handler registrado.
        await charge_point_instance.route_message(message)
    except ProtocolError as e:
        logger.error(f"ProtocolError from {charge_point_instance.id}: {e}")
    except NotSupportedError as e:
        logger.warning(f"Unsupported OCPP message from {charge_point_instance.id}: {e}")
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON message from {charge_point_instance.id}: {message}")
    except Exception as e: # Captura qualquer outra exceção, incluindo as que antes seriam CallError
        logger.error(f"Unhandled exception while processing message from {charge_point_instance.id}: {e}", exc_info=True)


async def handle_ocpp_connection(websocket, path):
    """
    Este é o callback de conexão que o servidor WebSocket (ocpp_websocket_server.py)
    chama para cada nova conexão. Ele registra os handlers OCPP para o Charge Point.
    """
    # Importação local para evitar circular, garantindo que ocpp_server já carregou tudo que precisa
    from ev_charging_system.core.ocpp_server import on_connect
    await on_connect(websocket, path)