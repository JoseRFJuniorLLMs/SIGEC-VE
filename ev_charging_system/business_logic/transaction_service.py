# ev_charging_system/business_logic/transaction_service.py

from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional, List

from ev_charging_system.data.repositories import TransactionRepository, UserRepository, ChargePointRepository
from ev_charging_system.models.transaction import Transaction
from ev_charging_system.models.user import User
from ev_charging_system.models.charge_point import ChargePointConnector, ChargePoint # Adicionado ChargePoint se for necessário obter detalhes do CP diretamente
from ocpp.v16.enums import ChargePointStatus # Para possíveis atualizações de status

# --- INÍCIO DA CORREÇÃO ---
# MUDANÇA CRÍTICA AQUI:
# Importe 'send_ocpp_command_to_cp' do novo módulo 'ocpp_central_manager',
# não mais de 'ocpp_server'.
from ev_charging_system.core.ocpp_central_manager import send_ocpp_command_to_cp

# Você também pode precisar de 'connected_charge_points' se a lógica do serviço precisar de acesso direto
# from ev_charging_system.core.ocpp_central_manager import connected_charge_points
# --- FIM DA CORREÇÃO ---

import logging
logger = logging.getLogger(__name__)


class TransactionService:
    def __init__(self, db: Session):
        self.db = db
        self.transaction_repo = TransactionRepository(db)
        self.user_repo = UserRepository(db)
        self.charge_point_repo = ChargePointRepository(db) # Para obter detalhes de conectores e CPs

    async def start_transaction(
        self,
        charge_point_id: str,
        connector_id: int,
        id_tag: str,
        meter_start: float,
        timestamp: datetime
    ) -> Optional[Transaction]:
        """
        Inicia uma nova transação de carga.
        Verifica o usuário, o estado do conector e registra a transação.
        """
        logger.info(f"Attempting to start transaction for CP: {charge_point_id}, Connector: {connector_id}, ID Tag: {id_tag}")

        user = self.user_repo.get_user_by_auth_tag(id_tag)
        if not user:
            logger.warning(f"ID Tag {id_tag} not found or not authorized to start transaction.")
            # No mundo real, você poderia lançar uma HTTPException ou retornar um status específico para o CSMS
            return None

        # Obter o conector para garantir que ele exista e obter seu ID de DB
        connector = self.charge_point_repo.get_connector_by_id(connector_id, charge_point_id)
        if not connector:
            logger.error(f"Connector {connector_id} not found for CP {charge_point_id}. Cannot start transaction.")
            return None

        # Gerar um ID de transação. Em um sistema real, seria mais robusto,
        # talvez vindo do CP no StartTransaction.req ou um UUID.
        transaction_id = f"TRX-{charge_point_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{connector_id}"

        new_transaction = Transaction(
            id=transaction_id,
            charge_point_id=charge_point_id,
            connector_id=connector.id, # Usar o ID do conector do modelo
            user_id=user.id,
            start_time=timestamp,
            start_meter_value=meter_start,
            status="Charging"
        )
        created_transaction = self.transaction_repo.create_transaction(new_transaction)
        logger.info(f"Transaction {created_transaction.id} started successfully for user {user.id} on CP {charge_point_id}.")

        # Nota: A atualização do status do conector para "Charging" é geralmente feita
        # pelo Charge Point via StatusNotification após o StartTransaction.conf.
        # Se você quiser que o CSMS reflita o estado imediatamente, você precisaria do DeviceManagementService aqui.
        # from ev_charging_system.business_logic.device_management_service import DeviceManagementService
        # device_service = DeviceManagementService(self.db)
        # device_service.update_connector_status(charge_point_id, connector_id, ChargePointStatus.Charging.value, transaction_id)

        return created_transaction

    async def stop_transaction(
        self,
        transaction_id: str,
        meter_stop: float,
        timestamp: datetime,
        reason: Optional[str] = None
    ) -> Optional[Transaction]:
        """
        Para uma transação de carga existente e atualiza seus detalhes.
        """
        logger.info(f"Attempting to stop transaction: {transaction_id}")

        transaction = self.transaction_repo.get_transaction_by_id(transaction_id)
        if not transaction:
            logger.warning(f"Transaction {transaction_id} not found.")
            return None

        transaction.end_time = timestamp
        transaction.end_meter_value = meter_stop
        transaction.total_energy_kwh = meter_stop - transaction.start_meter_value
        transaction.status = "Finished"
        transaction.stop_reason = reason

        updated_transaction = self.transaction_repo.update_transaction(transaction)
        logger.info(f"Transaction {updated_transaction.id} stopped successfully. Energy: {updated_transaction.total_energy_kwh:.2f} kWh.")

        # Nota: A atualização do status do conector de volta para "Available" é feita
        # pelo Charge Point via StatusNotification após o StopTransaction.conf.
        # Se quiser pré-atualizar, use o DeviceManagementService aqui.
        # from ev_charging_system.business_logic.device_management_service import DeviceManagementService
        # device_service = DeviceManagementService(self.db)
        # device_service.update_connector_status(transaction.charge_point_id, transaction.connector_id, ChargePointStatus.Available.value, None)

        return updated_transaction

    async def remote_stop_transaction_via_ocpp(self, charge_point_id: str, transaction_id: str) -> bool:
        """
        Envia um comando RemoteStopTransaction para o Charge Point.
        """
        logger.info(f"Sending RemoteStopTransaction to CP {charge_point_id} for transaction {transaction_id}")
        payload = {"transactionId": transaction_id}
        success = await send_ocpp_command_to_cp(charge_point_id, "RemoteStopTransaction", payload)
        if not success:
            logger.error(f"Failed to send RemoteStopTransaction command to CP {charge_point_id}.")
        return success

    def get_transaction_details(self, transaction_id: str) -> Optional[Transaction]:
        """Retorna os detalhes de uma transação pelo seu ID."""
        return self.transaction_repo.get_transaction_by_id(transaction_id)

    def get_transactions_by_user_id(self, user_id: str) -> List[Transaction]:
        """Lista todas as transações para um determinado usuário."""
        return self.transaction_repo.get_transactions_by_user_id(user_id)

    def get_transactions_by_charge_point_id(self, cp_id: str) -> List[Transaction]:
        """Lista todas as transações para um determinado Charge Point."""
        return self.transaction_repo.get_transactions_by_charge_point_id(cp_id)