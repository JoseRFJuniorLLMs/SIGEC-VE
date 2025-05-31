# ev_charging_system/data/repositories.py

from sqlalchemy.orm import Session
from sqlalchemy import exc as sa_exc

# Importe os modelos da sua ÚNICA FONTE DE VERDADE: ev_charging_system/data/models.py
from ev_charging_system.data.models import ChargePoint, Connector, Transaction, User


class ChargePointRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_charge_point_by_id(self, cp_id: str) -> ChargePoint | None:
        return self.db.query(ChargePoint).filter(ChargePoint.charge_point_id == cp_id).first()

    def add_charge_point(self, charge_point: ChargePoint):
        self.db.add(charge_point)
        # self.db.commit() # Não comitar aqui, o serviço deve gerenciar o commit
        # self.db.refresh(charge_point) # Refresh também deve ser gerenciado pelo serviço se o commit não for aqui

    def get_connector_by_id(self, cp_id: str, connector_id: int) -> Connector | None:
        return self.db.query(Connector).filter(
            Connector.charge_point_id == cp_id,
            Connector.connector_id == connector_id
        ).first()

    def add_connector(self, connector: Connector):
        self.db.add(connector)
        # self.db.commit() # Não comitar aqui
        # self.db.refresh(connector) # Refresh também deve ser gerenciado pelo serviço


class TransactionRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_transaction_by_id(self, transaction_id: str) -> Transaction | None:
        return self.db.query(Transaction).filter(Transaction.transaction_id == transaction_id).first()

    def add_transaction(self, transaction: Transaction):
        self.db.add(transaction)
        # self.db.commit() # Não comitar aqui
        # self.db.refresh(transaction) # Refresh também deve ser gerenciado pelo serviço


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_user_by_id(self, user_id: str) -> User | None:
        return self.db.query(User).filter(User.user_id == user_id).first()

    def get_user_by_email(self, email: str) -> User | None:
        return self.db.query(User).filter(User.email == email).first()

    def get_user_by_id_tag(self, id_tag: str) -> User | None:
        return self.db.query(User).filter(User.id_tag == id_tag).first()

    def add_user(self, user: User):
        self.db.add(user)
        # self.db.commit() # Não comitar aqui
        # self.db.refresh(user) # Refresh também deve ser gerenciado pelo serviço

    def delete_user(self, user: User):
        self.db.delete(user)
        # self.db.commit() # Não comitar aqui