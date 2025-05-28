# ev_charging_system/models/charge_point.py

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime

@dataclass
class ChargePointConnector:
    """Representa um conector individual em um posto de carregamento."""
    id: int  # Identificador único do conector dentro do CP (e.g., 1, 2)
    status: str  # Ex: "Available", "Occupied", "Unavailable", "Faulted"
    type: str    # Ex: "Type2", "CCS2", "CHAdeMO"
    power_kw: float # Potência máxima em kW que este conector pode fornecer
    current_transaction_id: Optional[str] = None # ID da transação atual, se estiver ocupado

@dataclass
class ChargePoint:
    """Representa um posto de carregamento completo."""
    id: str  # Identificador único do Charge Point (e.g., "CP-A123")
    vendor_name: str # Nome do fabricante (e.g., "MinhaEmpresa")
    model: str # Modelo do equipamento (e.g., "ExemploChargePoint-001")
    location: str # Localização física (e.g., "Lisboa", "Estoril")
    firmware_version: str # Versão atual do firmware
    status: str # Status geral do CP (e.g., "Online", "Offline", "Updating", "Faulted")
    connectors: List[ChargePointConnector] = field(default_factory=list) # Lista de conectores
    last_boot_time: Optional[datetime] = None # Última vez que o CP iniciou
    last_heartbeat_time: Optional[datetime] = None # Último heartbeat recebido
    configuration: Dict = field(default_factory=dict) # Configurações específicas do CP
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    def add_connector(self, connector: ChargePointConnector):
        """Adiciona um conector à lista de conectores do posto."""
        self.connectors.append(connector)

    def get_connector(self, connector_id: int) -> Optional[ChargePointConnector]:
        """Retorna um conector pelo seu ID."""
        return next((c for c in self.connectors if c.id == connector_id), None)