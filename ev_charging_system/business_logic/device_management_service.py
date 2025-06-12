# ev_charging_system/business_logic/device_management_service.py

import logging
from typing import Optional, List
from sqlalchemy.orm import Session

from ev_charging_system.data.models import ChargePoint, Transaction, User
from ev_charging_system.data.repositories import ChargePointRepository, TransactionRepository, UserRepository

logger = logging.getLogger(__name__)


class DeviceManagementService:
    def __init__(self, cp_repo: ChargePointRepository, trx_repo: TransactionRepository, user_repo: UserRepository):
        self.charge_point_repo = cp_repo
        self.transaction_repo = trx_repo
        self.user_repo = user_repo
        # O serviço agora pode aceder à sessão do DB através de qualquer um dos repositórios
        self.db = cp_repo.db

    # --- Charge Point Management ---

    def register_charge_point(self, charge_point_id: str, vendor_name: str, model: str) -> ChargePoint:
        if self.charge_point_repo.get_charge_point_by_id(charge_point_id):
            raise ValueError(f"Charge Point {charge_point_id} already exists")

        charge_point = ChargePoint(
            charge_point_id=charge_point_id,
            vendor_name=vendor_name,
            model=model,
            status="Offline"
        )
        self.charge_point_repo.add_charge_point(charge_point)
        self.db.commit()  # O serviço agora faz o commit
        self.db.refresh(charge_point)  # E o refresh
        return charge_point

    def get_all_charge_points(self) -> List[ChargePoint]:
        return self.charge_point_repo.get_all_charge_points()

    def get_charge_point_by_id(self, charge_point_id: str) -> Optional[ChargePoint]:
        return self.charge_point_repo.get_charge_point_by_id(charge_point_id)

    # --- Transaction Management ---

    def get_all_transactions(self) -> List[Transaction]:
        return self.transaction_repo.get_all_transactions()

    def get_transaction_by_id(self, transaction_id: str) -> Optional[Transaction]:
        return self.transaction_repo.get_transaction_by_id(transaction_id)

    # --- User Management ---

    def create_user(self, user_id: str, name: str, email: str, phone: Optional[str], id_tag: Optional[str],
                    is_active: bool) -> User:
        if self.user_repo.get_user_by_id(user_id) or self.user_repo.get_user_by_email(email):
            raise ValueError("User with this ID or email already exists.")

        new_user = User(
            user_id=user_id,
            name=name,
            email=email,
            phone=phone,
            id_tag=id_tag,
            is_active=is_active
        )
        self.user_repo.add_user(new_user)
        self.db.commit()  # O serviço agora faz o commit
        self.db.refresh(new_user)  # E o refresh
        return new_user

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        return self.user_repo.get_user_by_id(user_id)