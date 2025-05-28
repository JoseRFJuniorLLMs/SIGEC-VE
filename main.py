# Em main.py ou um script de inicialização do BD
from ev_charging_system.data.database import Base, engine
import ev_charging_system.models.charge_point # Importa para que os modelos sejam registrados com a Base
import ev_charging_system.models.user
import ev_charging_system.models.transaction

def create_db_tables():
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created (or already exist).")

# Chame esta função na inicialização do seu main.py, antes de iniciar os servidores
# Ex:
# if __name__ == "__main__":
#     check_db_connection() # Verifique a conexão
#     create_db_tables()    # Crie as tabelas
#     # ... Inicie seus servidores ...