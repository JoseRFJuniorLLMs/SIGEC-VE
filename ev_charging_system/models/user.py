# ev_charging_system/models/user.py

from dataclasses import dataclass, field
from typing import Dict, Optional

@dataclass
class User:
    """Representa um usuário da rede de carregamento."""
    id: str  # ID único do usuário (e.g., e-mail, ID interno)
    auth_tag: str # Tag para autenticação (e.g., cartão RFID, token da app)
    name: str # Nome completo do usuário
    email: str # E-mail do usuário
    balance: float = 0.0 # Saldo da conta do usuário
    preferences: Dict = field(default_factory=dict) # Preferências do usuário (e.g., {"cost_sensitive": True, "priority": "normal"})
    # Outros campos relevantes (telefone, endereço, etc.)