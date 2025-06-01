import asyncio
import logging
import websockets
from ocpp.v16 import call_result
from ocpp.v16 import ChargePoint
from ocpp.v16.enums import RegistrationStatus, RemoteStartStopStatus, ResetType, AvailabilityType, ChargePointStatus
from ocpp.routing import on

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('charge_point_simulator')


# --- Funções de Manipulação de Mensagens OCPP ---
@on('BootNotification')
async def on_boot_notification(charge_point: ChargePoint, **kwargs):
    logger.info(f"CP {charge_point.id}: Recebida BootNotification: {kwargs}")
    return call_result.BootNotification(
        current_time='2025-05-30T10:00:00Z',  # Data fictícia
        interval=300,  # Enviar Heartbeat a cada 300 segundos
        status=RegistrationStatus.accepted
    )


@on('RemoteStartTransaction')
async def on_remote_start_transaction(charge_point: ChargePoint, connector_id: int, id_tag: str, **kwargs):
    logger.info(
        f"CP {charge_point.id}: Recebida RemoteStartTransaction para conector {connector_id} com ID Tag {id_tag}")
    # Simula a aceitação do comando
    response_status = RemoteStartStopStatus.accepted
    if connector_id == 0:  # ConnectorId 0 geralmente significa todo o CP, mas RemoteStart é para um conector específico
        logger.warning(f"CP {charge_point.id}: RemoteStartTransaction para conector 0. Isso não é padrão.")
        # response_status = RemoteStartStopStatus.rejected # Poderia rejeitar

    # Em um CP real, aqui ele mudaria o status do conector para "Charging" e enviaria um StartTransaction.req
    # Para o simulador, vamos simular o StartTransaction.req imediatamente para o CSMS
    if response_status == RemoteStartStopStatus.accepted:
        logger.info(f"CP {charge_point.id}: Simulando envio de StartTransaction.req para o CSMS...")
        # Você precisa gerar um transactionId para esta transação.
        # No mundo real, o CP geraria isso. Aqui, podemos usar um timestamp ou um contador simples.
        import time
        transaction_id = int(time.time() * 1000)  # Exemplo simples de ID de transação

        await charge_point.send_start_transaction(
            connector_id=connector_id,
            id_tag=id_tag,
            meter_start=0,  # Metragem inicial
            timestamp=datetime.utcnow().isoformat(),
            transaction_id=transaction_id  # ID gerado pelo CP
        )
        logger.info(
            f"CP {charge_point.id}: StartTransaction.req enviado para o CSMS para transaction_id {transaction_id}")

        # Opcional: Atualizar status do conector para "Charging" e enviar StatusNotification
        await charge_point.send_status_notification(
            connector_id=connector_id,
            status=ChargePointStatus.Charging,
            error_code="NoError"
        )

    return call_result.RemoteStartTransaction(status=response_status)


@on('RemoteStopTransaction')
async def on_remote_stop_transaction(charge_point: ChargePoint, transaction_id: int):
    logger.info(f"CP {charge_point.id}: Recebida RemoteStopTransaction para transação {transaction_id}")
    # Simula a aceitação do comando
    response_status = RemoteStartStopStatus.accepted

    # Em um CP real, aqui ele mudaria o status do conector para "Finishing" ou "Available"
    # e enviaria um StopTransaction.req para o CSMS
    if response_status == RemoteStartStopStatus.accepted:
        logger.info(f"CP {charge_point.id}: Simulando envio de StopTransaction.req para o CSMS...")
        await charge_point.send_stop_transaction(
            transaction_id=transaction_id,
            meter_stop=random.randint(100, 500),  # Metragem final simulada
            timestamp=datetime.utcnow().isoformat(),
            reason="RemoteStopped"  # Razão da parada
        )
        logger.info(
            f"CP {charge_point.id}: StopTransaction.req enviado para o CSMS para transaction_id {transaction_id}")

        # Opcional: Atualizar status do conector para "Available" e enviar StatusNotification
        await charge_point.send_status_notification(
            connector_id=1,  # Assumindo conector 1 para simplificar, idealmente buscar da transação
            status=ChargePointStatus.Available,
            error_code="NoError"
        )

    return call_result.RemoteStopTransaction(status=response_status)


@on('Reset')
async def on_reset(charge_point: ChargePoint, type: ResetType):  # Usando ResetType para tipagem
    logger.info(f"CP {charge_point.id}: Recebido Reset {type} para o CP.")
    # Simula um breve atraso para o reset
    await asyncio.sleep(2)
    # Após o reset, um CP real enviaria um novo BootNotification.
    # Vamos simular isso para completar o ciclo.
    logger.info(f"CP {charge_point.id}: Simulando novo BootNotification após reset...")
    await charge_point.send_boot_notification(
        charge_point_vendor="Simulador",
        charge_point_model="SIGEC-VE-Simulator"
    )
    logger.info(f"CP {charge_point.id}: Novo BootNotification enviado após reset.")
    return call_result.Reset(status='Accepted')


