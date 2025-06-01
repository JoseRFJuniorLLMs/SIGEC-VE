import requests
import time
import random
import logging
import asyncio
from datetime import datetime, timezone
import aiohttp  # Importação adicionada para requisições assíncronas

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('ev_simulator')

# URL da sua API RESTful do CSMS (main.py ou ocpp_server.py)
# A porta padrão do FastAPI/Uvicorn é 8000
CSMS_API_URL = "http://localhost:8000/api"


async def simulate_ev_charging_session(charge_point_id: str, connector_id: int, user_id: str):
    logger.info(f"-------------------------------------------------------")
    logger.info(f"Simulando VE '{user_id}' no CP '{charge_point_id}', conector {connector_id}...")
    transaction_id = None

    # Simular uma duração de carregamento e kWh a consumir
    charging_time_seconds = random.randint(15, 60)  # Carregamento de 15 a 60 segundos
    simulated_kwh_consumption = random.uniform(5.0, 30.0)  # Consumo de 5 a 30 kWh

    try:
        # 1. Simular "Plug-in" do VE (comunicação EV -> CSMS via API)
        # O EV solicita ao CSMS para iniciar uma transação no CP
        start_charging_url = f"{CSMS_API_URL}/charge_points/{charge_point_id}/start_transaction"
        start_charging_payload = {
            "connector_id": connector_id,
            "id_token": user_id,  # Usando user_id como id_token para simplificar
            "remote_start": True # Indica que é um início remoto iniciado pelo CSMS
        }
        logger.info(f"VE '{user_id}': Solicitando início de transação ao CSMS para CP '{charge_point_id}'...")
        async with aiohttp.ClientSession() as session:
            async with session.post(start_charging_url, json=start_charging_payload) as response:
                response.raise_for_status()  # Levanta uma exceção para erros HTTP (4xx ou 5xx)
                start_response = await response.json()
                transaction_id = start_response.get("transaction_id")
                if not transaction_id:
                    logger.error(f"VE '{user_id}': CSMS não retornou transaction_id. Resposta: {start_response}")
                    return

        logger.info(f"VE '{user_id}': Transação {transaction_id} iniciada no CP '{charge_point_id}'. Carregando...")

        # 2. Simular carregamento ativo
        # Durante o carregamento real, o CP enviaria MeterValues. Aqui, o VE apenas espera.
        await asyncio.sleep(charging_time_seconds)

        # 3. Simular "Unplug" do VE (comunicação EV -> CSMS via API)
        # O EV solicita ao CSMS para parar a transação
        stop_charging_url = f"{CSMS_API_URL}/charge_points/{charge_point_id}/stop_transaction"
        stop_charging_payload = {
            "transaction_id": transaction_id,
            "remote_stop": True # Indica que é uma parada remota iniciada pelo CSMS
        }
        logger.info(f"VE '{user_id}': Solicitando parada de transação {transaction_id} ao CSMS para CP '{charge_point_id}'...")
        async with aiohttp.ClientSession() as session:
            async with session.post(stop_charging_url, json=stop_charging_payload) as response:
                response.raise_for_status()
                await response.json()

        logger.info(f"VE '{user_id}': Transação {transaction_id} finalizada. Consumo simulado: {simulated_kwh_consumption:.2f} kWh.")

    except aiohttp.ClientResponseError as e:
        logger.error(f"VE '{user_id}': Erro de comunicação com a API do CSMS: {e.status}, message='{e.message}', url='{e.request_info.url}'", exc_info=True)
    except aiohttp.ClientConnectionError as e:
        logger.error(f"VE '{user_id}': Erro de conexão com a API do CSMS: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"VE '{user_id}': Um erro inesperado ocorreu durante a simulação: {e}", exc_info=True)
    finally:
        logger.info(f"-------------------------------------------------------")


if __name__ == '__main__':
    async def main_ev_sim():
        logger.info("Iniciando simuladores de Veículos Elétricos dinamicamente...")

        # Lista de CPs e conectores disponíveis (idealmente viria de uma API do CSMS)
        # Importante: Estes IDs de CP (CP_001, CP_002, CP_003) PRECISAM BATER
        # com os IDs que você configurou no charge_point_simulator.py
        cps_and_connectors = [
            ("CP_001", 1), ("CP_001", 2),
            ("CP_002", 1), ("CP_002", 2),
            ("CP_003", 1), ("CP_003", 2) # Adicionado CP_003 para corresponder ao outro simulador
        ]
        users = [f"User-EV-{i:03d}" for i in range(1, 16)]  # 15 usuários simulados

        tasks = []
        num_simulations = 30  # Número total de sessões de carregamento a simular

        for i in range(num_simulations):
            cp_id, conn_id = random.choice(cps_and_connectors)
            user_id = random.choice(users)

            # Introduzir um pequeno atraso aleatório antes de iniciar cada sessão
            await asyncio.sleep(random.uniform(0.5, 3.0))  # Atraso
            task = asyncio.create_task(simulate_ev_charging_session(cp_id, conn_id, user_id))
            tasks.append(task)

        await asyncio.gather(*tasks)
        logger.info("Todas as %d simulações de Veículos Elétricos foram concluídas.", num_simulations)


    asyncio.run(main_ev_sim())