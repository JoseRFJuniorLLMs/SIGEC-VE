# ev_charging_system/data/database.py

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import OperationalError
import logging

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configuração do Banco de Dados ---
# A DATABASE_URL será lida das variáveis de ambiente.
# No Docker Compose, ela será definida como:
# DATABASE_URL: postgresql://sigec_user:sua_senha_segura@db:5432/sigec_ve_database
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    logger.error("DATABASE_URL environment variable not set. Please set it to connect to the PostgreSQL database.")
    # Uma opção mais robusta seria levantar uma exceção ou parar a aplicação aqui.
    # Para desenvolvimento, podemos usar um valor padrão (NÃO para produção):
    # DATABASE_URL = "postgresql://postgres:mysecretpassword@localhost:5432/postgres"

# Cria a "engine" do SQLAlchemy. A engine é o ponto de partida para qualquer interação com o banco de dados.
# pool_pre_ping=True ajuda a manter as conexões ativas, útil em ambientes de contêiner.
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# Cria uma "SessionLocal" configurada para cada requisição.
# Cada instância de SessionLocal será uma sessão de banco de dados.
# O "autocommit=False" significa que as alterações não são persistidas automaticamente.
# O "autoflush=False" significa que as alterações não são sincronizadas automaticamente antes de uma consulta.
# O "bind=engine" conecta a sessão à nossa engine criada.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base Declarativa:
# Esta é a base para as suas classes de modelo (definidas em models/).
# Ao herdar desta Base, suas classes de modelo se tornarão tabelas no banco de dados.
Base = declarative_base()

# --- Funções Utilitárias de Conexão ---
def get_db():
    """
    Função geradora para obter uma sessão de banco de dados.
    Esta função é comumente usada em frameworks como FastAPI para gerenciamento de dependências.
    Garante que a sessão seja fechada corretamente após o uso, mesmo que ocorram erros.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def check_db_connection():
    """
    Tenta se conectar ao banco de dados para verificar se a conexão está funcionando.
    Útil para verificações de saúde da aplicação (health checks).
    """
    try:
        with engine.connect() as connection:
            connection.execute("SELECT 1")
        logger.info("Database connection successful!")
        return True
    except OperationalError as e:
        logger.error(f"Database connection failed: {e}")
        return False
    except Exception as e:
        logger.error(f"An unexpected error occurred during database connection check: {e}")
        return False

# Você pode chamar check_db_connection() na inicialização da sua aplicação (em main.py)
# para garantir que o BD esteja acessível.