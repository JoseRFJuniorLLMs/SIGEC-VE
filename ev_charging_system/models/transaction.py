# ev_charging_system/models/transaction.py

# ADICIONE ESTA LINHA:
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Integer # <--- Adicionado Integer aqui!
from sqlalchemy.orm import relationship
from datetime import datetime
from ev_charging_system.data.database import Base

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String, primary_key=True, index=True) # ID da transação (OCPP)
    charge_point_id = Column(String, ForeignKey("charge_points.id"))
    connector_id = Column(Integer, ForeignKey("charge_point_connectors.id")) # Chave estrangeira para o conector
    user_id = Column(String, ForeignKey("users.id"))
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    start_meter_value = Column(Float) # kWh
    end_meter_value = Column(Float, nullable=True) # kWh
    total_energy_kwh = Column(Float, nullable=True)
    status = Column(String) # Charging, Finished, Failed, Canceled
    tariff_applied = Column(String, nullable=True)
    cost = Column(Float, nullable=True)
    stop_reason = Column(String, nullable=True)

    # Relações:
    charge_point = relationship("ChargePoint", back_populates="transactions", uselist=False) # Um para um ou muitos para um
    connector = relationship("ChargePointConnector", back_populates="transactions")
    user = relationship("User", back_populates="transactions")

    def __repr__(self):
        return f"<Transaction(id='{self.id}', user_id='{self.user_id}', cp_id='{self.charge_point_id}')>"