import requests
import time
import random
import logging
import asyncio
from datetime import datetime, timezone
import aiohttp  # Importação adicionada para requisições assíncronas

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('ev_simulator')

# URL da sua API RESTful do CSMS (main.py)
# CORREÇÃO AQUI: A porta padrão do FastAPI/Uvicorn é 8000, não 8001
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
        logger.info(f"VE '{user_id}': Enviando evento de Plug-in para CP '{charge_point_id}'...")

        # Usando aiohttp para requisições assíncronas
        async with aiohttp.ClientSession() as session:
            async with session.post(
                    f"{CSMS_API_URL}/ev_events/plug_in",
                    json={
                        "charge_point_id": charge_point_id,
                        "connector_id": connector_id,
                        "ev_id": user_id,  # Usando user_id como ev_id para PnC simulado
                        "id_tag_type": "ISO15118Certificate"  # Simular PnC para o CSMS
                    }
            ) as response:
                plug_in_response = await response.json()
                response.raise_for_status()  # Lança uma exceção para códigos de status HTTP 4xx/5xx

        if plug_in_response and plug_in_response.get("ocpp_response", {}).get("status") == "Accepted":
            logger.info(f"VE '{user_id}': Plug-in aceito pelo CSMS. RemoteStartTransaction enviado ao CP.")

            # Em um cenário real, o CSMS enviaria o transaction_id de volta após a confirmação do CP.
            # Aqui, vamos pegar o transactionId que o CSMS retorna (se retornar um temporário)
            # ou usar um mock para prosseguir a simulação.
            transaction_id = plug_in_response.get("transactionId")
            if not transaction_id:  # Se o CSMS não retornou um ID temporário ou real ainda
                transaction_id = f"MOCK_TRX_{user_id}_{int(time.time())}"
                logger.warning(
                    f"VE '{user_id}': CSMS não retornou transactionId imediatamente. Usando ID mock: {transaction_id}")

            logger.info(f"VE '{user_id}': Transação simulada iniciada (ID provisório/mock) {transaction_id}.")

            # 2. Simular período de carregamento
            logger.info(
                f"VE '{user_id}': Carregando por aproximadamente {charging_time_seconds} segundos (simulando {simulated_kwh_consumption:.2f} kWh)...")
            await asyncio.sleep(charging_time_seconds)

            # 3. Simular "Unplug" do VE (comunicação EV -> CSMS via API)
            logger.info(
                f"VE '{user_id}': Enviando evento de Unplug para CP '{charge_point_id}', transação {transaction_id}...")

            async with aiohttp.ClientSession() as session:
                async with session.post(
                        f"{CSMS_API_URL}/ev_events/unplug",
                        json={
                            "charge_point_id": charge_point_id,
                            "connector_id": connector_id,  # Pode ser útil para CSMS identificar o conector
                            "ev_id": user_id,
                            "transaction_id": transaction_id  # Passar o ID da transação
                        }
                ) as response:
                    unplug_response = await response.json()
                    response.raise_for_status()  # Lança uma exceção para códigos de status HTTP 4xx/5xx

            if unplug_response and unplug_response.get("ocpp_response", {}).get("status") == "Accepted":
                logger.info(f"VE '{user_id}': Unplug aceito pelo CSMS. RemoteStopTransaction enviado ao CP.")
                logger.info(
                    f"VE '{user_id}': Transação {transaction_id} concluída. kWh simulados: {simulated_kwh_consumption:.2f}.")
            else:
                logger.error(
                    f"VE '{user_id}': Não foi possível parar a transação {transaction_id}. Resposta: {unplug_response}")

        else:
            logger.error(
                f"VE '{user_id}': Não foi possível iniciar a transação para CP '{charge_point_id}'. Resposta: {plug_in_response}")

    except aiohttp.ClientError as e:  # Captura erros de requisição aiohttp
        logger.error(f"VE '{user_id}': Erro de comunicação com a API do CSMS: {e}")
    except Exception as e:
        logger.error(f"VE '{user_id}': Um erro inesperado ocorreu durante a simulação: {e}", exc_info=True)
    finally:
        logger.info(f"-------------------------------------------------------")


if __name__ == '__main__':
    async def main_ev_sim():
        logger.info("Iniciando simuladores de Veículos Elétricos dinamicamente...")

        # Lista de CPs e conectores disponíveis (idealmente viria de uma API do CSMS)
        # Para fins de simulação, vamos usar os CPs e conectores que sabemos que existem
        cps_and_connectors = [
            ("CP-SIGEC-001", 1), ("CP-SIGEC-001", 2),
            ("CP-SIGEC-002", 1), ("CP-SIGEC-002", 2)
        ]
        users = [f"User-EV-{i:03d}" for i in range(1, 16)]  # 15 usuários simulados, mais dinâmico

        tasks = []
        num_simulations = 30  # Número total de sessões de carregamento a simular

        for i in range(num_simulations):
            cp_id, conn_id = random.choice(cps_and_connectors)
            user_id = random.choice(users)

            # Introduzir um pequeno atraso aleatório antes de iniciar cada sessão
            await asyncio.sleep(random.uniform(0.5, 3.0))  # Atraso de 0.5 a 3 segundos

            tasks.append(asyncio.create_task(
                simulate_ev_charging_session(cp_id, conn_id, user_id)
            ))

        await asyncio.gather(*tasks)
        logger.info(f"Todas as {num_simulations} simulações de Veículos Elétricos foram concluídas.")


    asyncio.run(main_ev_sim())