@on('ChangeConfiguration')
async def on_change_configuration(charge_point: ChargePoint, key: str, value: str):
    logger.info(f"CP {charge_point.id}: Recebida ChangeConfiguration - Key: {key}, Value: {value}")
    # Aqui você simularia a aplicação da nova configuração no CP
    # Para o simulador, apenas aceitamos e logamos.
    return call_result.ChangeConfiguration(status='Accepted')


@on('ChangeAvailability')
async def on_change_availability(charge_point: ChargePoint, connector_id: int, type: AvailabilityType):
    logger.info(f"CP {charge_point.id}: Recebida ChangeAvailability - Conector: {connector_id}, Tipo: {type}")
    # Simula a mudança de disponibilidade do conector
    status_to_report = ChargePointStatus.Available if type == AvailabilityType.operative else ChargePointStatus.Unavailable
    await charge_point.send_status_notification(
        connector_id=connector_id,
        status=status_to_report,
        error_code="NoError"
    )
    return call_result.ChangeAvailability(status='Accepted')


# --- Função Principal de Conexão do CP ---
async def start_charge_point(cp_id: str, csms_url: str):
    logger.info(f"Iniciando Charge Point '{cp_id}' conectando a {csms_url}")
    try:
        async with websockets.connect(f"{csms_url}/{cp_id}", subprotocols=['ocpp2.0', 'ocpp2.0.1']) as websocket:
            charge_point = ChargePoint(cp_id, websocket)

            # Define os handlers para as mensagens que o CSMS pode enviar para o CP
            charge_point.add_handler(on_boot_notification)
            charge_point.add_handler(on_remote_start_transaction)
            charge_point.add_handler(on_remote_stop_transaction)
            charge_point.add_handler(on_reset)
            charge_point.add_handler(on_change_configuration)  # Adicionado handler
            charge_point.add_handler(on_change_availability)  # Adicionado handler

            # Envia a primeira BootNotification assim que conectar
            logger.info(f"CP {cp_id}: Enviando BootNotification...")
            response = await charge_point.send_boot_notification(
                charge_point_vendor="Simulador",
                charge_point_model="SIGEC-VE-Simulator"
            )
            logger.info(f"CP {cp_id}: BootNotification Response: {response}")

            if response.status == RegistrationStatus.accepted:
                logger.info(f"CP {cp_id}: Conectado e aceito pelo CSMS. Mantendo conexão...")
                # Opcional: Enviar StatusNotification para os conectores após BootNotification
                await asyncio.sleep(1)  # Pequeno atraso
                await charge_point.send_status_notification(
                    connector_id=1,
                    status=ChargePointStatus.Available,
                    error_code="NoError"
                )
                await asyncio.sleep(0.5)
                await charge_point.send_status_notification(
                    connector_id=2,
                    status=ChargePointStatus.Available,
                    error_code="NoError"
                )
                logger.info(f"CP {cp_id}: StatusNotification para conectores enviado.")

                # Mantém a conexão aberta, o Charge Point pode receber chamadas do CSMS
                # e enviar mensagens periódicas (e.g., Heartbeat, MeterValues)
                await asyncio.Future()  # Mantém o loop de eventos rodando indefinidamente
            else:
                logger.error(f"CP {cp_id}: Não aceito pelo CSMS. Status: {response.status}")

    except websockets.exceptions.ConnectionClosedOK:
        logger.info(f"CP {cp_id}: Conexão fechada normalmente pelo CSMS.")
    except Exception as e:
        logger.error(f"CP {cp_id}: Erro ao conectar Charge Point: {e}")


# --- Execução Principal ---
if __name__ == '__main__':
    # URL do seu servidor CSMS (ocpp_server.py)
    # Lembre-se que o seu CSMS deve estar rodando na porta 9000
    CSMS_URL = "ws://localhost:9000"


    async def main():
        logger.info("Iniciando simuladores de Charge Point...")
        # Rodar 2 CPs simulados em paralelo
        cp1_task = asyncio.create_task(start_charge_point("CP-SIGEC-001", CSMS_URL))
        cp2_task = asyncio.create_task(start_charge_point("CP-SIGEC-002", CSMS_URL))
        await asyncio.gather(cp1_task, cp2_task)
        logger.info("Simuladores de Charge Point concluídos.")


    asyncio.run(main())