# test_ocpp_server_connection.py

import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from ocpp.v16 import ChargePoint as OCPPCp
from ocpp.routing import create_route_map
from ev_charging_system.core.ocpp_server import on_connect
from ev_charging_system.core.ocpp_central_manager import connected_charge_points


# NÂO DEVE TER -> from ev_charging_system.data.models import Base
# NÂO DEVE TER -> from sqlalchemy.orm import configure_mappers

# Fixtures para DeviceManagementService e ChargePointRepository
# Estes devem ser definidos no seu conftest.py se forem compartilhados
# ou mockados diretamente aqui se for um mock simples para este teste.

@pytest.fixture
def mock_device_management_service():
    """
    Mock para DeviceManagementService.
    Geralmente, você mockaria os métodos específicos que são chamados.
    """
    with patch('ev_charging_system.business_logic.device_management_service.DeviceManagementService',
               autospec=True) as MockService:
        service_instance = MockService.return_value
        yield service_instance


@pytest.fixture
def mock_charge_point_repository():
    """
    Mock para ChargePointRepository.
    """
    with patch('ev_charging_system.data.repositories.ChargePointRepository', autospec=True) as MockRepo:
        repo_instance = MockRepo.return_value
        yield repo_instance


# Testes
@pytest.mark.asyncio
async def test_on_connect_accepts_path_argument(mock_get_db, mock_device_management_service,
                                                mock_charge_point_repository):
    """
    Testa se a função on_connect aceita o argumento path e adiciona o CP.
    """
    mock_websocket = AsyncMock()
    test_path = "/CP-TEST-001"
    test_cp_id = "CP-TEST-001"

    # Mockar o retorno do get_charge_point_by_id para simular CP existente
    # ou não existente, dependendo do cenário de teste.
    # Neste caso, para aceitar o CP, ele não deve encontrar um existente
    mock_charge_point_repository.get_charge_point_by_id.return_value = None

    with patch('ocpp.v16.ChargePoint', autospec=True) as MockOCPPCp:
        mock_ocpp_cp_instance = AsyncMock()
        MockOCPPCp.return_value = mock_ocpp_cp_instance

        await on_connect(mock_websocket, test_path)

        MockOCPPCp.assert_called_once_with(test_cp_id, mock_websocket)
        mock_device_management_service.add_charge_point.assert_called_once()
        assert test_cp_id in connected_charge_points
        assert connected_charge_points[test_cp_id] == mock_ocpp_cp_instance
        # O teste também deve verificar se o 'start()' foi chamado, se aplicável
        mock_ocpp_cp_instance.start.assert_awaited_once()


@pytest.mark.asyncio
async def test_on_connect_already_connected_cp(mock_get_db, mock_device_management_service,
                                               mock_charge_point_repository):
    """
    Testa se a função on_connect lida corretamente com um Charge Point já conectado.
    """
    mock_websocket = AsyncMock()
    test_path = "/CP-EXISTS-001"
    test_cp_id = "CP-EXISTS-001"

    # Simular que o Charge Point já existe no banco de dados e está conectado
    mock_existing_cp_db_instance = AsyncMock()  # Mock de um objeto ChargePoint do DB
    mock_existing_cp_db_instance.charge_point_id = test_cp_id  # Definir ID para o mock
    mock_charge_point_repository.get_charge_point_by_id.return_value = mock_existing_cp_db_instance

    # Pre-popula o dicionário connected_charge_points como se o CP já estivesse conectado
    mock_existing_ocpp_cp_instance = AsyncMock()  # Mock da instância OCPP ChargePoint
    connected_charge_points[test_cp_id] = mock_existing_ocpp_cp_instance

    with patch('ocpp.v16.ChargePoint', autospec=True) as MockOCPPCp:
        mock_ocpp_cp_instance_new_connection = AsyncMock()
        MockOCPPCp.return_value = mock_ocpp_cp_instance_new_connection

        await on_connect(mock_websocket, test_path)

        # Verificar se o método de atualização de status do DeviceManagementService foi chamado
        mock_device_management_service.update_charge_point_status.assert_called_once_with(test_cp_id, "Offline")

        # Verificar se a conexão antiga foi fechada
        mock_existing_ocpp_cp_instance.shutdown.assert_awaited_once()

        # Verificar se a nova conexão foi estabelecida e iniciada
        MockOCPPCp.assert_called_once_with(test_cp_id, mock_websocket)
        assert connected_charge_points[test_cp_id] == mock_ocpp_cp_instance_new_connection
        mock_ocpp_cp_instance_new_connection.start.assert_awaited_once()