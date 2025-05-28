# ev_charging_system/models/charge_point.py

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import List, Dict, Optional # Adicionei Dict para configuração
from ev_charging_system.data.database import Base # Importa a Base declarativa

class ChargePoint(Base):
    __tablename__ = "charge_points"

    id = Column(String, primary_key=True, index=True) # OCPP Charge Point ID
    vendor_name = Column(String)
    model = Column(String)
    location = Column(String)
    firmware_version = Column(String)
    status = Column(String, default="Offline") # Online, Offline, Faulted, etc.
    last_boot_time = Column(DateTime, nullable=True)
    last_heartbeat_time = Column(DateTime, nullable=True)
    # Exemplo de campo JSON para configurações flexíveis (requer tipo JSONB para PostgreSQL)
    # from sqlalchemy.dialects.postgresql import JSONB
    # configuration = Column(JSONB, default={})
    # Se não quiser JSONB, use String e serialize/deserialize para JSON manualmente
    configuration = Column(String, default="{}") # Armazenar como string JSON
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # Relação com ChargePointConnectors (um ChargePoint pode ter muitos Connectors)
    connectors = relationship("ChargePointConnector", back_populates="charge_point")

    def __repr__(self):
        return f"<ChargePoint(id='{self.id}', status='{self.status}')>"

class ChargePointConnector(Base):
    __tablename__ = "charge_point_connectors"

    id = Column(Integer, primary_key=True, index=True) # Connector ID dentro do CP
    charge_point_id = Column(String, ForeignKey("charge_points.id")) # Chave estrangeira para o CP
    status = Column(String, default="Unavailable") # Available, Occupied, Faulted, etc.
    type = Column(String) # Type2, CCS2, CHAdeMO
    power_kw = Column(Float) # Potência máxima em kW
    current_transaction_id = Column(String, nullable=True) # ID da transação atual, se houver

    # Relação com ChargePoint (um Connector pertence a um ChargePoint)
    charge_point = relationship("ChargePoint", back_populates="connectors")
    # Relação com Transaction (um Connector pode ter muitas Transactions)
    transactions = relationship("Transaction", back_populates="connector")

    def __repr__(self):
        return f"<ChargePointConnector(id={self.id}, cp_id='{self.charge_point_id}', status='{self.status}')>"