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
    # Simulate meter values being sent periodically
    meter_value = meter_start
    while True:
        try:
            meter_value += random.randint(1, 5)  # Simulate energy consumption
            meter_data = [
                ocpp_datatypes_v201.MeterValue(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    sampled_value=[
                        ocpp_datatypes_v201.SampledValue(
                            value=str(meter_value),
                            measurand=ocpp_enums_v201.MeasurandType.energy_active_import_register,
                            unit_of_measure=ocpp_datatypes_v201.UnitOfMeasure(
                                unit=ocpp_enums_v201.MeasurandUnitType.wh
                            )
                        )
                    ]
                )
            ]

            # Criar a mensagem MeterValues para a versão 2.0.1
            meter_values_request = ocpp_call_v201.MeterValues(
                evse_id=evse_id,
                meter_value=meter_data,
                transaction_id=transaction_id
            )

            logger.info(
                f"CP {charge_point.id}: Enviando MeterValues para Transação {transaction_id}, EVSE {evse_id}: {meter_value} Wh")
            response = await charge_point.call(meter_values_request)

            # Aqui você pode adicionar lógica para verificar a resposta se necessário
            # Ex: if response.status == ocpp_enums_v201.RequestStartStopStatusType.accepted:
            #     logger.info("MeterValues aceito.")

            await asyncio.sleep(10)  # Send meter values every 10 seconds
        except asyncio.CancelledError:
            logger.info(
                f"CP {charge_point.id}: Envio de MeterValues cancelado para Transação {transaction_id}, EVSE {evse_id}.")
            break
        except Exception as e:
            logger.error(f"CP {charge_point.id}: Erro no envio de MeterValues: {e}")
            break


async def send_heartbeats(charge_point: OCPPCp):
    """Envia Heartbeat a cada intervalo."""
    while True:
        try:
            request = ocpp_call_v201.Heartbeat()
            await charge_point.call(request)
            logger.info(f"CP {charge_point.id}: Heartbeat enviado.")
            await asyncio.sleep(300)  # Intervalo de heartbeat (5 minutos)
        except asyncio.CancelledError:
            logger.info(f"CP {charge_point.id}: Heartbeat task cancelada.")
            break
        except Exception as e:
            logger.error(f"CP {charge_point.id}: Erro ao enviar Heartbeat: {e}")
            await asyncio.sleep(60)  # Tenta novamente após um tempo se houver erro


async def start_charge_point(cp_id: str, csms_url: str):
    logger.info(f"CP {cp_id}: Tentando conectar ao CSMS em {csms_url}...")
    heartbeat_task = None
    try:
        async with websockets.connect(csms_url, subprotocols=['ocpp2.0.1']) as websocket:
            charge_point = OCPPCp(cp_id, websocket)
            logger.info(f"CP {cp_id}: Conectado ao CSMS. Enviando BootNotification...")

            # Envia BootNotification
            boot_notification_request = ocpp_call_v201.BootNotification(
                reason=ocpp_enums_v201.BootReasonEnumType.PowerUp, # Linha corrigida aqui
                charging_station={
                    'model': 'EV-Charge-Simulator',
                    'vendor_name': 'SIGEC-VE',
                    'firmware_version': '1.0.0',
                    'serial_number': f'CP-SN-{cp_id.split("_")[1]}'
                }
            )

            response = await charge_point.call(boot_notification_request)

            if response.status == ocpp_enums_v201.RegistrationStatusType.accepted:
                logger.info(f"CP {cp_id}: Conectado e aceito pelo CSMS! Status: {response.status}")

                # Inicia a tarefa de heartbeat
                if not heartbeat_task:
                    heartbeat_task = asyncio.create_task(send_heartbeats(charge_point))

                # Exemplo: Simular um StatusNotification para um conector
                # (Assumindo que cada CP tem pelo menos um conector)
                for i in range(1, 2):  # Para cada conector (ex: conector 1)
                    status_notification_msg = ocpp_call_v201.StatusNotification(
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        connector_status=ocpp_enums_v201.ConnectorStatusType.available,
                        evse_id=i,
                        connector_id=i
                    )
                    await charge_point.call(status_notification_msg)
                await charge_point.start()
            else:
                logger.error(f"CP {cp_id}: Não aceito pelo CSMS. Status: {response.status}")

    except websockets.exceptions.ConnectionClosedOK:
        logger.info(f"CP {cp_id}: Conexão fechada normalmente pelo CSMS.")
    except websockets.exceptions.ConnectionClosedError as e:
        logger.warning(f"CP {cp_id}: Conexão fechada inesperadamente: {e}")
    except Exception as e:
        logger.error(f"CP {cp_id}: Erro ao conectar Charge Point: {e}")
    finally:
        # Clean up heartbeat task
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


if __name__ == '__main__':
    CSMS_URL = "ws://localhost:9000"


    async def main():
        logger.info("Iniciando simuladores de Charge Point...")

        tasks = []
        charge_point_ids = ["CP_001", "CP_002", "CP_003"]  # Added one more for testing

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
                                 return_exceptions=True)  # Use return_exceptions=True to avoid errors for already cancelled tasks
        finally:
            logger.info("Simuladores de Charge Point finalizados.")


    asyncio.run(main())