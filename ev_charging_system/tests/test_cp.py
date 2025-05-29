# test_cp.py
import asyncio
import websockets
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional


class OCPPTestClient:
    """Cliente de teste OCPP 1.6"""

    def __init__(self, cp_id: str, server_url: str = "ws://localhost:9000"):
        self.cp_id = cp_id
        self.server_url = f"{server_url}/{cp_id}"
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.message_counter = 0

    def generate_message_id(self) -> str:
        """Gera um ID único para cada mensagem"""
        self.message_counter += 1
        return f"{self.cp_id}_{self.message_counter}_{uuid.uuid4().hex[:8]}"

    def create_ocpp_message(self, action: str, payload: Dict[str, Any]) -> list:
        """Cria uma mensagem OCPP no formato correto"""
        return [
            2,  # MessageType.CALL
            self.generate_message_id(),
            action,
            payload
        ]

    async def connect(self):
        """Conecta ao servidor OCPP"""
        try:
            print(f"🔌 Conectando ao servidor OCPP: {self.server_url}")
            self.websocket = await websockets.connect(
                self.server_url,
                subprotocols=['ocpp1.6'],
                ping_interval=20,  # Ping a cada 20 segundos
                ping_timeout=10  # Timeout de 10 segundos para pong
            )
            print(f"✅ Conectado com sucesso!")
            return True
        except Exception as e:
            print(f"❌ Erro ao conectar: {e}")
            return False

    async def send_message(self, action: str, payload: Dict[str, Any]) -> Optional[Dict]:
        """Envia uma mensagem OCPP e aguarda resposta"""
        if not self.websocket:
            print("❌ WebSocket não está conectado")
            return None

        try:
            message = self.create_ocpp_message(action, payload)
            message_json = json.dumps(message)

            print(f"📤 Enviando {action}: {message_json}")
            await self.websocket.send(message_json)

            # Aguarda resposta
            response = await self.websocket.recv()
            print(f"📥 Resposta recebida: {response}")

            return json.loads(response)

        except Exception as e:
            print(f"❌ Erro ao enviar mensagem {action}: {e}")
            return None

    async def boot_notification(self):
        """Envia BootNotification"""
        payload = {
            "chargePointVendor": "SIGEC-VE",
            "chargePointModel": "TestModel-001",
            "firmwareVersion": "1.0.0",
            "chargePointSerialNumber": f"CP-{self.cp_id}",
            "iccid": "",
            "imsi": "",
            "meterType": "AC.SampleClock",
            "meterSerialNumber": f"M-{self.cp_id}-001"
        }

        response = await self.send_message("BootNotification", payload)

        if response and len(response) >= 4:
            status = response[3].get("status", "Unknown")
            interval = response[3].get("interval", 300)
            print(f"🔔 BootNotification Status: {status}, HeartbeatInterval: {interval}s")
            return status == "Accepted", interval

        return False, 300

    async def heartbeat(self):
        """Envia Heartbeat"""
        response = await self.send_message("Heartbeat", {})

        if response and len(response) >= 4:
            current_time = response[3].get("currentTime", "Unknown")
            print(f"💓 Heartbeat OK - Server Time: {current_time}")
            return True

        return False

    async def status_notification(self, connector_id: int = 1, status: str = "Available"):
        """Envia StatusNotification"""
        payload = {
            "connectorId": connector_id,
            "errorCode": "NoError",
            "status": status,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

        response = await self.send_message("StatusNotification", payload)
        print(f"📊 StatusNotification enviado: Connector {connector_id} = {status}")
        return response is not None

    async def start_transaction(self, connector_id: int = 1, id_tag: str = "RFID123456"):
        """Simula início de transação"""
        payload = {
            "connectorId": connector_id,
            "idTag": id_tag,
            "meterStart": 12345,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

        response = await self.send_message("StartTransaction", payload)

        if response and len(response) >= 4:
            transaction_id = response[3].get("transactionId")
            auth_status = response[3].get("idTagInfo", {}).get("status", "Unknown")
            print(f"🔋 StartTransaction - ID: {transaction_id}, Auth: {auth_status}")
            return transaction_id, auth_status == "Accepted"

        return None, False

    async def stop_transaction(self, transaction_id: int, meter_stop: int = 15000):
        """Simula fim de transação"""
        payload = {
            "transactionId": transaction_id,
            "meterStop": meter_stop,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "reason": "Local"
        }

        response = await self.send_message("StopTransaction", payload)

        if response and len(response) >= 4:
            auth_status = response[3].get("idTagInfo", {}).get("status", "Unknown")
            print(f"🛑 StopTransaction - Auth: {auth_status}")
            return auth_status == "Accepted"

        return False

    async def meter_values(self, connector_id: int = 1, transaction_id: Optional[int] = None):
        """Envia MeterValues"""
        payload = {
            "connectorId": connector_id,
            "meterValue": [
                {
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "sampledValue": [
                        {
                            "value": "13500",
                            "context": "Sample.Periodic",
                            "format": "Raw",
                            "measurand": "Energy.Active.Import.Register",
                            "unit": "Wh"
                        },
                        {
                            "value": "220.5",
                            "context": "Sample.Periodic",
                            "format": "Raw",
                            "measurand": "Voltage",
                            "unit": "V"
                        }
                    ]
                }
            ]
        }

        if transaction_id:
            payload["transactionId"] = transaction_id

        response = await self.send_message("MeterValues", payload)
        print(f"📊 MeterValues enviado para connector {connector_id}")
        return response is not None

    async def disconnect(self):
        """Desconecta do servidor"""
        if self.websocket:
            await self.websocket.close()
            print("🔌 Desconectado do servidor")


async def test_complete_scenario():
    """Testa um cenário completo de carregamento"""
    cp_id = "CP_TESTE_001"
    client = OCPPTestClient(cp_id)

    try:
        # 1. Conectar
        if not await client.connect():
            return

        # 2. BootNotification
        print("\n=== FASE 1: Boot Notification ===")
        accepted, heartbeat_interval = await client.boot_notification()

        if not accepted:
            print("❌ BootNotification rejeitada")
            return

        # 3. StatusNotification inicial
        print("\n=== FASE 2: Status Notification ===")
        await client.status_notification(1, "Available")

        # 4. Heartbeat
        print("\n=== FASE 3: Heartbeat ===")
        await client.heartbeat()

        # 5. Simular início de carregamento
        print("\n=== FASE 4: Start Transaction ===")
        await client.status_notification(1, "Preparing")
        transaction_id, auth_ok = await client.start_transaction(1, "RFID123456")

        if auth_ok and transaction_id:
            await client.status_notification(1, "Charging")

            # 6. Enviar alguns MeterValues
            print("\n=== FASE 5: Meter Values ===")
            for i in range(3):
                await client.meter_values(1, transaction_id)
                await asyncio.sleep(2)

            # 7. Finalizar transação
            print("\n=== FASE 6: Stop Transaction ===")
            await client.stop_transaction(transaction_id, 15000)
            await client.status_notification(1, "Available")

        # 8. Heartbeat final
        print("\n=== FASE 7: Heartbeat Final ===")
        await client.heartbeat()

        print("\n✅ Teste completo finalizado!")

    except KeyboardInterrupt:
        print("\n⏹️ Teste interrompido pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro durante o teste: {e}")
    finally:
        await client.disconnect()


# Teste individual de Boot Notification (compatível com seu código original)
async def test_boot_notification():
    """Teste simples de BootNotification (mantendo compatibilidade)"""
    cp_id = "CP_TESTE_001"
    uri = f"ws://localhost:9000/{cp_id}"

    try:
        async with websockets.connect(uri, subprotocols=['ocpp1.6']) as websocket:
            print(f"Connected to {uri}")

            # BootNotification
            boot_notification = [
                2,
                "12345",
                "BootNotification",
                {
                    "chargePointVendor": "OCPP Test Vendor",
                    "chargePointModel": "TestModel-001",
                    "firmwareVersion": "1.0.0",
                    "iccid": "",
                    "imsi": "",
                    "meterType": "SimpleMeter",
                    "meterSerialNumber": "M-SN-001",
                    "chargePointSerialNumber": "CP-SN-001"
                }
            ]
            print(f"Sending BootNotification: {boot_notification}")
            await websocket.send(json.dumps(boot_notification))

            response = await websocket.recv()
            print(f"Received response: {response}")

            # Heartbeat
            heartbeat = [
                2,
                "54321",
                "Heartbeat",
                {}
            ]
            print(f"Sending Heartbeat: {heartbeat}")
            await websocket.send(json.dumps(heartbeat))
            response = await websocket.recv()
            print(f"Received response: {response}")

            await asyncio.sleep(2)

    except Exception as e:
        print(f"Erro: {e}")


if __name__ == "__main__":
    print("🧪 OCPP Test Client")
    print("1 - Teste completo (recomendado)")
    print("2 - Teste simples (original)")

    choice = input("Escolha o teste (1/2): ").strip()

    if choice == "2":
        asyncio.run(test_boot_notification())
    else:
        asyncio.run(test_complete_scenario())