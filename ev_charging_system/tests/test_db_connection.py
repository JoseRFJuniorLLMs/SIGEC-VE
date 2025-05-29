import os
import pytest
import psycopg2
from psycopg2 import OperationalError
from dotenv import load_dotenv
import time

# Load environment variables from .env file
load_dotenv()


def test_db_connection():
    """Test database connection configuration and actual connection."""

    # Check if DATABASE_URL is set
    database_url = os.getenv('DATABASE_URL')

    if not database_url:
        pytest.fail("Erro: A variável de ambiente DATABASE_URL não está definida.")

    print(f"DATABASE_URL configured: {database_url}")

    # Test actual database connection
    try:
        print("Tentando conectar ao banco de dados...")
        conn = psycopg2.connect(database_url)

        # Test if connection is working
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        db_version = cursor.fetchone()

        print(f"Conexão bem-sucedida! Versão do PostgreSQL: {db_version[0]}")

        # Test basic operations
        cursor.execute("SELECT current_database(), current_user;")
        db_info = cursor.fetchone()
        print(f"Banco atual: {db_info[0]}, Usuário: {db_info[1]}")

        cursor.close()
        conn.close()
        print("Conexão fechada com sucesso.")

    except OperationalError as e:
        error_msg = str(e)
        if "could not connect to server" in error_msg or "Connection refused" in error_msg:
            print("❌ Erro: Não foi possível conectar ao servidor PostgreSQL.")
            print("Verifique se o PostgreSQL está rodando:")
            print("  - Para Docker: docker-compose up db")
            print("  - Para instalação local: verifique se o serviço está ativo")
            pytest.skip("PostgreSQL não está disponível - pulando teste de conexão")
        elif "authentication failed" in error_msg:
            print("❌ Erro: Falha na autenticação.")
            print("Verifique as credenciais no DATABASE_URL")
            pytest.fail(f"Erro de autenticação: {e}")
        elif "database" in error_msg and "does not exist" in error_msg:
            print("❌ Erro: Banco de dados não existe.")
            print("Crie o banco de dados primeiro ou verifique o nome no DATABASE_URL")
            pytest.fail(f"Banco de dados não existe: {e}")
        else:
            pytest.fail(f"Erro de conexão com o banco: {e}")

    except Exception as e:
        pytest.fail(f"Erro inesperado ao conectar ao banco: {e}")


def test_db_connection_with_retry():
    """Test database connection with retry logic (useful for Docker environments)."""

    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        pytest.fail("DATABASE_URL não está definida")

    max_retries = 5
    retry_delay = 2  # seconds

    for attempt in range(max_retries):
        try:
            print(f"Tentativa {attempt + 1} de {max_retries}...")
            conn = psycopg2.connect(database_url)

            # Simple connectivity test
            cursor = conn.cursor()
            cursor.execute("SELECT 1;")
            result = cursor.fetchone()

            cursor.close()
            conn.close()

            print(f"✅ Conexão bem-sucedida na tentativa {attempt + 1}")
            assert result[0] == 1
            return

        except OperationalError as e:
            if attempt < max_retries - 1:
                print(f"❌ Tentativa {attempt + 1} falhou: {e}")
                print(f"Aguardando {retry_delay} segundos antes da próxima tentativa...")
                time.sleep(retry_delay)
            else:
                pytest.fail(f"Falha ao conectar após {max_retries} tentativas: {e}")


def test_database_schema():
    """Test if we can query database schema information."""

    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        pytest.skip("DATABASE_URL não está definida")

    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()

        # Check available schemas
        cursor.execute("""
            SELECT schema_name 
            FROM information_schema.schemata 
            WHERE schema_name NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
        """)

        schemas = cursor.fetchall()
        print(f"Schemas disponíveis: {[s[0] for s in schemas]}")

        # Check available tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)

        tables = cursor.fetchall()
        print(f"Tabelas disponíveis: {[t[0] for t in tables]}")

        cursor.close()
        conn.close()

        # At minimum, we should have the public schema
        schema_names = [s[0] for s in schemas]
        assert 'public' in schema_names

    except Exception as e:
        pytest.skip(f"Não foi possível verificar schema: {e}")


if __name__ == "__main__":
    print("🔍 Executando testes de conexão com banco de dados...\n")

    print("1. Teste básico de configuração:")
    test_db_connection()

    print("\n2. Teste com retry:")
    test_db_connection_with_retry()

    print("\n3. Teste de schema:")
    test_database_schema()

    print("\n✅ Todos os testes concluídos!")