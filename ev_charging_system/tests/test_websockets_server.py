import asyncio
import logging
from websockets import serve as serve_websocket

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ATENÇÃO: 'path' agora é opcional para diagnóstico
async def simple_on_connect(websocket, path=None):
    """
    Função de conexão simples para testar o argumento 'path'.
    """
    logger.info(f"Conexão recebida! Path: {path}") # Irá mostrar None se o path não for passado
    try:
        # Apenas espera por mensagens, não faz nada complexo
        await websocket.recv()
    except Exception as e:
        logger.error(f"Erro na conexão: {e}")
    finally:
        logger.info(f"Conexão com path '{path}' encerrada.")

async def main():
    host = "0.0.0.0"
    port = 9001 # Usando uma porta diferente para não conflitar com o servidor OCPP
    logger.info(f"Iniciando servidor websockets de teste em ws://{host}:{port}")
    server = await serve_websocket(
        simple_on_connect,
        host,
        port,
    )
    logger.info(f"Servidor de teste iniciado. Escutando em ws://{host}:{port}...")
    await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())