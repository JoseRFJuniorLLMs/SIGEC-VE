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
# A porta padrão do FastAPI/Uvicorn é 8000.
# Mantenha esta URL consistente com a porta em que seu main.py realmente roda.
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
        # O EV solicita ao CSMS o início de uma transação.
        # Rota correta agora é /api/ev_events/plug_in
        plug_in_url = f"{CSMS_API_URL}/ev_events/plug_in"
        plug_in_payload = {
            "ev_id": user_id,
            "charge_point_id": charge_point_id,
            "connector_id": connector_id
        }

        logger.info(f"VE '{user_id}': Solicitando início de transação ao CSMS para CP '{charge_point_id}' via {plug_in_url}...")
        async with aiohttp.ClientSession() as session:
            async with session.post(plug_in_url, json=plug_in_payload) as response:
                response.raise_for_status()  # Levanta uma exceção para erros HTTP (4xx ou 5xx)
                plug_in_response_data = await response.json()
                logger.info(f"VE '{user_id}': Resposta da API de plug-in: {plug_in_response_data}")

                # A API retorna um "transactionId" temporário ou o ID da transação
                transaction_id = plug_in_response_data.get("transactionId")
                if not transaction_id:
                    logger.error(f"VE '{user_id}': Resposta da API não retornou 'transactionId'.")
                    raise ValueError("Transaction ID not returned by API from plug-in event.")

        # 2. Simular carregamento ativo (espera)
        logger.info(f"VE '{user_id}': Carregando por {charging_time_seconds} segundos (ID Transação: {transaction_id})...")
        await asyncio.sleep(charging_time_seconds)
        logger.info(f"VE '{user_id}': Carregamento concluído. Consumo simulado: {simulated_kwh_consumption:.2f} kWh.")

        # 3. Simular "Unplug" do VE (comunicação EV -> CSMS via API)
        # O EV solicita ao CSMS o fim da transação.
        # Rota correta agora é /api/ev_events/unplug
        unplug_url = f"{CSMS_API_URL}/ev_events/unplug"
        unplug_payload = {
            "ev_id": user_id,
            "charge_point_id": charge_point_id,
            "connector_id": connector_id,
            "transaction_id": transaction_id # Enviamos o ID da transação recebido no plug-in
        }

        logger.info(f"VE '{user_id}': Solicitando fim de transação ao CSMS para CP '{charge_point_id}' via {unplug_url}...")
        async with aiohttp.ClientSession() as session:
            async with session.post(unplug_url, json=unplug_payload) as response:
                response.raise_for_status()
                logger.info(f"VE '{user_id}': Resposta da API de unplug: {await response.json()}")

    except aiohttp.ClientResponseError as e:
        logger.error(f"VE '{user_id}': Erro de comunicação com a API do CSMS: {e.status}, message='{e.message}', url='{e.request_info.url}'")
    except aiohttp.ClientConnectorError as e:
        logger.error(f"VE '{user_id}': Erro de conexão com a API do CSMS: {e}. Verifique se o servidor CSMS está rodando em {CSMS_API_URL}.")
    except Exception as e:
        logger.error(f"VE '{user_id}': Ocorreu um erro inesperado durante a simulação: {e}", exc_info=True)
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
        num_simulations = 5  # Número total de sessões de carregamento a simular

        for i in range(num_simulations):
            cp_id, conn_id = random.choice(cps_and_connectors)
            user_id = random.choice(users)

            # Introduzir um pequeno atraso aleatório antes de iniciar cada sessão
            # Isso ajuda a distribuir as requisições e evitar sobrecarga inicial
            delay = random.uniform(0.1, 1.0)
            await asyncio.sleep(delay)

            task = asyncio.create_task(simulate_ev_charging_session(cp_id, conn_id, user_id))
            tasks.append(task)

        try:
            await asyncio.gather(*tasks)
            logger.info(f"Todas as {num_simulations} simulações de Veículos Elétricos foram concluídas.")
        except KeyboardInterrupt:
            logger.info("Simulações de VE interrompidas pelo usuário.")
        except Exception as e:
            logger.error(f"Erro inesperado no main_ev_sim: {e}", exc_info=True)

    asyncio.run(main_ev_sim())