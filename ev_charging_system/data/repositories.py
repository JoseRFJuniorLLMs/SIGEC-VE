# ev_charging_system/data/repositories.py

from sqlalchemy.orm import Session
from typing import List, Optional

# Importa os modelos que você acabou de definir e ajustar
from ev_charging_system.models.charge_point import ChargePoint, ChargePointConnector
from ev_charging_system.models.user import User
from ev_charging_system.models.transaction import Transaction

# --- Repositório de ChargePoint ---
class ChargePointRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_charge_point_by_id(self, cp_id: str) -> Optional[ChargePoint]:
        return self.db.query(ChargePoint).filter(ChargePoint.id == cp_id).first()

    def create_charge_point(self, cp: ChargePoint) -> ChargePoint:
        self.db.add(cp)
        self.db.commit()
        self.db.refresh(cp)
        return cp

    def update_charge_point(self, cp: ChargePoint) -> ChargePoint:
        # Apenas commitamos as alterações se o objeto já estiver na sessão
        self.db.add(cp) # Garante que o objeto está sendo rastreado pela sessão
        self.db.commit()
        self.db.refresh(cp)
        return cp

    def get_all_charge_points(self) -> List[ChargePoint]:
        return self.db.query(ChargePoint).all()

    # Repositório de Conector (pode ser separado ou parte do ChargePointRepository)
    def get_connector_by_id(self, connector_id: int, cp_id: str) -> Optional[ChargePointConnector]:
        return self.db.query(ChargePointConnector).filter(
            ChargePointConnector.id == connector_id,
            ChargePointConnector.charge_point_id == cp_id
        ).first()

    def create_connector(self, connector: ChargePointConnector) -> ChargePointConnector:
        self.db.add(connector)
        self.db.commit()
        self.db.refresh(connector)
        return connector

    def update_connector(self, connector: ChargePointConnector) -> ChargePointConnector:
        self.db.add(connector)
        self.db.commit()
        self.db.refresh(connector)
        return connector

# --- Repositório de Usuário ---
class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()

    def get_user_by_auth_tag(self, auth_tag: str) -> Optional[User]:
        return self.db.query(User).filter(User.auth_tag == auth_tag).first()

    def create_user(self, user: User) -> User:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update_user(self, user: User) -> User:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

# --- Repositório de Transação ---
class TransactionRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_transaction_by_id(self, transaction_id: str) -> Optional[Transaction]:
        return self.db.query(Transaction).filter(Transaction.id == transaction_id).first()

    def create_transaction(self, transaction: Transaction) -> Transaction:
        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(transaction)
        return transaction

    def update_transaction(self, transaction: Transaction) -> Transaction:
        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(transaction)
        return transaction

    def get_transactions_by_user_id(self, user_id: str) -> List[Transaction]:
        return self.db.query(Transaction).filter(Transaction.user_id == user_id).all()

    def get_transactions_by_charge_point_id(self, cp_id: str) -> List[Transaction]:
        return self.db.query(Transaction).filter(Transaction.charge_point_id == cp_id).all()