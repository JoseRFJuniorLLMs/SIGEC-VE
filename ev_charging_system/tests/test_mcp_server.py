#!/usr/bin/env python3
"""
Servidor OCPP básico para testes
"""

import asyncio
import websockets
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import uuid

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OCPPTestServer:
    """Servidor OCPP 1.6 básico para testes"""

    def __init__(self, host: str = "localhost", port: int = 9000):
        self.host = host
        self.port = port
        self.connected_chargers: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.transactions: Dict[int, Dict[str, Any]] = {}
        self.next_transaction_id = 1

    def generate_transaction_id(self) -> int:
        """Gera um novo ID de transação"""
        tid = self.next_transaction_id
        self.next_transaction_id += 1
        return tid

    def create_call_result(self, unique_id: str, payload: Dict[str, Any]) -> str:
        """Cria uma resposta OCPP CALLRESULT"""
        message = [3, unique_id, payload]  # MessageType.CALLRESULT
        return json.dumps(message)

    def create_call_error(self, unique_id: str, error_code: str, error_description: str) -> str:
        """Cria uma resposta de erro OCPP CALLERROR"""
        message = [4, unique_id, error_code, error_description, {}]  # MessageType.CALLERROR
        return json.dumps(message)

    async def handle_boot_notification(self, unique_id: str, payload: Dict[str, Any]) -> str:
        """Processa BootNotification"""
        vendor = payload.get("chargePointVendor", "Unknown")
        model = payload.get("chargePointModel", "Unknown")
        serial = payload.get("chargePointSerialNumber", "Unknown")

        logger.info(f"📋 BootNotification - Vendor: {vendor}, Model: {model}, Serial: {serial}")

        response_payload = {
            "status": "Accepted",
            "currentTime": datetime.utcnow().isoformat() + "Z",
            "interval": 60  # Heartbeat interval em segundos
        }

        return self.create_call_result(unique_id, response_payload)

    async def handle_heartbeat(self, unique_id: str, payload: Dict[str, Any]) -> str:
        """Processa Heartbeat"""
        logger.info("💓 Heartbeat recebido")

        response_payload = {
            "currentTime": datetime.utcnow().isoformat() + "Z"
        }

        return self.create_call_result(unique_id, response_payload)

    async def handle_status_notification(self, unique_id: str, payload: Dict[str, Any]) -> str:
        """Processa StatusNotification"""
        connector_id = payload.get("connectorId", 0)
        status = payload.get("status", "Unknown")
        error_code = payload.get("errorCode", "NoError")

        logger.info(f"📊 StatusNotification - Connector {connector_id}: {status} ({error_code})")

        response_payload = {}
        return self.create_call_result(unique_id, response_payload)

    async def handle_start_transaction(self, unique_id: str, payload: Dict[str, Any]) -> str:
        """Processa StartTransaction"""
        connector_id = payload.get("connectorId", 1)
        id_tag = payload.get("idTag", "Unknown")
        meter_start = payload.get("meterStart", 0)

        transaction_id = self.generate_transaction_id()

        # Armazenar dados da transação
        self.transactions[transaction_id] = {
            "connectorId": connector_id,
            "idTag": id_tag,
            "meterStart": meter_start,
            "startTime": datetime.utcnow(),
            "active": True
        }

        logger.info(f"🔋 StartTransaction - ID: {transaction_id}, Tag: {id_tag}, Connector: {connector_id}")

        response_payload = {
            "transactionId": transaction_id,
            "idTagInfo": {
                "status": "Accepted"
            }
        }

        return self.create_call_result(unique_id, response_payload)

    async def handle_stop_transaction(self, unique_id: str, payload: Dict[str, Any]) -> str:
        """Processa StopTransaction"""
        transaction_id = payload.get("transactionId")
        meter_stop = payload.get("meterStop", 0)
        reason = payload.get("reason", "Local")

        if transaction_id in self.transactions:
            transaction = self.transactions[transaction_id]
            transaction["active"] = False
            transaction["meterStop"] = meter_stop
            transaction["stopTime"] = datetime.utcnow()

            energy_consumed = meter_stop - transaction["meterStart"]
            logger.info(f"🛑 StopTransaction - ID: {transaction_id}, Energia: {energy_consumed}Wh, Razão: {reason}")
        else:
            logger.warning(f"⚠️ Transação {transaction_id} não encontrada")

        response_payload = {
            "idTagInfo": {
                "status": "Accepted"
            }
        }

        return self.create_call_result(unique_id, response_payload)

    async def handle_meter_values(self, unique_id: str, payload: Dict[str, Any]) -> str:
        """Processa MeterValues"""
        connector_id = payload.get("connectorId", 1)
        transaction_id = payload.get("transactionId")
        meter_values = payload.get("meterValue", [])

        for meter_value in meter_values:
            timestamp = meter_value.get("timestamp", "Unknown")
            sampled_values = meter_value.get("sampledValue", [])

            for sample in sampled_values:
                value = sample.get("value", "0")
                measurand = sample.get("measurand", "Unknown")
                unit = sample.get("unit", "")

                logger.info(f"📊 MeterValues - Connector {connector_id}: {measurand} = {value}{unit}")

        response_payload = {}
        return self.create_call_result(unique_id, response_payload)

    async def handle_message(self, websocket, path: str, message: str) -> Optional[str]:
        """Processa mensagens OCPP recebidas"""
        try:
            data = json.loads(message)

            if not isinstance(data, list) or len(data) < 3:
                return self.create_call_error("unknown", "FormationViolation", "Invalid message format")

            message_type = data[0]
            unique_id = data[1]

            if message_type == 2:  # CALL
                action = data[2]
                payload = data[3] if len(data) > 3 else {}

                logger.info(f"📤 Recebido {action} de {path}")

                # Roteamento das mensagens
                if action == "BootNotification":
                    return await self.handle_boot_notification(unique_id, payload)
                elif action == "Heartbeat":
                    return await self.handle_heartbeat(unique_id, payload)
                elif action == "StatusNotification":
                    return await self.handle_status_notification(unique_id, payload)
                elif action == "StartTransaction":
                    return await self.handle_start_transaction(unique_id, payload)
                elif action == "StopTransaction":
                    return await self.handle_stop_transaction(unique_id, payload)
                elif action == "MeterValues":
                    return await self.handle_meter_values(unique_id, payload)
                else:
                    logger.warning(f"⚠️ Ação não suportada: {action}")
                    return self.create_call_error(unique_id, "NotSupported", f"Action {action} not supported")

            else:
                logger.warning(f"⚠️ Tipo de mensagem não suportado: {message_type}")
                return self.create_call_error(unique_id, "MessageTypeNotSupported", "Only CALL messages supported")

        except json.JSONDecodeError:
            logger.error("❌ Erro ao decodificar JSON")
            return self.create_call_error("unknown", "FormationViolation", "Invalid JSON")
        except Exception as e:
            logger.error(f"❌ Erro ao processar mensagem: {e}")
            return self.create_call_error("unknown", "InternalError", str(e))

        return None

    async def handle_client(self, websocket, path: str):
        """Lida com conexões de clientes"""
        # Extrair ID do charge point do path
        cp_id = path.strip('/')
        if not cp_id:
            cp_id = f"CP_{uuid.uuid4().hex[:8]}"

        self.connected_chargers[cp_id] = websocket
        logger.info(f"🔌 Charge Point conectado: {cp_id} ({websocket.remote_address})")

        try:
            async for message in websocket:
                logger.debug(f"📨 Mensagem de {cp_id}: {message}")

                response = await self.handle_message(websocket, cp_id, message)

                if response:
                    logger.debug(f"📤 Resposta para {cp_id}: {response}")
                    await websocket.send(response)

        except websockets.exceptions.ConnectionClosed:
            logger.info(f"🔌 Charge Point desconectado: {cp_id}")
        except Exception as e:
            logger.error(f"❌ Erro na conexão com {cp_id}: {e}")
        finally:
            if cp_id in self.connected_chargers:
                del self.connected_chargers[cp_id]

    async def start_server(self):
        """Inicia o servidor OCPP"""
        logger.info(f"🚀 Iniciando servidor OCPP em {self.host}:{self.port}")
        logger.info("📋 Protocolos suportados: ocpp1.6")
        logger.info("🔌 Aguardando conexões de Charge Points...")

        return await websockets.serve(
            self.handle_client,
            self.host,
            self.port,
            subprotocols=['ocpp1.6']
        )

    def print_status(self):
        """Imprime status atual do servidor"""
        print(f"\n📊 Status do Servidor OCPP")
        print(f"🔌 Charge Points conectados: {len(self.connected_chargers)}")
        for cp_id in self.connected_chargers.keys():
            print(f"  - {cp_id}")

        print(f"🔋 Transações ativas: {len([t for t in self.transactions.values() if t.get('active', False)])}")
        print(f"🔋 Total de transações: {len(self.transactions)}")


async def main():
    """Função principal"""
    server = OCPPTestServer()

    try:
        # Iniciar servidor
        websocket_server = await server.start_server()

        # Mostrar status a cada 30 segundos
        async def status_monitor():
            while True:
                await asyncio.sleep(30)
                server.print_status()

        # Executar ambos concorrentemente
        await asyncio.gather(
            websocket_server.wait_closed(),
            status_monitor()
        )

    except KeyboardInterrupt:
        logger.info("🛑 Servidor interrompido pelo usuário")
    except Exception as e:
        logger.error(f"❌ Erro no servidor: {e}")


if __name__ == "__main__":
    asyncio.run(main())