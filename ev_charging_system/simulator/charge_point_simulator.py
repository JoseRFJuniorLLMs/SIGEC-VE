import asyncio
import logging
import websockets
from datetime import datetime, timezone
import time
import random

# Importar o ChargePoint e os enums/datatypes
from ocpp.v201 import ChargePoint as OCPPCp
from ocpp.v201 import enums as ocpp_enums_v201
from ocpp.v201 import datatypes as ocpp_datatypes_v201
from ocpp.routing import on

# Importar TODOS os objetos de call de uma vez usando um alias
import ocpp.v201.call as ocpp_call_v201

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('charge_point_simulator')

current_transactions = {}


@on('BootNotification')
async def on_boot_notification(charge_point: OCPPCp, **kwargs):
    logger.info(f"CP {charge_point.id}: Recebida BootNotification: {kwargs}")
    return {
        'current_time': datetime.now(timezone.utc).isoformat(),
        'interval': 300,
        'status': ocpp_enums_v201.RegistrationStatusType.accepted
    }


async def _send_meter_values(charge_point: OCPPCp, evse_id: int, transaction_id: str, meter_start: int):
    # Simular o envio de MeterValues periodicamente
    logger.info(f"CP {charge_point.id}: Iniciando envio de MeterValues para Transação {transaction_id} no EVSE {evse_id}...")
    meter_value = meter_start
    try:
        while True:
            await asyncio.sleep(5)  # Envia MeterValues a cada 5 segundos
            meter_value += random.uniform(0.1, 0.5)  # Simula consumo de energia
            logger.info(f"CP {charge_point.id}: Enviando MeterValue {meter_value:.2f} kWh para Transação {transaction_id} no EVSE {evse_id}")

            meter_data = ocpp_datatypes_v201.MeterValueType(
                timestamp=datetime.now(timezone.utc).isoformat(),
                sampled_value=[
                    ocpp_datatypes_v201.SampledValueType(
                        value=str(round(meter_value, 2)),
                        unit=ocpp_enums_v201.UnitOfMeasureEnumType.kwh,
                        measurand=ocpp_enums_v201.MeasurandEnumType.energy_active_import_register
                    )
                ]
            )
            request = ocpp_call_v201.MeterValues(
                evse_id=evse_id,
                meter_value=[meter_data],
                transaction_id=transaction_id
            )
            await charge_point.call(request)
    except asyncio.CancelledError:
        logger.info(f"CP {charge_point.id}: Envio de MeterValues cancelado para Transação {transaction_id}.")
    except Exception as e:
        logger.error(f"CP {charge_point.id}: Erro no envio de MeterValues para Transação {transaction_id}: {e}", exc_info=True)


async def start_charge_point(cp_id: str, csms_url: str):
    logger.info(f"CP {cp_id}: Tentando conectar ao CSMS em {csms_url}...")
    websocket = None
    heartbeat_task = None
    try:
        async with websockets.connect(f"{csms_url}/{cp_id}", subprotocols=['ocpp2.0.1']) as ws:
            charge_point = OCPPCp(cp_id, ws)

            logger.info(f"CP {cp_id}: Conectado ao CSMS. Enviando BootNotification...")

            # Use ocpp_enums_v201.BootReasonEnum.PowerUp
            boot_notification_payload = ocpp_call_v201.BootNotification(
                reason=ocpp_enums_v201.BootReasonEnumType.power_up, # Changed from PowerUp to power_up
                charging_station=ocpp_datatypes_v201.ChargingStationType(
                    model='Simulator_Model',
                    vendor_name='Simulator_Vendor',
                    firmware_version='1.0.0'
                )
            )
            await charge_point.call(boot_notification_payload)
            logger.info(f"CP {cp_id}: BootNotification enviado.")

            # Iniciar a tarefa de heartbeat
            heartbeat_task = asyncio.create_task(send_heartbeats(charge_point))

            # Loop principal para manter a conexão aberta e processar mensagens
            while True:
                try:
                    message = await asyncio.wait_for(ws.recv(), timeout=60)
                    logger.debug(f"CP {cp_id}: Mensagem recebida: {message}")
                    await charge_point.process_message(message)
                except asyncio.TimeoutError:
                    logger.warning(f"CP {charge_point.id}: Tempo limite de recebimento de mensagem excedido. Verificando conexão...")
                    # O heartbeat deve manter a conexão viva, mas isso serve como um fallback.
                    pass
                except websockets.exceptions.ConnectionClosedOK:
                    logger.info(f"CP {charge_point.id}: Conexão fechada normalmente.")
                    break
                except websockets.exceptions.ConnectionClosedError as e:
                    logger.error(f"CP {cp_id}: Conexão fechada com erro: {e}", exc_info=True)
                    break

    except ConnectionRefusedError:
        logger.error(f"CP {cp_id}: Conexão recusada. Certifique-se de que o CSMS está em execução em {csms_url}.")
    except websockets.exceptions.InvalidURI: # Changed from InvalidURIError to InvalidURI
        logger.error(f"CP {cp_id}: URI do CSMS inválida: {csms_url}")
    except Exception as e:
        logger.error(f"CP {cp_id}: Erro ao conectar Charge Point: {e}", exc_info=True)
    finally:
        logger.info(f"CP {cp_id}: Finalizando Charge Point.")
        if heartbeat_task:
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass

        # Clean up any remaining transactions for this charge point
        if cp_id in current_transactions:
            for evse_id, trx_info in current_transactions[cp_id].items():
                if trx_info.get("charging_task"):
                    trx_info["charging_task"].cancel()
            del current_transactions[cp_id]


