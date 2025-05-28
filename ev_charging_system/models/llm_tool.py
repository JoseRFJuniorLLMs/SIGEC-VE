# ev_charging_system/models/llm_tool.py

from dataclasses import dataclass, field
from typing import Dict, Optional

@dataclass
class LLMToolDefinition:
    """
    Define uma "ferramenta" que o LLM pode chamar via MCP para realizar ações.
    O schema JSON dos parâmetros é crucial para o LLM entender como usar a ferramenta.
    """
    name: str  # Nome único da ferramenta (e.g., "start_charging_session")
    description: str  # Descrição clara do que a ferramenta faz
    parameters: Dict = field(default_factory=dict) # Esquema JSON (OpenAPI-like) para os parâmetros da ferramenta

@dataclass
class LLMResourceDefinition:
    """
    Define um "recurso" de dados que o LLM pode consultar via MCP para obter informações.
    """
    name: str  # Nome único do recurso (e.g., "charge_point_status")
    description: str  # Descrição clara do tipo de dado que o recurso fornece
    path: str  # O caminho do endpoint (se for uma API REST interna ao MCP)
    query_parameters: Optional[Dict] = None # Esquema JSON para parâmetros de consulta (se houver)
    response_schema: Dict = field(default_factory=dict) # Esquema JSON da resposta esperada