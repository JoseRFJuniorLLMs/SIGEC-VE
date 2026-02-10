import pytest
from unittest.mock import MagicMock
from ev_charging_system.business_logic.auth_service import AuthService
from ev_charging_system.data.repositories import UserRepository

def test_authenticate_user_success():
    mock_repo = MagicMock(spec=UserRepository)
    mock_user = MagicMock()
    mock_user.is_active = True
    mock_repo.get_by_id.return_value = mock_user

    auth_service = AuthService(mock_repo)
    result = auth_service.authenticate_user("user123")
    
    assert result is True
    mock_repo.get_by_id.assert_called_with("user123")

def test_authenticate_user_failure():
    mock_repo = MagicMock(spec=UserRepository)
    mock_repo.get_by_id.return_value = None

    auth_service = AuthService(mock_repo)
    result = auth_service.authenticate_user("unknown_user")

    assert result is False
