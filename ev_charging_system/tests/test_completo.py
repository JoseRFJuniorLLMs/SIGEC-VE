# ev_charging_system/tests/test_completo.py

import asyncio
import requests
import websockets
import logging
import random  # Adicionado para test_ev_charging_flow
from datetime import datetime

# Importações do seu projeto
# MUDANÇA AQUI: Corrigindo o caminho de importação para ser absoluto dentro do pacote
from ev_charging_system.data.database import check_db_connection
from ocpp.v16.enums import RemoteStartStopStatus, ChargePointStatus  # Adicionado ChargePointStatus

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('teste-completo')

# URLs dos serviços
CSMS_API_URL = "http://localhost:8001/api"  # Caminho base para a API RESTful
OCPP_SERVER_URL = "ws://localhost:9000"  # URL base para o servidor WebSocket OCPP


async def test_db_connection():
    logger.info("--- Testando Conexão com o Banco de Dados ---")
    if check_db_connection():
        logger.info("Teste de Banco de Dados: SUCESSO! Conexão com o DB estabelecida.")
        return True
    else:
        logger.error("Teste de Banco de Dados: FALHA! Não foi possível conectar ao DB.")
        return False


async def test_fastapi_api():
    logger.info("--- Testando API RESTful do FastAPI ---")
    health_url = f"{CSMS_API_URL}/health"  # Endpoint de saúde da sua API

    try:
        response = requests.get(health_url, timeout=5)
        if response.status_code == 200:
            logger.info(
                f"Teste da API FastAPI: SUCESSO! Status: {response.status_code} ({response.json()}) em {health_url}.")
            return True
        else:
            logger.error(
                f"Teste da API FastAPI: FALHA! Status inesperado: {response.status_code} ({response.text}) em {health_url}.")
            return False
    except requests.exceptions.ConnectionError:
        logger.error(
            f"Teste da API FastAPI: FALHA! Não foi possível conectar à API em {health_url}. Certifique-se de que o serviço está rodando.")
        return False
    except requests.exceptions.Timeout:
        logger.error(f"Teste da API FastAPI: FALHA! Tempo limite excedido ao conectar à API em {health_url}.")
        return False
    except Exception as e:
        logger.error(f"Teste da API FastAPI: FALHA! Ocorreu um erro inesperado: {e}", exc_info=True)
        return False


async def test_ocpp_websocket_server():
    logger.info("--- Testando Servidor WebSocket OCPP ---")
    uri = OCPP_SERVER_URL  # URL base para o teste de conexão.

    try:
        # Removido 'timeout=5' para compatibilidade com versões mais antigas/específicas do websockets
        async with websockets.connect(uri) as websocket:
            logger.info(f"Conectado ao servidor OCPP em {uri} com sucesso.")
            # Opcional: enviar um ping/pong para teste básico de comunicação
            # await websocket.ping()
            # await websocket.pong()
            logger.info("Teste de conexão WebSocket OCPP: SUCESSO!")
            return True
    # Alterado para websockets.exceptions.ConnectionClosed
    except websockets.exceptions.ConnectionClosed as e:
        logger.error(f"Teste de conexão WebSocket OCPP: FALHA! Conexão recusada ou fechada. Erro: {e}")
    except Exception as e:
        logger.error(f"Teste de conexão WebSocket OCPP: FALHA! Erro inesperado: {e}", exc_info=True)
        return False  # Garantir que retorna False em caso de erro inesperado
    return False  # Retorna False se não houver sucesso


