# ev_charging_system/services/device_service.py

import logging
from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from ev_charging_system.data.models import ChargePoint, Connector, User
from ev_charging_system.data.repositories import ChargePointRepository, UserRepository

logger = logging.getLogger(__name__)


class DeviceServiceError(Exception):
    """Base exception for device service operations."""
    pass


class ChargePointNotFoundError(DeviceServiceError):
    """Raised when a charge point is not found."""
    pass


class ConnectorNotFoundError(DeviceServiceError):
    """Raised when a connector is not found."""
    pass


class UserNotFoundError(DeviceServiceError):
    """Raised when a user is not found."""
    pass


class DeviceService:
    """
    Service for managing charge points, connectors, and users.
    Handles business logic without OCPP protocol specifics.
    """

    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.charge_point_repo = ChargePointRepository(db_session)
        self.user_repo = UserRepository(db_session)

    # --- Charge Point Management ---

    def get_charge_point(self, cp_id: str) -> Optional[ChargePoint]:
        """
        Retrieve a charge point by ID.

        Args:
            cp_id: Charge point identifier

        Returns:
            ChargePoint instance or None if not found
        """
        return self.charge_point_repo.get_charge_point_by_id(cp_id)

    def create_charge_point(self, cp_id: str, vendor: Optional[str] = None,
                            model: Optional[str] = None, num_connectors: int = 1) -> ChargePoint:
        """
        Create a new charge point with connectors.

        Args:
            cp_id: Unique charge point identifier
            vendor: Manufacturer name
            model: Model name
            num_connectors: Number of connectors to create

        Returns:
            Created ChargePoint instance

        Raises:
            DeviceServiceError: If charge point already exists or creation fails
        """
        try:
            # Check if charge point already exists
            existing_cp = self.get_charge_point(cp_id)
            if existing_cp:
                raise DeviceServiceError(f"Charge Point {cp_id} already exists")

            # Create charge point
            charge_point = ChargePoint(
                charge_point_id=cp_id,
                vendor=vendor,
                model=model,
                num_connectors=num_connectors,
                status="Offline",  # Default to offline until connected
                created_at=datetime.utcnow()
            )

            self.charge_point_repo.add_charge_point(charge_point)

            # Create connectors
            for connector_id in range(1, num_connectors + 1):
                connector = Connector(
                    charge_point_id=cp_id,
                    connector_id=connector_id,
                    status="Available"
                )
                self.charge_point_repo.add_connector(connector)

            self.db_session.commit()
            logger.info(f"Created charge point {cp_id} with {num_connectors} connectors")

            return charge_point

        except IntegrityError as e:
            self.db_session.rollback()
            logger.error(f"Database integrity error creating charge point {cp_id}: {e}")
            raise DeviceServiceError(f"Failed to create charge point {cp_id}: Database constraint violation")

        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Unexpected error creating charge point {cp_id}: {e}")
            raise DeviceServiceError(f"Failed to create charge point {cp_id}: {str(e)}")

    def update_charge_point_status(self, cp_id: str, status: str) -> bool:
        """
        Update charge point status.

        Args:
            cp_id: Charge point identifier
            status: New status (Online, Offline, Unavailable, etc.)

        Returns:
            True if updated successfully

        Raises:
            ChargePointNotFoundError: If charge point not found
        """
        charge_point = self.get_charge_point(cp_id)
        if not charge_point:
            raise ChargePointNotFoundError(f"Charge Point {cp_id} not found")

        try:
            old_status = charge_point.status
            charge_point.status = status
            charge_point.updated_at = datetime.utcnow()

            self.db_session.commit()
            logger.info(f"Updated charge point {cp_id} status: {old_status} -> {status}")
            return True

        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error updating charge point {cp_id} status: {e}")
            raise DeviceServiceError(f"Failed to update charge point status: {str(e)}")

    def update_heartbeat(self, cp_id: str) -> bool:
        """
        Update the last heartbeat timestamp for a charge point.

        Args:
            cp_id: Charge point identifier

        Returns:
            True if updated successfully

        Raises:
            ChargePointNotFoundError: If charge point not found
        """
        charge_point = self.get_charge_point(cp_id)
        if not charge_point:
            raise ChargePointNotFoundError(f"Charge Point {cp_id} not found")

        try:
            charge_point.last_heartbeat = datetime.utcnow()
            self.db_session.commit()
            logger.debug(f"Updated heartbeat for charge point {cp_id}")
            return True

        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error updating heartbeat for {cp_id}: {e}")
            raise DeviceServiceError(f"Failed to update heartbeat: {str(e)}")

    def get_all_charge_points(self) -> List[ChargePoint]:
        """Get all charge points."""
        return self.charge_point_repo.get_all_charge_points()

    # --- Connector Management ---

    def get_connector(self, cp_id: str, connector_id: int) -> Optional[Connector]:
        """
        Get a specific connector.

        Args:
            cp_id: Charge point identifier
            connector_id: Connector identifier

        Returns:
            Connector instance or None if not found
        """
        return self.charge_point_repo.get_connector_by_id(cp_id, connector_id)

    def update_connector_status(self, cp_id: str, connector_id: int, status: str) -> bool:
        """
        Update connector status.

        Args:
            cp_id: Charge point identifier
            connector_id: Connector identifier
            status: New status (Available, Occupied, Charging, etc.)

        Returns:
            True if updated successfully

        Raises:
            ConnectorNotFoundError: If connector not found
        """
        connector = self.get_connector(cp_id, connector_id)
        if not connector:
            raise ConnectorNotFoundError(f"Connector {connector_id} for CP {cp_id} not found")

        try:
            old_status = connector.status
            connector.status = status
            connector.updated_at = datetime.utcnow()

            self.db_session.commit()
            logger.info(f"Updated connector {cp_id}:{connector_id} status: {old_status} -> {status}")
            return True

        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error updating connector {cp_id}:{connector_id} status: {e}")
            raise DeviceServiceError(f"Failed to update connector status: {str(e)}")

    def get_available_connectors(self, cp_id: str) -> List[Connector]:
        """Get all available connectors for a charge point."""
        charge_point = self.get_charge_point(cp_id)
        if not charge_point:
            raise ChargePointNotFoundError(f"Charge Point {cp_id} not found")

        return [c for c in charge_point.connectors if c.status == "Available"]

    # --- User Management ---

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        return self.user_repo.get_user_by_id(user_id)

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        return self.user_repo.get_user_by_email(email)

    def get_user_by_id_tag(self, id_tag: str) -> Optional[User]:
        """Get user by RFID tag."""
        return self.user_repo.get_user_by_id_tag(id_tag)

    def create_user(self, user_id: str, name: str, email: str,
                    id_tag: str, phone: Optional[str] = None) -> User:
        """
        Create a new user.

        Args:
            user_id: Unique user identifier
            name: User's full name
            email: User's email address
            id_tag: RFID tag identifier
            phone: Phone number (optional)

        Returns:
            Created User instance

        Raises:
            DeviceServiceError: If user creation fails or constraints violated
        """
        try:
            # Check for existing users
            if self.get_user_by_id(user_id):
                raise DeviceServiceError(f"User {user_id} already exists")

            if self.get_user_by_email(email):
                raise DeviceServiceError(f"User with email {email} already exists")

            if self.get_user_by_id_tag(id_tag):
                raise DeviceServiceError(f"User with ID tag {id_tag} already exists")

            # Create user
            user = User(
                user_id=user_id,
                name=name,
                email=email,
                phone=phone,
                id_tag=id_tag,
                is_active=True,
                created_at=datetime.utcnow()
            )

            self.user_repo.add_user(user)
            self.db_session.commit()

            logger.info(f"Created user {user_id} with email {email}")
            return user

        except IntegrityError as e:
            self.db_session.rollback()
            logger.error(f"Database integrity error creating user {user_id}: {e}")
            raise DeviceServiceError(f"Failed to create user: Database constraint violation")

        except DeviceServiceError:
            raise

        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Unexpected error creating user {user_id}: {e}")
            raise DeviceServiceError(f"Failed to create user: {str(e)}")

    def update_user_status(self, user_id: str, is_active: bool) -> bool:
        """
        Update user active status.

        Args:
            user_id: User identifier
            is_active: New active status

        Returns:
            True if updated successfully

        Raises:
            UserNotFoundError: If user not found
        """
        user = self.get_user_by_id(user_id)
        if not user:
            raise UserNotFoundError(f"User {user_id} not found")

        try:
            user.is_active = is_active
            user.updated_at = datetime.utcnow()

            self.db_session.commit()
            logger.info(f"Updated user {user_id} active status to {is_active}")
            return True

        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error updating user {user_id} status: {e}")
            raise DeviceServiceError(f"Failed to update user status: {str(e)}")

    def delete_user(self, user_id: str) -> bool:
        """
        Delete a user.

        Args:
            user_id: User identifier

        Returns:
            True if deleted successfully

        Raises:
            UserNotFoundError: If user not found
        """
        user = self.get_user_by_id(user_id)
        if not user:
            raise UserNotFoundError(f"User {user_id} not found")

        try:
            self.user_repo.delete_user(user)
            self.db_session.commit()

            logger.info(f"Deleted user {user_id}")
            return True

        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error deleting user {user_id}: {e}")
            raise DeviceServiceError(f"Failed to delete user: {str(e)}")

    def is_user_authorized(self, id_tag: str) -> bool:
        """
        Check if a user is authorized to start transactions.

        Args:
            id_tag: RFID tag identifier

        Returns:
            True if user is found and active
        """
        user = self.get_user_by_id_tag(id_tag)
        return user is not None and user.is_active