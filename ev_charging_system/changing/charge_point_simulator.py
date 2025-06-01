import asyncio
import logging
import websockets
from ocpp.v16 import call_result
from ocpp.v16 import ChargePoint as OCPPCp  # Renomeado para evitar conflito com a classe local
from ocpp.v16.enums import (
    RegistrationStatus,
    RemoteStartStopStatus,
    ResetType,
    AvailabilityType,
    ChargePointStatus,
)
from ocpp.routing import on  # Mantenha o 'on' para os decoradores

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("charge_point_simulator")


# --- Classe Personalizada para o Charge Point Simulador ---
# Os decorators @on() funcionam quando aplicados a métodos de uma classe
# que herda de ocpp.v16.ChargePoint.
class ChargePoint(
    OCPPCp
):  # Agora ChargePoint herda de OCPPCp (o ChargePoint da biblioteca)
    @on("BootNotification")
    async def on_boot_notification(self, **kwargs):
        logger.info(f"CP {self.id}: Recebida BootNotification: {kwargs}")
        # Envia StatusNotification imediatamente após BootNotification para informar o CSMS
        await self.send_status_notification(
            connector_id=1, status=ChargePointStatus.Available, error_code="NoError"
        )
        await self.send_status_notification(
            connector_id=2, status=ChargePointStatus.Available, error_code="NoError"
        )
        logger.info(
            f"CP {self.id}: StatusNotification para conectores enviado após BootNotification."
        )

        return call_result.BootNotification(
            current_time="2025-05-30T10:00:00Z",  # Data fictícia
            interval=300,  # Enviar Heartbeat a cada 300 segundos
            status=RegistrationStatus.accepted,
        )

    @on("RemoteStartTransaction")
    async def on_remote_start_transaction(
        self, connector_id: int, id_tag: str, **kwargs
    ):
        logger.info(
            f"CP {self.id}: Recebida RemoteStartTransaction para conector {connector_id} com ID Tag {id_tag}"
        )
        # Simula a aceitação do comando
        # Em um CP real, isso iniciaria a transação e enviaria um StartTransaction.conf
        return call_result.RemoteStartTransaction(status=RemoteStartStopStatus.accepted)

    @on("RemoteStopTransaction")
    async def on_remote_stop_transaction(self, transaction_id: int, **kwargs):
        logger.info(
            f"CP {self.id}: Recebida RemoteStopTransaction para transação {transaction_id}"
        )
        # Simula a aceitação do comando
        # Em um CP real, isso pararia a transação e enviaria um StopTransaction.conf
        return call_result.RemoteStopTransaction(status=RemoteStartStopStatus.accepted)

    @on("Reset")
    async def on_reset(self, type: ResetType, **kwargs):
        logger.info(f"CP {self.id}: Recebida Reset com tipo: {type}")
        # Simula o reset. Em um CP real, ele se desconectaria e reiniciaria.
        return call_result.Reset(status=ResetType.accepted)

    @on("ChangeAvailability")
    async def on_change_availability(self, connector_id: int, type: AvailabilityType, **kwargs):
        logger.info(
            f"CP {self.id}: Recebida ChangeAvailability para conector {connector_id} tipo: {type}"
        )
        # Simula a mudança de disponibilidade.
        return call_result.ChangeAvailability(status=AvailabilityType.accepted)

    @on("Heartbeat")
    async def on_heartbeat(self, **kwargs):
        # logger.info(f"CP {self.id}: Recebido Heartbeat.")  # Descomente para ver todos os heartbeats
        return call_result.Heartbeat(current_time="2025-05-30T10:00:00Z")


# --- Função para Iniciar um Charge Point Simulador --
async def start_charge_point(cp_id: str, csms_url: str):
    logger.info(f"Iniciando Charge Point '{cp_id}' conectando a {csms_url}/{cp_id}")
    try:
        async with websockets.connect(
            csms_url + f"/{cp_id}", subprotocols=['ocpp2.0', 'ocpp2.0.1']
        ) as websocket:
            # Instancia sua classe personalizada ChargePoint
            charge_point = ChargePoint(cp_id, websocket)

            logger.info(f"CP {cp_id}: Conectado ao CSMS. Enviando BootNotification...")
            # Envia BootNotification (isso acionará o on_boot_notification acima)
            await charge_point.send_boot_notification(
                charge_point_model="SIGEC-CP-Sim", charge_point_vendor="SIGEC"
            )

            # Mantém a conexão aberta, o Charge Point pode receber chamadas do CSMS
            # e enviar mensagens periódicas (e.g., Heartbeat, MeterValues)
            await asyncio.Future()  # Mantém o loop de eventos rodando indefinidamente
    except websockets.exceptions.ConnectionClosedOK:
        logger.info(f"CP {cp_id}: Conexão fechada normalmente pelo CSMS.")
    except Exception as e:
        logger.error(f"CP {cp_id}: Erro ao conectar Charge Point: {e}")


# --- Execução Principal ---
if __name__ == "__main__":
    # URL do seu servidor CSMS (ocpp_server.py)
    # Lembre-se que o seu CSMS deve estar rodando na porta 9000
    CSMS_URL = "ws://localhost:9000"

    async def main():
        logger.info("Iniciando simuladores de Charge Point...")
        # Rodar 2 CPs simulados em paralelo
        cp1_task = asyncio.create_task(start_charge_point("CP-SIGEC-001", CSMS_URL))
        # Adiciona um pequeno atraso para o segundo CP iniciar
        await asyncio.sleep(1)
        cp2_task = asyncio.create_task(start_charge_point("CP-SIGEC-002", CSMS_URL))

        # Esperar que ambos os simuladores terminem (o que neste caso é indefinidamente)
        await asyncio.gather(cp1_task, cp2_task)
        logger.info("Simuladores de Charge Point concluídos.")

    asyncio.run(main())