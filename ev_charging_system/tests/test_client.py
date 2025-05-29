import asyncio
import websockets

async def test_connect():
    uri = "ws://localhost:9001/teste_path"
    print(f"Tentando conectar a {uri}")
    try:
        async with websockets.connect(uri) as websocket:
            print(f"Conectado a {uri}")
            await websocket.send("Olá, servidor de teste!")
            response = await websocket.recv()
            print(f"Mensagem recebida: {response}")
    except Exception as e:
        print(f"Erro na conexão: {e}")

if __name__ == "__main__":
    asyncio.run(test_connect())