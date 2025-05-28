# ev_charging_system/models/transaction.py

from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class Transaction:
    """Representa uma sessão de carregamento."""
    id: str  # ID único da transação (gerado pelo CSMS ou CP)
    charge_point_id: str # ID do posto de carregamento onde ocorreu a transação
    connector_id: int # ID do conector usado
    user_id: str # ID do usuário que iniciou a transação
    start_time: datetime # Data e hora de início da transação
    end_time: Optional[datetime] = None # Data e hora de término da transação
    start_meter_value: float # Leitura do contador em kWh no início
    end_meter_value: Optional[float] = None # Leitura do contador em kWh no final
    total_energy_kwh: Optional[float] = None # Energia total consumida na sessão (kWh)
    status: str # Status da transação (e.g., "Charging", "Finished", "Failed", "Canceled")
    tariff_applied: Optional[str] = None # Tarifa aplicada (e.g., "Padrao", "Noturno")
    cost: Optional[float] = None # Custo total da transação
    stop_reason: Optional[str] = None # Motivo do término (e.g., "EVDisconnected", "LocalStop", "RemoteStop")
    # Outros dados relevantes (eventos, erros específicos da transação)