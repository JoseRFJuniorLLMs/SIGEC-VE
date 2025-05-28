# test_cp.py
import asyncio
import websockets
import json

async def test_boot_notification():
    cp_id = "CP_TESTE_001"
    uri = f"ws://localhost:9000/{cp_id}" # Conecte ao seu servidor OCPP

    async with websockets.connect(uri, subprotocols=['ocpp1.6']) as websocket:
        print(f"Connected to {uri}")

        # Exemplo de BootNotification
        boot_notification = [
            2, # MessageType.CALL
            "12345", # UniqueId (ID da mensagem)
            "BootNotification", # Action
            { # Payload
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

        # Exemplo de Heartbeat (após BootNotification)
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

        await asyncio.sleep(5) # Mantenha a conexão por um tempo

if __name__ == "__main__":
    asyncio.run(test_boot_notification())