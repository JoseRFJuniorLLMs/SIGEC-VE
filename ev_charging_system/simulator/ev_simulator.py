# ev_charging_system/ev_simulator.py

import requests
import time
import random
import logging
import asyncio # Necessário para rodar funções async
from datetime import datetime # Importado para obter o timestamp

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('ev_simulator')

# URL da sua API RESTful do CSMS (api/rest_api.py)
# Certifique-se que sua FastAPI está rodando na porta 8001 (ou a porta configurada no main.py)
CSMS_API_URL = "http://localhost:8001/api" # Adicionado /api prefixo como no main.py

async def simulate_ev_charging_session(charge_point_id: str, connector_id: int, user_id: str):
    """
    Simula uma sessão completa de carregamento de VE.
    Envia requisições para a API do CSMS para iniciar e parar transações.
    """
    logger.info(f"-------------------------------------------------------")
    logger.info(f"Simulando VE '{user_id}' no CP '{charge_point_id}', conector {connector_id}...")
    transaction_id = None

    try:
        # 1. Simular "Plug-in" e "Autorização" (chamando a API do CSMS para iniciar transação)
        start_payload = {
            "charge_point_id": charge_point_id,
            "connector_id": connector_id,
            "id_tag": user_id, # Usando o user_id como id_tag para simplificar
            "meter_start": random.uniform(0.0, 10.0), # Valor inicial aleatório para o medidor
            "timestamp": datetime.utcnow().isoformat() + "Z" # Hora atual em formato ISO 8601 UTC
        }
        logger.info(f"VE '{user_id}': Chamando API para iniciar transação: {start_payload}")
        start_response = requests.post(f"{CSMS_API_URL}/transactions/start", json=start_payload)
        start_data = start_response.json()

        if start_response.status_code == 200 and start_data.get("status") == "Started":
            transaction_id = start_data.get("transaction_id")
            logger.info(f"VE '{user_id}': Transação iniciada com sucesso! ID: {transaction_id}")
            logger.info(f"VE '{user_id}': Iniciando simulação de carregamento por 5-15 segundos...")

            # 2. Simular carregamento por um período de tempo
            charge_duration = random.randint(5, 15) # Carregar por 5 a 15 segundos
            await asyncio.sleep(charge_duration)

            # 3. Simular "Desconexão" (chamando a API do CSMS para parar transação)
            if transaction_id:
                stop_payload = {
                    "charge_point_id": charge_point_id,
                    "transaction_id": transaction_id,
                    "meter_stop": start_payload["meter_start"] + random.uniform(5.0, 50.0), # Valor final do medidor
                    "timestamp": datetime.utcnow().isoformat() + "Z", # Hora de parada
                    "reason": "EVDisconnected"
                }
                logger.info(f"VE '{user_id}': Chamando API para parar transação: {stop_payload}")
                stop_response = requests.post(f"{CSMS_API_URL}/transactions/stop", json=stop_payload)
                stop_data = stop_response.json()

                if stop_response.status_code == 200 and stop_data.get("status") == "Stopped":
                    logger.info(f"VE '{user_id}': Transação {transaction_id} parada com sucesso.")
                    logger.info(f"VE '{user_id}': Energia consumida: {stop_data.get('total_energy_kwh', 'N/A')} kWh")
                    logger.info(f"VE '{user_id}': Custo: {stop_data.get('cost', 'N/A')} €")
                else:
                    logger.warning(f"VE '{user_id}': Erro ou status inesperado ao parar transação {transaction_id}: {stop_data}")
            else:
                logger.warning(f"VE '{user_id}': Não foi possível parar a transação, ID da transação não disponível.")

        else:
            logger.error(f"VE '{user_id}': Não foi possível iniciar a transação para CP '{charge_point_id}'. Status: {start_data.get('status')}. Detalhes: {start_data.get('detail', 'N/A')}")

    except requests.exceptions.RequestException as e:
        logger.error(f"VE '{user_id}': Erro de comunicação com a API do CSMS: {e}")
    except Exception as e:
        logger.error(f"VE '{user_id}': Um erro inesperado ocorreu durante a simulação: {e}", exc_info=True)
    finally:
        logger.info(f"-------------------------------------------------------")


# --- Execução Principal do Simulador de VE ---
if __name__ == '__main__':
    async def main_ev_sim():
        # Simular alguns cenários de VE
        logger.info("Iniciando simuladores de Veículos Elétricos...")
        await simulate_ev_charging_session("CP-SIGEC-001", 1, "User-EV-001")
        await asyncio.sleep(3) # Pequeno intervalo entre as simulações
        await simulate_ev_charging_session("CP-SIGEC-002", 1, "User-EV-002")
        await asyncio.sleep(3)
        await simulate_ev_charging_session("CP-SIGEC-001", 2, "User-EV-003")
        logger.info("Simulações de Veículos Elétricos concluídas.")

    # Rodar a função principal assíncrona
    asyncio.run(main_ev_sim())