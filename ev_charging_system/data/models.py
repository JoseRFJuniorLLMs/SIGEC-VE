# ev_charging_system/data/models.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Float
from sqlalchemy.orm import relationship, declarative_base, configure_mappers
from datetime import datetime

# A ÚNICA chamada para declarative_base() em todo o seu projeto.
# Esta instância Base é compartilhada por todos os seus modelos.
Base = declarative_base()


class ChargePoint(Base):
    """
    Model to represent a Charge Point (Charging Station) in the system.
    """
    __tablename__ = "charge_points"

    id = Column(Integer, primary_key=True, index=True)
    charge_point_id = Column(String, unique=True, index=True, nullable=False)  # Ex: CP-SIGEC-001
    status = Column(String,
                    default="Offline")  # Online, Offline, Available, Preparing, Charging, Finishing, Reserved, Faulted

    # Campo 'vendor' foi renomeado para 'vendor_name' para corresponder ao resto da aplicação.
    vendor_name = Column(String, nullable=True)

    model = Column(String, nullable=True)
    last_heartbeat = Column(DateTime, nullable=True)
    firmware_version = Column(String, nullable=True)
    address = Column(String, nullable=True)  # Ex: Rua A, 123
    num_connectors = Column(Integer, default=1)  # Number of connectors in the CP

    # Campos que faltavam adicionados para corrigir os erros
    last_boot_notification = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships:
    # One Charge Point can have many Connectors
    connectors = relationship("Connector", back_populates="charge_point", cascade="all, delete-orphan", lazy="selectin")
    # One Charge Point can have many Transactions
    transactions = relationship("Transaction", back_populates="charge_point", cascade="all, delete-orphan",
                                lazy="selectin")


class Connector(Base):
    """
    Model to represent an individual Connector in a Charge Point.
    """
    __tablename__ = "connectors"

    id = Column(Integer, primary_key=True, index=True)
    # connector_id is the logical ID of the connector WITHIN the Charge Point (ex: 1, 2, etc.)
    connector_id = Column(Integer, nullable=False)
    # Foreign key to the Charge Point this connector belongs to
    charge_point_id = Column(String, ForeignKey("charge_points.charge_point_id"), nullable=False)
    status = Column(String, default="Available")  # Available, Occupied, Faulted, Charging, etc.
    standard = Column(String, nullable=True)  # Ex: IEC 62196 Type 2
    format = Column(String, nullable=True)  # Ex: C (Cable) or S (Socket)
    power_type = Column(String, nullable=True)  # Ex: AC, DC
    max_voltage = Column(Integer, nullable=True)
    max_amperage = Column(Integer, nullable=True)
    max_power = Column(Integer, nullable=True)  # In Watts or kW

    # Campos que faltavam adicionados para consistência
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship back to the Charge Point
    charge_point = relationship("ChargePoint", back_populates="connectors",
                                primaryjoin="ChargePoint.charge_point_id == Connector.charge_point_id")  # Explicit primaryjoin for clarity


class Transaction(Base):
    """
    Model to record charging transactions.
    """
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String, unique=True, index=True, nullable=False)  # Transaction ID in CSMS
    charge_point_id = Column(String, ForeignKey("charge_points.charge_point_id"), nullable=False)
    connector_id = Column(Integer, nullable=False)  # ID of connector used in transaction
    id_tag = Column(String, nullable=False)  # RFID or user identifier
    start_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    stop_time = Column(DateTime, nullable=True)
    meter_start = Column(Float, nullable=False)  # Meter reading at start (Wh or kWh)
    meter_stop = Column(Float, nullable=True)  # Meter reading at end (Wh or kWh)
    energy_transfered = Column(Float, default=0.0, nullable=False)  # Total energy transferred (Wh or kWh)
    status = Column(String, default="Charging", nullable=False)  # Charging, Completed, Failed, Authorized, Stopped

    # Campos que faltavam adicionados para consistência
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship back to the Charge Point
    charge_point = relationship("ChargePoint", back_populates="transactions",
                                primaryjoin="ChargePoint.charge_point_id == Transaction.charge_point_id")  # Explicit primaryjoin for clarity


class User(Base):
    """
    Model to represent users in the system.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, nullable=True)
    id_tag = Column(String, unique=True, index=True, nullable=False)  # RFID tag
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Crucial: Ensures that all mappers are configured after all classes have been defined.
# This makes sure SQLAlchemy understands all relationships.
configure_mappers()
print("DEBUG: Mappers configured in models.py")