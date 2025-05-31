# D:\dev\SIGEC-VE\pythonProject\ev_charging_system\tests\conftest.py

import pytest
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, clear_mappers, Session
from sqlalchemy.exc import OperationalError
from sqlalchemy import text  # Necessário para db.execute(text("SELECT 1"))

# IMPORTANT: Import ALL your models here to ensure Pytest loads them.
# This ensures that Base.metadata is populated correctly.
from ev_charging_system.data.models import Base, ChargePoint, Connector, Transaction, User  # Added User
from ev_charging_system.data.database import SessionLocal as AppSessionLocal


# --- Test Database Engine Fixture (Session Scope) ---
@pytest.fixture(scope="session")
def db_engine():
    # Usando SQLite em memória para testes, para isolamento completo
    engine = create_engine("sqlite:///:memory:")

    print("\n--- Configuring SQLAlchemy for Tests ---")

    # Crucial para prevenir "Table is already defined" errors em pytest.
    # Limpa mapeadores e definições de tabela existentes da MetaData.
    clear_mappers()
    Base.metadata.clear()

    # Agora, cria as tabelas. Como metadata está limpa, não haverá colisão.
    # Base.metadata deve agora estar populada pela importação de models.py no topo.
    Base.metadata.create_all(engine)
    print("--- Tables created ---")

    yield engine  # Provides the engine for the test session

    # Cleanup after all tests in the session
    print("--- Destroying Tables and Clearing Mappers ---")
    Base.metadata.drop_all(engine)
    clear_mappers()
    Base.metadata.clear()  # Clear metadata again for the next test run (if any)


# --- Database Session Fixture (Function Scope) ---
@pytest.fixture(scope="function")
def db_session(db_engine):
    """
    Provides an isolated database session for each test.
    Changes are rolled back after each test.
    """
    connection = db_engine.connect()
    transaction = connection.begin()

    session = AppSessionLocal(bind=connection)

    # --- POPULANDO TEST DATA (before each test) ---
    print("\n--- Populating test data ---")

    # Example test user
    user1 = User(
        user_id="USER-TEST-001",
        name="Test User",
        email="test@example.com",
        id_tag="TAG-TEST-001"
    )
    session.add(user1)
    session.flush()  # Flush to ensure user1.id is available if needed

    cp1 = ChargePoint(
        charge_point_id="CP-TEST-001",
        status="Available",
        vendor="TestVendor",
        model="TestModel",
        num_connectors=2
    )
    session.add(cp1)
    session.flush()

    conn1 = Connector(
        charge_point_id=cp1.charge_point_id,
        connector_id=1,
        status="Available"
    )
    conn2 = Connector(
        charge_point_id=cp1.charge_point_id,
        connector_id=2,
        status="Available"
    )
    session.add_all([conn1, conn2])
    session.flush()

    tx1 = Transaction(
        transaction_id="TX-TEST-001",
        charge_point_id=cp1.charge_point_id,
        connector_id=1,
        id_tag="TAG-TEST-001",  # Using the user's id_tag
        meter_start=100.0,
        status="Charging"
    )
    session.add(tx1)

    session.commit()
    print("--- Test data populated and committed ---")

    yield session

    print("--- Reverting changes and closing session ---")
    session.close()
    transaction.rollback()
    connection.close()


# --- Overriding 'get_db' Fixture for Tests ---
@pytest.fixture
def mock_get_db(db_session: Session):
    """
    Fixture that simulates the FastAPI get_db dependency,
    using the test session from db_session.
    """

    def _override_get_db():
        yield db_session

    return _override_get_db


# --- Example Test to Verify Model Mapping and Data Population ---
def test_sqlalchemy_model_mapping(db_session: Session):
    """
    A simple test to verify that data and mapping are correct.
    """
    cp = db_session.query(ChargePoint).filter_by(charge_point_id="CP-TEST-001").first()
    assert cp is not None
    assert cp.status == "Available"
    print(f"DEBUG: ChargePoint '{cp.charge_point_id}' found.")

    assert len(cp.transactions) == 1
    assert cp.transactions[0].transaction_id == "TX-TEST-001"
    print(f"DEBUG: Transaction '{cp.transactions[0].transaction_id}' found for '{cp.charge_point_id}'.")

    assert len(cp.connectors) == 2
    print(f"DEBUG: {len(cp.connectors)} connectors found for '{cp.charge_point_id}'.")

    tx = db_session.query(Transaction).filter_by(transaction_id="TX-TEST-001").first()
    assert tx is not None
    assert tx.charge_point.charge_point_id == "CP-TEST-001"
    print(f"DEBUG: Transaction '{tx.transaction_id}' points to ChargePoint '{tx.charge_point.charge_point_id}'.")

    user = db_session.query(User).filter_by(user_id="USER-TEST-001").first()
    assert user is not None
    assert user.email == "test@example.com"
    print(f"DEBUG: User '{user.name}' found.")