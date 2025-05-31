# ev_charging_system/business_logic/device_management_service.py

from sqlalchemy.orm import Session
from sqlalchemy import exc as sa_exc
from datetime import datetime

# Importe as classes de modelo diretamente do seu arquivo de modelos consolidado
from ev_charging_system.data.models import ChargePoint, Connector, Transaction, User
# Assumindo que você tem um UserRepository (se não, você precisará criá-lo)
from ev_charging_system.data.repositories import ChargePointRepository, TransactionRepository, UserRepository


class DeviceManagementService:
    """
    Serviço para gerenciar operações relacionadas a Charge Points, Conectores,
    Transações e Usuários, orquestrando a lógica de negócio entre a camada
    de comunicação (OCPP) e a persistência (repositórios).
    """

    def __init__(self,
                 charge_point_repo: ChargePointRepository,
                 transaction_repo: TransactionRepository,
                 user_repo: UserRepository
                ):
        """
        Inicializa o DeviceManagementService com os repositórios necessários.

        Args:
            charge_point_repo: O repositório para operações de ChargePoint.
            transaction_repo: O repositório para operações de Transaction.
            user_repo: O repositório para operações de User.
        """
        self.charge_point_repo = charge_point_repo
        self.transaction_repo = transaction_repo
        self.user_repo = user_repo


    # --- Métodos de Gerenciamento de ChargePoint ---

    def get_charge_point_by_id(self, cp_id: str) -> ChargePoint | None:
        """
        Busca um Charge Point pelo seu ID.
        Args: cp_id: O ID do Charge Point (ex: "CP-SIGEC-001").
        Returns: Uma instância de ChargePoint se encontrada, ou None.
        """
        return self.charge_point_repo.get_charge_point_by_id(cp_id)

    def add_charge_point(
            self,
            cp_id: str,
            vendor: str | None = None,
            model: str | None = None,
            num_connectors: int = 1,
    ) -> ChargePoint:
        """
        Adiciona um novo Charge Point ao sistema.
        Args: cp_id: O ID único do Charge Point.
              vendor: O fabricante do Charge Point.
              model: O modelo do Charge Point.
              num_connectors: Número de conectores que o Charge Point possui.
        Returns: A instância do ChargePoint recém-criado.
        Raises: ValueError: Se o Charge Point com o ID já existir.
        """
        existing_cp = self.charge_point_repo.get_charge_point_by_id(cp_id)
        if existing_cp:
            raise ValueError(f"Charge Point with ID {cp_id} already exists.")

        charge_point = ChargePoint(
            charge_point_id=cp_id,
            vendor=vendor,
            model=model,
            num_connectors=num_connectors,
            status="Online"
        )
        self.charge_point_repo.add_charge_point(charge_point)

        for i in range(1, num_connectors + 1):
            connector = Connector(
                charge_point_id=cp_id,
                connector_id=i,
                status="Available"
            )
            self.charge_point_repo.add_connector(connector)

        self.charge_point_repo.db.commit()
        return charge_point

    def update_charge_point_status(self, cp_id: str, status: str) -> bool:
        """
        Atualiza o status de um Charge Point.
        Args: cp_id: O ID do Charge Point.
              status: O novo status (ex: "Online", "Offline", "Available").
        Returns: True se a atualização for bem-sucedida, False caso contrário.
        """
        charge_point = self.charge_point_repo.get_charge_point_by_id(cp_id)
        if charge_point:
            charge_point.status = status
            self.charge_point_repo.db.commit()
            return True
        return False

    def update_charge_point_last_heartbeat(self, cp_id: str) -> bool:
        """
        Atualiza o timestamp do último heartbeat de um Charge Point.
        Args: cp_id: O ID do Charge Point.
        Returns: True se a atualização for bem-sucedida, False caso contrário.
        """
        charge_point = self.charge_point_repo.get_charge_point_by_id(cp_id)
        if charge_point:
            charge_point.last_heartbeat = datetime.utcnow()
            self.charge_point_repo.db.commit()
            return True
        return False

    # --- Métodos de Gerenciamento de Conectores ---

    def get_connector_status(self, cp_id: str, connector_id: int) -> str | None:
        """
        Obtém o status de um conector específico de um Charge Point.
        Args: cp_id: O ID do Charge Point.
              connector_id: O ID do conector.
        Returns: O status do conector se encontrado, ou None.
        """
        connector = self.charge_point_repo.get_connector_by_id(cp_id, connector_id)
        if connector:
            return connector.status
        return None

    def update_connector_status(self, cp_id: str, connector_id: int, status: str) -> bool:
        """
        Atualiza o status de um conector específico.
        Args: cp_id: O ID do Charge Point.
              connector_id: O ID do conector.
              status: O novo status (ex: "Available", "Occupied", "Charging").
        Returns: True se a atualização for bem-sucedida, False caso contrário.
        """
        connector = self.charge_point_repo.get_connector_by_id(cp_id, connector_id)
        if connector:
            connector.status = status
            self.charge_point_repo.db.commit()
            return True
        return False

    # --- Métodos de Gerenciamento de Transações ---

    def start_transaction(
            self,
            cp_id: str,
            connector_id: int,
            id_tag: str,
            meter_start: float,
            transaction_id: str,
    ) -> Transaction:
        """
        Inicia uma nova transação de carregamento.
        Args: cp_id: ID do Charge Point.
              connector_id: ID do conector.
              id_tag: ID da tag (RFID) do usuário.
              meter_start: Leitura do medidor no início da transação.
              transaction_id: ID único da transação gerado pelo CSMS.
        Returns: A instância da Transação recém-criada.
        Raises: ValueError: Se a transação com o ID já existir ou o Charge Point/Conector não for encontrado.
        """
        charge_point = self.charge_point_repo.get_charge_point_by_id(cp_id)
        if not charge_point:
            raise ValueError(f"Charge Point with ID {cp_id} not found.")

        connector = self.charge_point_repo.get_connector_by_id(cp_id, connector_id)
        if not connector:
            raise ValueError(f"Connector {connector_id} for Charge Point {cp_id} not found.")

        existing_transaction = self.transaction_repo.get_transaction_by_id(transaction_id)
        if existing_transaction:
            raise ValueError(f"Transaction with ID {transaction_id} already exists.")

        transaction = Transaction(
            transaction_id=transaction_id,
            charge_point_id=cp_id,
            connector_id=connector_id,
            id_tag=id_tag,
            start_time=datetime.utcnow(),
            meter_start=meter_start,
            status="Charging"
        )
        self.transaction_repo.add_transaction(transaction)
        self.transaction_repo.db.commit()
        self.update_connector_status(cp_id, connector_id, "Charging")
        return transaction

    def stop_transaction(
            self,
            transaction_id: str,
            meter_stop: float,
            energy_transfered: float,
    ) -> Transaction | None:
        """
        Finaliza uma transação de carregamento.
        Args: transaction_id: ID da transação a ser finalizada.
              meter_stop: Leitura do medidor no final da transação.
              energy_transfered: Energia total transferida durante a transação.
        Returns: A instância da Transação atualizada se encontrada, ou None.
        """
        transaction = self.transaction_repo.get_transaction_by_id(transaction_id)
        if transaction:
            transaction.stop_time = datetime.utcnow()
            transaction.meter_stop = meter_stop
            transaction.energy_transfered = energy_transfered
            transaction.status = "Completed"
            self.transaction_repo.db.commit()
            self.update_connector_status(transaction.charge_point_id, transaction.connector_id, "Available")
            return transaction
        return None

    # --- Métodos de Gerenciamento de Usuários (Re-incluídos) ---

    def add_user(
            self,
            user_id: str,
            name: str,
            email: str,
            id_tag: str,
            phone: str | None = None,
    ) -> User:
        """
        Adiciona um novo usuário ao sistema.
        Args: user_id: O ID único do usuário.
              name: Nome do usuário.
              email: Email do usuário (único).
              id_tag: RFID tag do usuário (único).
              phone: Telefone do usuário (opcional).
        Returns: A instância do User recém-criado.
        Raises: ValueError: Se o usuário ou id_tag/email já existirem.
        """
        if self.user_repo.get_user_by_id(user_id):
            raise ValueError(f"User with ID {user_id} already exists.")
        if self.user_repo.get_user_by_email(email):
            raise ValueError(f"User with email {email} already exists.")
        if self.user_repo.get_user_by_id_tag(id_tag):
            raise ValueError(f"User with ID tag {id_tag} already exists.")

        user = User(
            user_id=user_id,
            name=name,
            email=email,
            phone=phone,
            id_tag=id_tag
        )
        self.user_repo.add_user(user)
        self.user_repo.db.commit()
        return user

    def get_user_by_id(self, user_id: str) -> User | None:
        """
        Busca um usuário pelo seu ID.
        Args: user_id: O ID do usuário.
        Returns: Uma instância de User se encontrada, ou None.
        """
        return self.user_repo.get_user_by_id(user_id)

    def get_user_by_email(self, email: str) -> User | None:
        """
        Busca um usuário pelo seu email.
        Args: email: O email do usuário.
        Returns: Uma instância de User se encontrada, ou None.
        """
        return self.user_repo.get_user_by_email(email)

    def get_user_by_id_tag(self, id_tag: str) -> User | None:
        """
        Busca um usuário pela sua tag RFID.
        Args: id_tag: A tag RFID do usuário.
        Returns: Uma instância de User se encontrada, ou None.
        """
        return self.user_repo.get_user_by_id_tag(id_tag)

    def update_user_status(self, user_id: str, is_active: bool) -> bool:
        """
        Atualiza o status de atividade de um usuário.
        Args: user_id: O ID do usuário.
              is_active: O novo status de atividade (True para ativo, False para inativo).
        Returns: True se a atualização for bem-sucedida, False caso contrário.
        """
        user = self.user_repo.get_user_by_id(user_id)
        if user:
            user.is_active = is_active
            user.updated_at = datetime.utcnow()
            self.user_repo.db.commit()
            return True
        return False

    def delete_user(self, user_id: str) -> bool:
        """
        Remove um usuário do sistema.
        Args: user_id: O ID do usuário a ser removido.
        Returns: True se a remoção for bem-sucedida, False caso contrário.
        """
        user = self.user_repo.get_user_by_id(user_id)
        if user:
            self.user_repo.delete_user(user)
            self.user_repo.db.commit()
            return True
        return False