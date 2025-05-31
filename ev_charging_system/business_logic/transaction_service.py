# ev_charging_system/business_logic/transaction_service.py

from sqlalchemy.orm import Session
from datetime import datetime
import logging

# IMPORTANTE: Importe os modelos da sua ÚNICA FONTE DE VERDADE: ev_charging_system/data/models.py
from ev_charging_system.data.models import Transaction, ChargePoint, Connector, User
from ev_charging_system.data.repositories import TransactionRepository, ChargePointRepository, \
    UserRepository  # Certifique-se de que UserRepository é importado se for usado

logger = logging.getLogger(__name__)


class TransactionService:
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.transaction_repo = TransactionRepository(db_session)
        self.charge_point_repo = ChargePointRepository(db_session)
        self.user_repo = UserRepository(db_session)  # Adicione se o serviço de transação interage com usuários

    async def start_transaction(self, charge_point_id: str, connector_id: int, id_tag: str, meter_start: float,
                                transaction_id: str) -> Transaction:
        # Verifica se o ChargePoint e o Connector existem
        charge_point = self.charge_point_repo.get_charge_point_by_id(charge_point_id)
        if not charge_point:
            logger.error(f"Charge Point {charge_point_id} not found for transaction {transaction_id}")
            raise ValueError(f"Charge Point {charge_point_id} not found.")

        connector = self.charge_point_repo.get_connector_by_id(charge_point_id, connector_id)
        if not connector:
            logger.error(
                f"Connector {connector_id} for CP {charge_point_id} not found for transaction {transaction_id}")
            raise ValueError(f"Connector {connector_id} for Charge Point {charge_point_id} not found.")

        # Verifica se a transação já existe
        existing_transaction = self.transaction_repo.get_transaction_by_id(transaction_id)
        if existing_transaction:
            logger.warning(f"Transaction {transaction_id} already exists. Returning existing one.")
            return existing_transaction

        # Cria a nova transação
        new_transaction = Transaction(
            transaction_id=transaction_id,
            charge_point_id=charge_point_id,
            connector_id=connector_id,
            id_tag=id_tag,
            start_time=datetime.utcnow(),
            meter_start=meter_start,
            status="Charging"
        )
        self.transaction_repo.add_transaction(new_transaction)
        self.db_session.commit()
        self.db_session.refresh(new_transaction)

        # Atualiza o status do conector
        connector.status = "Charging"
        self.db_session.commit()

        logger.info(f"Transaction {transaction_id} started for CP {charge_point_id}, Connector {connector_id}")
        return new_transaction

    async def stop_transaction(self, transaction_id: str, meter_stop: float, energy_transfered: float) -> Transaction:
        transaction = self.transaction_repo.get_transaction_by_id(transaction_id)
        if not transaction:
            logger.error(f"Transaction {transaction_id} not found to stop.")
            raise ValueError(f"Transaction {transaction_id} not found.")

        transaction.stop_time = datetime.utcnow()
        transaction.meter_stop = meter_stop
        transaction.energy_transfered = energy_transfered
        transaction.status = "Completed"
        self.db_session.commit()
        self.db_session.refresh(transaction)

        # Atualiza o status do conector associado
        connector = self.charge_point_repo.get_connector_by_id(transaction.charge_point_id, transaction.connector_id)
        if connector:
            connector.status = "Available"
            self.db_session.commit()
            logger.info(f"Connector {connector.connector_id} for CP {connector.charge_point_id} set to Available.")

        logger.info(f"Transaction {transaction_id} stopped. Energy: {energy_transfered} kWh.")
        return transaction