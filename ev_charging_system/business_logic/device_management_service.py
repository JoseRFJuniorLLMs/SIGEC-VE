# ev_charging_system/business_logic/device_management_service.py

from sqlalchemy.orm import Session
from typing import List, Optional, Dict
import json  # Para lidar com a configuração como string JSON

# Importa os modelos e repositórios necessários
from ev_charging_system.models.charge_point import ChargePoint, ChargePointConnector
from ev_charging_system.data.repositories import ChargePointRepository


class DeviceManagementService:
    def __init__(self, db: Session):
        # A sessão do banco de dados será injetada.
        self.db = db
        self.charge_point_repo = ChargePointRepository(db)

    def register_or_update_charge_point(
            self,
            cp_id: str,
            vendor_name: str,
            model: str,
            firmware_version: str,
            status: str = "Online",
            connectors_data: Optional[List[Dict]] = None,  # Dados dos conectores (id, tipo, power_kw)
            location: Optional[str] = None,
            latitude: Optional[float] = None,
            longitude: Optional[float] = None,
            configuration: Optional[Dict] = None  # Configurações adicionais
    ) -> ChargePoint:
        """
        Registra um novo Charge Point ou atualiza um existente.
        Chamado principalmente por BootNotification.
        """
        charge_point = self.charge_point_repo.get_charge_point_by_id(cp_id)

        if charge_point:
            # Atualiza informações do CP existente
            charge_point.vendor_name = vendor_name
            charge_point.model = model
            charge_point.firmware_version = firmware_version
            charge_point.status = status  # Pode ser "Online" ou outro status inicial
            charge_point.location = location if location is not None else charge_point.location
            charge_point.latitude = latitude if latitude is not None else charge_point.latitude
            charge_point.longitude = longitude if longitude is not None else charge_point.longitude
            if configuration is not None:
                charge_point.configuration = json.dumps(configuration)  # Converte dict para string JSON
            # Não atualiza last_boot_time aqui, pois BootNotification é um evento.
            # O campo last_boot_time deve ser atualizado no handler OCPP.
            updated_cp = self.charge_point_repo.update_charge_point(charge_point)

            # Atualiza ou cria conectores
            if connectors_data:
                self._update_or_create_connectors(updated_cp, connectors_data)
            return updated_cp
        else:
            # Cria um novo Charge Point
            new_cp = ChargePoint(
                id=cp_id,
                vendor_name=vendor_name,
                model=model,
                firmware_version=firmware_version,
                status=status,
                location=location,
                latitude=latitude,
                longitude=longitude,
                configuration=json.dumps(configuration) if configuration is not None else "{}"
            )
            created_cp = self.charge_point_repo.create_charge_point(new_cp)

            # Cria conectores para o novo CP
            if connectors_data:
                self._update_or_create_connectors(created_cp, connectors_data)
            return created_cp

    def _update_or_create_connectors(self, charge_point: ChargePoint, connectors_data: List[Dict]):
        """Função auxiliar para gerenciar conectores de um Charge Point."""
        existing_connector_ids = {c.id for c in charge_point.connectors}

        for conn_data in connectors_data:
            connector_id = conn_data.get('id')
            if connector_id is None:
                # Log a warning or raise an error if connector_id is missing
                continue

            connector = self.charge_point_repo.get_connector_by_id(connector_id, charge_point.id)
            if connector:
                # Atualiza conector existente
                connector.status = conn_data.get('status', connector.status)
                connector.type = conn_data.get('type', connector.type)
                connector.power_kw = conn_data.get('power_kw', connector.power_kw)
                self.charge_point_repo.update_connector(connector)
            else:
                # Cria novo conector
                new_connector = ChargePointConnector(
                    id=connector_id,
                    charge_point_id=charge_point.id,
                    status=conn_data.get('status', "Available"),  # Default para novo conector
                    type=conn_data.get('type', "Unknown"),
                    power_kw=conn_data.get('power_kw', 0.0)
                )
                self.charge_point_repo.create_connector(new_connector)

    def update_charge_point_status(self, cp_id: str, status: str) -> Optional[ChargePoint]:
        """Atualiza o status operacional de um Charge Point."""
        charge_point = self.charge_point_repo.get_charge_point_by_id(cp_id)
        if charge_point:
            charge_point.status = status
            return self.charge_point_repo.update_charge_point(charge_point)
        return None

    def update_connector_status(self, cp_id: str, connector_id: int, status: str,
                                current_transaction_id: Optional[str] = None) -> Optional[ChargePointConnector]:
        """Atualiza o status de um conector específico de um Charge Point."""
        connector = self.charge_point_repo.get_connector_by_id(connector_id, cp_id)
        if connector:
            connector.status = status
            connector.current_transaction_id = current_transaction_id  # Pode ser None
            return self.charge_point_repo.update_connector(connector)
        return None

    def get_charge_point_details(self, cp_id: str) -> Optional[ChargePoint]:
        """Retorna os detalhes completos de um Charge Point, incluindo seus conectores."""
        return self.charge_point_repo.get_charge_point_by_id(cp_id)

    def list_all_charge_points(self) -> List[ChargePoint]:
        """Lista todos os Charge Points registrados no sistema."""
        return self.charge_point_repo.get_all_charge_points()

    def get_charge_point_status_summary(self) -> Dict[str, int]:
        """Retorna um resumo da contagem de CPs por status."""
        all_cps = self.list_all_charge_points()
        summary = {"Online": 0, "Offline": 0, "Faulted": 0, "Unknown": 0}
        for cp in all_cps:
            if cp.status in summary:
                summary[cp.status] += 1
            else:
                summary["Unknown"] += 1
        return summary