# main.py

import asyncio
import logging
import os
from contextlib import asynccontextmanager

# Importa a função de verificação e criação de tabelas do seu database.py
from ev_charging_system.data.database import check_db_connection, Base, engine
# Importa as classes de modelo para que o SQLAlchemy as conheça
import ev_charging_system.models.charge_point
import ev_charging_system.models.user
import ev_charging_system.models.transaction

# Importa a função para iniciar o servidor OCPP
from ev_charging_system.core.ocpp_server import start_ocpp_server

# Configuração de logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Variáveis de Ambiente ---
# Definimos portas padrão, mas é bom pegar de variáveis de ambiente para flexibilidade
OCPP_SERVER_PORT = int(os.getenv("OCPP_SERVER_PORT", 9000))
OCPP_SERVER_HOST = os.getenv("OCPP_SERVER_HOST", "0.0.0.0") # Escuta em todas as interfaces
FASTAPI_PORT = int(os.getenv("FASTAPI_PORT", 8001)) # Porta da API REST
LLM_CONNECTOR_PORT = int(os.getenv("LLM_CONNECTOR_PORT", 8000)) # Porta do conector LLM

# --- Funções de Setup ---

def create_db_tables():
    """
    Cria as tabelas do banco de dados com base nos modelos SQLAlchemy.
    Isso só deve ser feito uma vez na inicialização ou via migrações.
    """
    logger.info("Attempting to create database tables...")
    # Base.metadata.create_all() cria tabelas para todos os modelos que herdam de Base
    # apenas se as tabelas ainda não existirem.
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created (or already exist).")

@asynccontextmanager
async def lifespan(app):
    """
    Função de ciclo de vida para a aplicação FastAPI.
    Executa tarefas de inicialização antes da aplicação iniciar e tarefas de limpeza no desligamento.
    """
    logger.info("Starting up application services...")

    # 1. Verificar conexão com o Banco de Dados
    if not check_db_connection():
        logger.critical("Failed to connect to the database. Exiting.")
        # Em um ambiente de produção, você pode querer lançar uma exceção ou ter uma lógica de retry.
        # Por enquanto, apenas logamos o erro crítico.
        # sys.exit(1) # Descomente se quiser forçar a saída em caso de falha no BD

    # 2. Criar Tabelas do Banco de Dados
    create_db_tables()

    # 3. Iniciar Servidor OCPP em uma tarefa separada (background task)
    logger.info(f"Initializing OCPP Server on {OCPP_SERVER_HOST}:{OCPP_SERVER_PORT}...")
    # Usamos asyncio.create_task para rodar o servidor OCPP em paralelo com o FastAPI
    ocpp_task = asyncio.create_task(start_ocpp_server(OCPP_SERVER_HOST, OCPP_SERVER_PORT))

    # yield para que o FastAPI (e outros serviços) possam iniciar
    yield

    # Tarefas de limpeza no desligamento da aplicação
    logger.info("Shutting down application services...")
    # Cancelar a tarefa do servidor OCPP ao desligar
    ocpp_task.cancel()
    try:
        await ocpp_task  # Esperar que a tarefa seja cancelada e finalize
    except asyncio.CancelledError:
        logger.info("OCPP Server task cancelled successfully.")

# --- Inicialização da Aplicação ---
# Este é o ponto de entrada principal do script
if __name__ == "__main__":
    # IMPORTANTE: A importação e inicialização do FastAPI/Uvicorn virá aqui quando você
    # implementar a camada 'api/'. Por enquanto, vamos testar apenas o OCPP.

    # Para testar apenas o OCPP server (sem FastAPI ainda)
    # Você pode rodar este script diretamente: `python main.py`
    # E os logs mostrarão o servidor OCPP iniciando.
    logger.info("Starting SIGEC-VE (OCPP Server only for now)...")
    asyncio.run(start_ocpp_server(OCPP_SERVER_HOST, OCPP_SERVER_PORT))

    logger.info("SIGEC-VE application finished.")

# --- Como Rodar a Aplicação Completa com FastAPI (Futuro) ---
# Quando você implementar a camada 'api/', você usará o Uvicorn para iniciar a aplicação FastAPI,
# e o 'lifespan' cuidará da inicialização do OCPP Server.

# Exemplo de como seria o 'main.py' completo com FastAPI:
"""
from fastapi import FastAPI
from ev_charging_system.api.rest_api import router as rest_api_router # Importa seu router
# from ev_charging_system.llm_integration.google_llm_connector import router as llm_router # Se o LLM tiver sua própria API
import uvicorn

app = FastAPI(lifespan=lifespan, title="SIGEC-VE CSMS", version="0.1.0")

# Adicionar routers para a API REST e LLM Connector
app.include_router(rest_api_router, prefix="/api")
# app.include_router(llm_router, prefix="/llm") # Se o LLM tiver sua própria API

if __name__ == "__main__":
    # Não chamamos start_ocpp_server ou create_db_tables diretamente aqui,
    # pois o 'lifespan' do FastAPI cuidará disso.
    uvicorn.run(app, host="0.0.0.0", port=FASTAPI_PORT)
    # Note: O servidor LLM Connector pode rodar em uma porta diferente se for um serviço separado
    # uvicorn.run(llm_connector_app, host="0.0.0.0", port=LLM_CONNECTOR_PORT)
"""