async def test_ev_charging_flow():
    logger.info("--- Testando Fluxo de Carregamento de VE via API ---")

    test_cp_id = "CP-SIGEC-TEST"
    test_connector_id = 1
    test_user_id = "test-user-001"

    # 1. Criar um usuário de teste (se não existir)
    user_payload = {
        "id": test_user_id,
        "auth_tag": "TESTTAG123",
        "name": "Test User",
        "email": f"{test_user_id}@example.com"
    }
    try:
        user_response = requests.post(f"{CSMS_API_URL}/users", json=user_payload, timeout=5)
        if user_response.status_code == 201:
            logger.info(f"Usuário de teste '{test_user_id}' criado com sucesso.")
        elif user_response.status_code == 409:  # Conflito, usuário já existe
            logger.info(f"Usuário de teste '{test_user_id}' já existe.")
        else:
            logger.error(
                f"Falha ao criar/verificar usuário de teste: {user_response.status_code} - {user_response.text}")
            return False
    except Exception as e:
        logger.error(f"Erro ao tentar criar/verificar usuário de teste: {e}")
        return False

    # 2. Iniciar uma transação
    start_payload = {
        "charge_point_id": test_cp_id,
        "connector_id": test_connector_id,
        "id_tag": test_user_id
    }
    transaction_id = None
    try:
        start_response = requests.post(f"{CSMS_API_URL}/transactions/start", json=start_payload, timeout=5)
        start_data = start_response.json()

        if start_response.status_code == 200 and start_data.get("status") == "pending_cp_response":
            logger.info(f"Requisição de início de transação enviada ao CSMS. Status: {start_data.get('status')}")
            await asyncio.sleep(5)  # Damos um tempo para o CP responder

            cp_details_response = requests.get(f"{CSMS_API_URL}/charge_points/{test_cp_id}", timeout=5)
            if cp_details_response.status_code == 200:
                cp_details = cp_details_response.json()
                connector_info = next((c for c in cp_details.get('connectors', []) if c['id'] == test_connector_id),
                                      None)
                if connector_info and connector_info[
                    'status'] == ChargePointStatus.Charging.value:  # .value para comparar string
                    transaction_id = connector_info['current_transaction_id']  # Pega o ID da transação atual
                    logger.info(
                        f"Transação {transaction_id} para CP '{test_cp_id}' Conector {test_connector_id} iniciada e em 'Charging'.")
                else:
                    logger.error(
                        f"Conector {test_connector_id} no CP {test_cp_id} não está em 'Charging' ou não tem transação. Status: {connector_info.get('status') if connector_info else 'N/A'}")
                    return False
            else:
                logger.error(
                    f"Falha ao obter detalhes do CP {test_cp_id}: {cp_details_response.status_code} - {cp_details_response.text}")
                return False
        else:
            logger.error(f"Falha ao iniciar transação: {start_response.status_code} - {start_data}")
            return False

    except Exception as e:
        logger.error(f"Erro ao iniciar transação de teste: {e}", exc_info=True)
        return False

    if not transaction_id:
        logger.error("Não foi possível obter o ID da transação para prosseguir com a parada.")
        return False

    # 3. Parar uma transação
    stop_payload = {
        "charge_point_id": test_cp_id,
        "transaction_id": transaction_id,  # Usando o ID da transação obtido
        "meter_stop": random.uniform(1.0, 10.0),  # Valor aleatório para kWh
        "reason": "TestFinished"
    }
    try:
        stop_response = requests.post(f"{CSMS_API_URL}/transactions/stop", json=stop_payload, timeout=5)
        stop_data = stop_response.json()

        if stop_response.status_code == 200 and stop_data.get("status") == "pending_cp_response":
            logger.info(
                f"Requisição de parada de transação {transaction_id} enviada ao CSMS. Status: {stop_data.get('status')}")
            await asyncio.sleep(5)  # Tempo para o CP responder

            # Verificar se a transação foi finalizada no CSMS
            transaction_details_response = requests.get(f"{CSMS_API_URL}/transactions/{transaction_id}", timeout=5)
            if transaction_details_response.status_code == 200:
                tx_details = transaction_details_response.json()
                if tx_details['status'] == 'Finished' and tx_details['end_meter_value'] is not None:
                    logger.info(f"Transação {transaction_id} finalizada com sucesso no CSMS.")
                    return True
                else:
                    logger.error(
                        f"Transação {transaction_id} não finalizada corretamente. Status: {tx_details.get('status')}")
                    return False
            else:
                logger.error(
                    f"Falha ao obter detalhes da transação {transaction_id}: {transaction_details_response.status_code} - {transaction_details_response.text}")
                return False
        else:
            logger.error(f"Falha ao parar transação: {stop_response.status_code} - {stop_data}")
            return False

    except Exception as e:
        logger.error(f"Erro ao parar transação de teste: {e}", exc_info=True)
        return False


async def main():
    logger.info("-------------------------------------------------------")
    logger.info("Iniciando Teste Completo dos Serviços do CSMS...")
    logger.info("-------------------------------------------------------")
    logger.info("POR FAVOR, CERTIFIQUE-SE DE QUE 'docker-compose up app db' ESTÁ RODANDO")
    logger.info("EM UM TERMINAL SEPARADO ANTES DE EXECUTAR ESTE SCRIPT.")
    logger.info("-------------------------------------------------------")

    overall_success = True

    # Testar Conexão com o DB
    if not await test_db_connection():
        overall_success = False

    # Testar API RESTful
    if not await test_fastapi_api():
        overall_success = False

    # Testar Servidor WebSocket OCPP
    if not await test_ocpp_websocket_server():
        overall_success = False

    # Testar fluxo completo de carregamento (depende dos serviços estarem de pé)
    logger.info("--- Testando Fluxo Completo de Carregamento (Simulação EV) ---")
    logger.info("Este teste requer que 'charge_point_simulator.py' esteja rodando em outro terminal.")
    if await test_ev_charging_flow():
        logger.info("Teste de Fluxo de Carregamento: SUCESSO!")
    else:
        logger.error("Teste de Fluxo de Carregamento: FALHA!")
        overall_success = False

    logger.info("-------------------------------------------------------")
    if overall_success:
        logger.info("TESTE COMPLETO: SUCESSO! Todos os componentes básicos estão funcionando.")
    else:
        logger.error("TESTE COMPLETO: FALHA! Alguns componentes não estão funcionando como esperado.")
    logger.info("-------------------------------------------------------")


if __name__ == '__main__':
    asyncio.run(main())