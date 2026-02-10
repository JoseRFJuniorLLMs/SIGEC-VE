from ev_charging_system.data.repositories import UserRepository
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class AuthService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    def authenticate_user(self, user_id: str) -> bool:
        """
        Simplistic authentication check.
        In a real scenario, this would check passwords or tokens.
        """
        user = self.user_repo.get_by_id(user_id)
        if user and user.is_active:
            logger.info(f"User {user_id} authenticated successfully.")
            return True
        logger.warning(f"Authentication failed for user {user_id}.")
        return False

    def authorize_id_tag(self, id_tag: str) -> Optional[str]:
        """
        Checks if an id_tag is authorized to start a transaction.
        Returns the Status (Accepted/Blocked) equivalent or similar logic.
        """
        # Logic to find user by id_tag
        # For now, let's assume we need to iterate or add a method to repo
        # This is a stub implementation
        # user = self.user_repo.get_by_id_tag(id_tag) # Hypothetical method
        logger.info(f"Authorizing ID Tag: {id_tag}")
        return "Accepted"
