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
# --- NOVO: Importa a função para iniciar o servidor MCP ---
from ev_charging_system.llm_integration.mcp_server import start_mcp_server #

# --- NOVO: Importa FastAPI e uvicorn para a API REST ---
from fastapi import FastAPI #
import uvicorn #
from ev_charging_system.api.rest_api import router as rest_api_router # Assumindo que este router existe e é importado assim

# Configuração de logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Variáveis de Ambiente ---
OCPP_SERVER_PORT = int(os.getenv("OCPP_SERVER_PORT", 9000))
OCPP_SERVER_HOST = os.getenv("OCPP_SERVER_HOST", "0.0.0.0")
FASTAPI_PORT = int(os.getenv("FASTAPI_PORT", 8001))
LLM_CONNECTOR_PORT = int(os.getenv("LLM_CONNECTOR_PORT", 8000)) # Porta do conector LLM

# --- Funções de Setup ---

def create_db_tables():
    logger.info("Attempting to create database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created (or already exist).")

@asynccontextmanager
async def lifespan(app: FastAPI): # Adicionado o tipo para 'app'
    logger.info("Starting up application services...")

    # 1. Verificar conexão com o Banco de Dados
    if not check_db_connection():
        logger.critical("Failed to connect to the database. Exiting.")

    # 2. Criar Tabelas do Banco de Dados
    create_db_tables()

    # 3. Iniciar Servidor OCPP em uma tarefa separada (background task)
    logger.info(f"Initializing OCPP Server on {OCPP_SERVER_HOST}:{OCPP_SERVER_PORT}...")
    ocpp_task = asyncio.create_task(start_ocpp_server(OCPP_SERVER_HOST, OCPP_SERVER_PORT))

    # --- NOVO: Iniciar Servidor MCP em uma tarefa separada (background task) ---
    logger.info(f"Initializing MCP Server on {OCPP_SERVER_HOST}:{LLM_CONNECTOR_PORT}...")
    mcp_task = asyncio.create_task(start_mcp_server(OCPP_SERVER_HOST, LLM_CONNECTOR_PORT)) #

    # yield para que o FastAPI (e outros serviços) possam iniciar
    yield

    # Tarefas de limpeza no desligamento da aplicação
    logger.info("Shutting down application services...")
    ocpp_task.cancel()
    mcp_task.cancel() #
    try:
        await ocpp_task
        await mcp_task  # Esperar que a tarefa do MCP seja cancelada e finalize
    except asyncio.CancelledError:
        logger.info("OCPP and MCP Server tasks cancelled successfully.")

# --- Inicialização da Aplicação FastAPI ---
# A instância do FastAPI é criada aqui, usando a função lifespan
app = FastAPI(lifespan=lifespan, title="SIGEC-VE CSMS", version="0.1.0") #

# Adicionar routers para a API REST
# Assumindo que ev_charging_system/api/rest_api.py tem um 'router' FastAPI exportado
app.include_router(rest_api_router, prefix="/api") #

if __name__ == "__main__":
    logger.info("Starting SIGEC-VE (Full Application with FastAPI, OCPP, and MCP)...")
    # Agora, o Uvicorn inicia a aplicação FastAPI, e o 'lifespan' cuida dos outros servidores.
    uvicorn.run(app, host=OCPP_SERVER_HOST, port=FASTAPI_PORT) #