# ev_charging_system/models/user.py

from sqlalchemy import Column, String, Float
from sqlalchemy.orm import relationship
from ev_charging_system.data.database import Base # Importa a Base declarativa

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True) # Email, ou outro ID único
    auth_tag = Column(String, unique=True, index=True) # RFID, Token da app, etc.
    name = Column(String)
    email = Column(String, unique=True)
    balance = Column(Float, default=0.0)
    preferences = Column(String, default="{}") # Armazenar preferências como string JSON

    # Relação com Transactions (um User pode ter muitas Transactions)
    transactions = relationship("Transaction", back_populates="user")

    def __repr__(self):
        return f"<User(id='{self.id}', name='{self.name}')>"