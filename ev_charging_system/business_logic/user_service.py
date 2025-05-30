# ev_charging_system/business_logic/user_service.py

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional, Dict, Any
import logging

from ev_charging_system.models.user import User # Importa o modelo User
from ev_charging_system.data.database import SessionLocal # Importa a sessão do DB, se precisar fora do FastAPI Depends

logger = logging.getLogger(__name__)

class UserService:
    def __init__(self, db: Session):
        self.db = db

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """
        Busca um usuário pelo seu ID.
        """
        logger.info(f"Buscando usuário com ID: {user_id}")
        return self.db.query(User).filter(User.id == user_id).first()

    def get_user_by_auth_tag(self, auth_tag: str) -> Optional[User]:
        """
        Busca um usuário pela sua tag de autenticação (RFID, token, etc.).
        """
        logger.info(f"Buscando usuário com auth_tag: {auth_tag}")
        return self.db.query(User).filter(User.auth_tag == auth_tag).first()

    def create_user(self, user_id: str, auth_tag: str, name: str, email: str, balance: float = 0.0) -> User:
        """
        Cria um novo usuário.
        Levanta HTTPException se o user_id ou auth_tag já existirem.
        """
        logger.info(f"Tentando criar novo usuário: {user_id}, {email}")
        db_user = User(id=user_id, auth_tag=auth_tag, name=name, email=email, balance=balance)
        try:
            self.db.add(db_user)
            self.db.commit()
            self.db.refresh(db_user)
            logger.info(f"Usuário {user_id} criado com sucesso.")
            return db_user
        except IntegrityError:
            self.db.rollback()
            logger.error(f"Erro ao criar usuário {user_id}: ID ou Auth Tag já existem.")
            # Você pode levantar uma exceção específica ou retornar None/mensagem de erro
            raise ValueError(f"User with ID '{user_id}' or Auth Tag '{auth_tag}' already exists.")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro inesperado ao criar usuário {user_id}: {e}", exc_info=True)
            raise

    def update_user_balance(self, user_id: str, amount: float) -> Optional[User]:
        """
        Atualiza o saldo de um usuário.
        """
        logger.info(f"Atualizando saldo do usuário {user_id} em {amount}")
        user = self.get_user_by_id(user_id)
        if user:
            user.balance += amount
            self.db.commit()
            self.db.refresh(user)
            logger.info(f"Saldo do usuário {user_id} atualizado para {user.balance}.")
            return user
        logger.warning(f"Usuário {user_id} não encontrado para atualizar saldo.")
        return None

    def delete_user(self, user_id: str) -> bool:
        """
        Deleta um usuário pelo ID.
        """
        logger.info(f"Tentando deletar usuário {user_id}.")
        user = self.get_user_by_id(user_id)
        if user:
            self.db.delete(user)
            self.db.commit()
            logger.info(f"Usuário {user_id} deletado com sucesso.")
            return True
        logger.warning(f"Usuário {user_id} não encontrado para deletar.")
        return False

# Exemplo de uso (apenas para teste direto, não é o fluxo FastAPI)
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    # Assumindo que a base de dados já foi criada (via check_db_connection no main.py)
    # E que o SessionLocal está configurado para o seu banco de dados
    try:
        db_session = SessionLocal()
        user_service = UserService(db_session)

        # Exemplo de criação de usuário
        try:
            new_user = user_service.create_user(
                user_id="user_test_001",
                auth_tag="AUTH123",
                name="Test User One",
                email="test1@example.com",
                balance=100.0
            )
            logger.info(f"Criado: {new_user}")
        except ValueError as e:
            logger.error(e)

        # Exemplo de busca por ID
        found_user_id = user_service.get_user_by_id("user_test_001")
        logger.info(f"Encontrado por ID: {found_user_id}")

        # Exemplo de busca por Auth Tag
        found_user_tag = user_service.get_user_by_auth_tag("AUTH123")
        logger.info(f"Encontrado por Auth Tag: {found_user_tag}")

        # Exemplo de atualização de saldo
        updated_user = user_service.update_user_balance("user_test_001", 50.0)
        logger.info(f"Saldo atualizado: {updated_user.balance if updated_user else 'Usuário não encontrado'}")

        # Exemplo de deleção (descomente para testar)
        # if user_service.delete_user("user_test_001"):
        #     logger.info("Usuário 'user_test_001' deletado.")
        # else:
        #     logger.warning("Falha ao deletar 'user_test_001'.")

    except Exception as e:
        logger.critical(f"Erro fatal no UserService test: {e}", exc_info=True)
    finally:
        if 'db_session' in locals() and db_session:
            db_session.close()