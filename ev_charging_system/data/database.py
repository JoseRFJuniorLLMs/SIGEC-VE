# ev_charging_system/data/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

# Import the Base from your consolidated models file. It's the ONLY Base for your application.
from ev_charging_system.data.models import Base

# Database connection string (adjust as needed)
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    # Usar um banco de dados SQLite em memória para desenvolvimento/teste se a variável não estiver definida
    DATABASE_URL = "sqlite:///./sql_app.db" # Usando um arquivo SQLite para persistência simples
    print(f"WARNING: DATABASE_URL not defined, using SQLite database at {DATABASE_URL}.")
else:
    print(f"INFO: Using DATABASE_URL: {DATABASE_URL}")

# Create the database engine
engine = create_engine(DATABASE_URL)

# Create a local database session.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Convenience function to get a database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# IMPORTANT: No Base.metadata.create_all(engine) here!
# Table creation is now managed by the startup event in main.py
# or by a migration tool (like Alembic) in more complex setups.