async def send_heartbeats(charge_point: OCPPCp):
    # Envia Heartbeat a cada 30 segundos
    while True:
        await asyncio.sleep(30)
        try:
            logger.info(f"CP {charge_point.id}: Enviando Heartbeat...")
            request = ocpp_call_v201.Heartbeat()
            await charge_point.call(request)
            logger.info(f"CP {charge_point.id}: Heartbeat enviado.")
        except Exception as e:
            logger.error(f"CP {charge_point.id}: Erro ao enviar Heartbeat: {e}")
            break  # Sair do loop se houver um erro, indicando que a conexão pode ter caído


@on('RequestStartTransaction')
async def on_request_start_transaction(charge_point: OCPPCp, evse_id: int, id_token: ocpp_datatypes_v201.IdTokenType, **kwargs):
    logger.info(f"CP {charge_point.id}: Recebido RequestStartTransaction para EVSE {evse_id} com ID Token '{id_token.id_token}'")

    # Simular que o CP sempre aceita a transação
    transaction_id = str(random.randint(1000, 9999))
    meter_start = random.randint(1000, 5000)

    # Iniciar a tarefa de envio de MeterValues para esta transação
    charging_task = asyncio.create_task(
        _send_meter_values(charge_point, evse_id, transaction_id, meter_start)
    )

    # Armazenar informações da transação
    if charge_point.id not in current_transactions:
        current_transactions[charge_point.id] = {}
    current_transactions[charge_point.id][evse_id] = {
        "transaction_id": transaction_id,
        "meter_start": meter_start,
        "charging_task": charging_task,
        "id_token": id_token.id_token # Store the id_token for later use
    }

    response_payload = ocpp_call_v201.RequestStartTransactionPayload(
        status=ocpp_enums_v201.RequestStartStopStatusEnumType.accepted,
        transaction_id=transaction_id
    )
    return response_payload


@on('RequestStopTransaction')
async def on_request_stop_transaction(charge_point: OCPPCp, transaction_id: str, **kwargs):
    logger.info(f"CP {charge_point.id}: Recebido RequestStopTransaction para Transação {transaction_id}")

    # Encontrar e cancelar a tarefa de carregamento associada a esta transação
    found_transaction = False
    for evse_id, trx_info in current_transactions.get(charge_point.id, {}).items():
        if trx_info.get("transaction_id") == transaction_id:
            if trx_info.get("charging_task"):
                trx_info["charging_task"].cancel()
            del current_transactions[charge_point.id][evse_id]
            found_transaction = True
            logger.info(f"CP {charge_point.id}: Transação {transaction_id} no EVSE {evse_id} finalizada e tarefa de MeterValues cancelada.")
            break

    if not found_transaction:
        logger.warning(f"CP {charge_point.id}: Transação {transaction_id} não encontrada para parar.")

    response_payload = ocpp_call_v201.RequestStartStopStatusEnumType(
        status=ocpp_enums_v201.RequestStartStopStatusEnumType.accepted
    )
    return response_payload


if __name__ == '__main__':
    CSMS_URL = "ws://localhost:9000"


    async def main():
        logger.info("Iniciando simuladores de Charge Point...")

        tasks = []
        # Importante: Os IDs dos CPs aqui (CP_001, CP_002, CP_003) precisam ser os mesmos
        # que o simulador de EV vai tentar usar.
        charge_point_ids = ["CP_001", "CP_002", "CP_003"]

        for cp_id in charge_point_ids:
            task = asyncio.create_task(start_charge_point(cp_id, CSMS_URL))
            tasks.append(task)

        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            logger.info("Interrompido pelo usuário")
            # Cancel all tasks
            for task in tasks:
                task.cancel()
            # Wait for all tasks to complete cancellation
            await asyncio.gather(*tasks,
                                 return_exceptions=True)
        finally:
            logger.info("Simuladores de Charge Point finalizados.")

    asyncio.run(main())