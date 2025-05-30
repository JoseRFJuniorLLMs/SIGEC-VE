import asyncio
import websockets
import json
import logging

# Configuração de logging para o script de teste
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_ocpp_server():
    # Mantenha o ID do Charge Point aqui.
    # Se seu servidor não usa '/CP-001', ajuste conforme o código do seu servidor.
    uri = "ws://localhost:9000/CP-001"
    logger.info(f"Tentando conectar ao servidor OCPP em {uri}...")

    try:
        # Tenta conectar ao servidor WebSocket, incluindo o subprotocolo OCPP 1.6
        async with websockets.connect(uri, subprotocols=["ocpp1.6"], ping_interval=None) as websocket:
            logger.info("Conectado com sucesso ao servidor OCPP!")

            # --- Teste de Envio de BootNotification (OCPP 1.6) ---
            boot_notification_payload = {
                "chargePointVendor": "MinhaEmpresa",
                "chargePointModel": "MeuModeloCP",
                "chargePointSerialNumber": "CP-001-TESTE",
                "firmwareVersion": "1.0.0",
                "iccid": "",
                "imsi": "",
                "meterType": "kWh",
                "meterSerialNumber": "MET-001-TESTE"
            }
            ocpp_message = [
                2, # MessageTypeId: 2 (Call) para requisições do Charge Point
                "testeBootNotification123", # MessageId: um ID único para esta mensagem
                "BootNotification", # Action
                boot_notification_payload # Payload
            ]

            message_to_send = json.dumps(ocpp_message)
            logger.info(f"Enviando mensagem: {message_to_send}")
            await websocket.send(message_to_send)

            # Espera pela resposta do servidor
            response = await websocket.recv()
            logger.info(f"Resposta recebida: {response}")

    except ConnectionRefusedError:
        logger.error("Erro: Conexão recusada. O servidor OCPP pode não estar rodando ou a porta está incorreta/bloqueada.")
    except websockets.exceptions.ConnectionClosedOK:
        logger.info("Conexão WebSocket fechada normalmente.")
    except websockets.exceptions.ConnectionClosedError as e:
        logger.error(f"Conexão WebSocket fechada com erro: {e}")
    except websockets.exceptions.InvalidStatus as e:
        logger.error(f"Erro no handshake do WebSocket: {e}. Provavelmente subprotocolo ou URL incorretos.")
    except Exception as e:
        logger.error(f"Ocorreu um erro inesperado durante o teste: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(test_ocpp_server())