import asyncio
import logging
import websockets
from datetime import datetime, timezone
import time
import random

# MUDANÇA AQUI: Importar da versão 2.0.1
from ocpp.v201 import ChargePoint as OCPPCp
from ocpp.v201 import call_result as ocpp_call_result_v201
from ocpp.v201 import call as ocpp_call_v201
from ocpp.v201 import enums as ocpp_enums_v201
from ocpp.v201 import datatypes as ocpp_datatypes_v201
from ocpp.routing import on

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('charge_point_simulator')

# Dicionário para armazenar o estado das transações
current_transactions = {}  # {charge_point_id: {connector_id: {"transaction_id": "...", "meter_start": 0, "charging_task": None}}}


# --- Funções de Manipulação de Mensagens OCPP (AGORA PARA OCPP 2.0.1) ---
@on('BootNotification')
async def on_boot_notification(charge_point: OCPPCp, **kwargs):
    logger.info(f"CP {charge_point.id}: Recebida BootNotification: {kwargs}")
    return ocpp_call_result_v201.BootNotification(
        current_time=datetime.now(timezone.utc).isoformat(),
        interval=300,  # Enviar Heartbeat a cada 300 segundos
        status=ocpp_enums_v201.RegistrationStatus.Accepted
    )


async def _send_meter_values(charge_point: OCPPCp, connector_id: int, transaction_id: str, meter_start: int):
    """
    Função auxiliar para enviar MeterValues periodicamente.
    Simula o bloco J02.
    """
    logger.info(
        f"CP {charge_point.id}: Iniciando envio de MeterValues para transação {transaction_id} no conector {connector_id}.")
    current_meter = meter_start
    while True:
        await asyncio.sleep(5)  # Enviar a cada 5 segundos
        current_meter += random.randint(100, 500)  # Simular consumo em Wh (0.1 a 0.5 kWh)

        meter_value = ocpp_datatypes_v201.MeterValueType(
            timestamp=datetime.now(timezone.utc).isoformat(),
            sampled_value=[
                ocpp_datatypes_v201.SampledValueType(
                    value=str(current_meter),
                    unit=ocpp_enums_v201.MeasurandEnumType.Wh
                )
            ]
        )
        try:
            await charge_point.send(
                ocpp_call_v201.MeterValues(
                    evse_id=connector_id,
                    meter_value=[meter_value],
                    transaction_id=transaction_id
                )
            )
            logger.debug(
                f"CP {charge_point.id}: Enviado MeterValue: {current_meter} Wh para transação {transaction_id}")
        except Exception as e:
            logger.error(f"CP {charge_point.id}: Erro ao enviar MeterValue: {e}")
            break  # Sair do loop se houver erro

        # Verificar se a transação ainda está ativa para este CP e conector
        if charge_point.id not in current_transactions or \
                connector_id not in current_transactions[charge_point.id] or \
                current_transactions[charge_point.id][connector_id].get("transaction_id") != transaction_id:
            logger.info(
                f"CP {charge_point.id}: Transação {transaction_id} no conector {connector_id} encerrada, parando envio de MeterValues.")
            break


@on('RemoteStartTransaction')
async def on_remote_start_transaction(charge_point: OCPPCp, id_token: dict, connector_id: int, **kwargs):
    logger.info(
        f"CP {charge_point.id}: Recebida RemoteStartTransaction para conector {connector_id} com ID Token {id_token}")

    # Verificar se o conector já está em uma transação
    if charge_point.id in current_transactions and connector_id in current_transactions[charge_point.id]:
        logger.warning(
            f"CP {charge_point.id}: Conector {connector_id} já está em uma transação. Rejeitando RemoteStartTransaction.")
        return ocpp_call_result_v201.RemoteStartTransaction(status=ocpp_enums_v201.RequestStartStopStatus.Rejected)

    response_status = ocpp_enums_v201.RequestStartStopStatus.Accepted
    await charge_point.send(ocpp_call_result_v201.RemoteStartTransaction(status=response_status))

    if response_status == ocpp_enums_v201.RequestStartStopStatus.Accepted:
        logger.info(f"CP {charge_point.id}: Comando RemoteStartTransaction aceito. Iniciando transação no CP...")

        # Gerar um transaction_id realístico (ou usar um do CSMS se ele enviou)
        transaction_id = f"TRX-{charge_point.id}-{connector_id}-{int(time.time())}"

        # Simular leitura inicial do medidor
        meter_start = random.randint(1000, 5000)

        # Armazenar estado da transação
        if charge_point.id not in current_transactions:
            current_transactions[charge_point.id] = {}
        current_transactions[charge_point.id][connector_id] = {
            "transaction_id": transaction_id,
            "meter_start": meter_start,
            "id_token": id_token,
            "charging_task": None  # Tarefa para enviar MeterValues
        }

        # Envia TransactionEvent.Started para o CSMS (E01)
        await charge_point.send(
            ocpp_call_v201.TransactionEvent(
                event_type=ocpp_enums_v201.TransactionEventEnumType.Started,
                timestamp=datetime.now(timezone.utc).isoformat(),
                transaction_info=ocpp_datatypes_v201.TransactionType(transaction_id=transaction_id),
                seq_no=0,
                id_token=ocpp_datatypes_v201.IdTokenType(id_token=id_token['idToken'], type=id_token['type']),
                evse=ocpp_datatypes_v201.EVSEType(id=connector_id, connector_id=connector_id),
                meter_value=[  # Incluir meter_value inicial
                    ocpp_datatypes_v201.MeterValueType(
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        sampled_value=[
                            ocpp_datatypes_v201.SampledValueType(
                                value=str(meter_start),
                                unit=ocpp_enums_v201.MeasurandEnumType.Wh
                            )
                        ]
                    )
                ]
            )
        )
        logger.info(
            f"CP {charge_point.id}: Transação {transaction_id} iniciada no conector {connector_id}. Enviado TransactionEvent.Started.")

        # Atualizar status do conector para "Charging" (G02)
        await charge_point.send(
            ocpp_call_v201.StatusNotification(
                timestamp=datetime.now(timezone.utc).isoformat(),
                connector_status=ocpp_enums_v201.ConnectorStatusEnumType.Charging,
                evse_id=connector_id,
                connector_id=connector_id
            )
        )
        logger.info(f"CP {charge_point.id}: Status do conector {connector_id} atualizado para Charging.")

        # Iniciar tarefa para enviar MeterValues periodicamente (J02)
        charging_task = asyncio.create_task(
            _send_meter_values(charge_point, connector_id, transaction_id, meter_start)
        )
        current_transactions[charge_point.id][connector_id]["charging_task"] = charging_task

    return ocpp_call_result_v201.RemoteStartTransaction(status=response_status)


@on('RemoteStopTransaction')
async def on_remote_stop_transaction(charge_point: OCPPCp, transaction_id: str, **kwargs):
    logger.info(
        f"CP {charge_point.id}: Recebida RemoteStopTransaction para transação {transaction_id}")

    connector_id_to_stop = None
    if charge_point.id in current_transactions:
        for conn_id, trx_info in current_transactions[charge_point.id].items():
            if trx_info["transaction_id"] == transaction_id:
                connector_id_to_stop = conn_id
                break

    if connector_id_to_stop is None:
        logger.warning(
            f"CP {charge_point.id}: Transação {transaction_id} não encontrada. Rejeitando RemoteStopTransaction.")
        return ocpp_call_result_v201.RemoteStopTransaction(status=ocpp_enums_v201.RequestStartStopStatus.Rejected)

    response_status = ocpp_enums_v201.RequestStartStopStatus.Accepted
    await charge_point.send(ocpp_call_result_v201.RemoteStopTransaction(status=response_status))

    if response_status == ocpp_enums_v201.RequestStartStopStatus.Accepted:
        logger.info(
            f"CP {charge_point.id}: Comando RemoteStopTransaction aceito. Parando transação {transaction_id}...")

        trx_info = current_transactions[charge_point.id].pop(connector_id_to_stop)

        # Cancelar a tarefa de envio de MeterValues
        if trx_info["charging_task"]:
            trx_info["charging_task"].cancel()
            try:
                await trx_info["charging_task"]  # Aguardar cancelamento
            except asyncio.CancelledError:
                logger.debug(f"CP {charge_point.id}: Tarefa de MeterValues para {transaction_id} cancelada.")

        # Envia TransactionEvent.Ended para o CSMS (E02)
        meter_stop_value = trx_info["meter_start"] + random.randint(1000, 100000)  # Simular leitura final maior
        # Aumentar seq_no para o evento End. Assumindo que Start é seq_no=0, End será 1.
        # Em um cenário real, o CP manteria um contador de seq_no por transação.
        seq_no_end = 1
        await charge_point.send(
            ocpp_call_v201.TransactionEvent(
                event_type=ocpp_enums_v201.TransactionEventEnumType.Ended,
                timestamp=datetime.now(timezone.utc).isoformat(),
                transaction_info=ocpp_datatypes_v201.TransactionType(transaction_id=transaction_id),
                seq_no=seq_no_end,
                reason=ocpp_enums_v201.ReasonEnumType.Remote,
                meter_value=[  # Incluir meter_value final
                    ocpp_datatypes_v201.MeterValueType(
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        sampled_value=[
                            ocpp_datatypes_v201.SampledValueType(
                                value=str(meter_stop_value),
                                unit=ocpp_enums_v201.MeasurandEnumType.Wh
                            )
                        ]
                    )
                ]
            )
        )
        logger.info(f"CP {charge_point.id}: Transação {transaction_id} parada. Enviado TransactionEvent.Ended.")

        # Atualizar status do conector para disponível (G02)
        await charge_point.send(
            ocpp_call_v201.StatusNotification(
                timestamp=datetime.now(timezone.utc).isoformat(),
                connector_status=ocpp_enums_v201.ConnectorStatusEnumType.Available,
                evse_id=connector_id_to_stop,
                connector_id=connector_id_to_stop
            )
        )
        logger.info(f"CP {charge_point.id}: Status do conector {connector_id_to_stop} atualizado para Available.")

    return ocpp_call_result_v201.RemoteStopTransaction(status=response_status)


@on('Reset')
async def on_reset(charge_point: OCPPCp, type: str, **kwargs):
    logger.info(f"CP {charge_point.id}: Recebida mensagem Reset com tipo: {type}")
    # Simula o reset
    await asyncio.sleep(1)
    # Após o reset, o CP envia um novo BootNotification
    logger.info(f"CP {charge_point.id}: Simulando reinício após Reset. Enviando novo BootNotification.")

    # Limpar transações ativas para este CP
    if charge_point.id in current_transactions:
        for conn_id, trx_info in list(current_transactions[charge_point.id].items()):
            if trx_info and trx_info.get("charging_task"):
                trx_info["charging_task"].cancel()
                try:
                    await trx_info["charging_task"]
                except asyncio.CancelledError:
                    pass
            del current_transactions[charge_point.id][conn_id]
        if not current_transactions[charge_point.id]:
            del current_transactions[charge_point.id]

    await charge_point.send(
        ocpp_call_v201.BootNotification(
            reason=ocpp_enums_v201.BootReasonEnumType.RemoteReset,
            charging_station=ocpp_datatypes_v201.ChargingStationType(vendor_name="SIGEC", model="V1.0",
                                                                     serial_number=charge_point.id),
        )
    )
    return ocpp_call_result_v201.Reset(
        status=ocpp_enums_v201.ResetStatusEnumType.Accepted
    )


@on('ChangeConfiguration')  # Este handler no CP deve mapear para SetVariables no 2.0.1
async def on_change_configuration(charge_point: OCPPCp, **kwargs):
    logger.info(f"CP {charge_point.id}: Recebida ChangeConfiguration (mapeado para SetVariables): {kwargs}")
    # Adaptação para SetVariables no OCPP 2.0.1
    # Implementação completa exigiria parsing de 'kwargs' para construir set_variable_result
    # Para fins de simulação, vamos retornar um Accepted genérico.
    # No OCPP 2.0.1, SetVariables é o comando que substitui ChangeConfiguration.
    # Se o CSMS envia um ChangeConfiguration, a biblioteca ocpp-lib irá convertê-lo
    # para SetVariables e o CP receberia SetVariables.
    # No entanto, se o CSMS ainda envia um ChangeConfiguration (como em algumas transições),
    # este handler o capturaria. A resposta esperada seria um SetVariablesResponse.
    # Vamos simular uma resposta de SetVariables.
    return ocpp_call_result_v201.SetVariables(
        set_variable_result=[
            ocpp_datatypes_v201.SetVariableResultType(
                attribute_status=ocpp_enums_v201.SetVariableStatusEnumType.Accepted,
                component=ocpp_datatypes_v201.ComponentType(name="GenericComponent"),
                variable=ocpp_datatypes_v201.VariableType(name="GenericVariable")
            )
        ]
    )


@on('ChangeAvailability')
async def on_change_availability(charge_point: OCPPCp, evse_id: int, operational_status: str, **kwargs):
    logger.info(f"CP {charge_point.id}: Recebida ChangeAvailability para EVSE {evse_id}, status: {operational_status}")

    # Mapear operational_status para AvailabilityStatusEnumType (OCPP 2.0.1)
    status_enum = ocpp_enums_v201.ChangeAvailabilityStatusEnumType.Rejected
    new_connector_status = ocpp_enums_v201.ConnectorStatusEnumType.Unknown  # Default ou erro

    if operational_status == ocpp_enums_v201.OperationalStatusEnumType.Operative:
        status_enum = ocpp_enums_v201.ChangeAvailabilityStatusEnumType.Accepted
        new_connector_status = ocpp_enums_v201.ConnectorStatusEnumType.Available
    elif operational_status == ocpp_enums_v201.OperationalStatusEnumType.Inoperative:
        status_enum = ocpp_enums_v201.ChangeAvailabilityStatusEnumType.Accepted
        new_connector_status = ocpp_enums_v201.ConnectorStatusEnumType.Unavailable
    # No OCPP 2.0.1, ChangeAvailability não recebe connector_id separadamente do evse_id.
    # evse_id geralmente é o ID do conector para CPs simples.
    # A resposta é ChangeAvailabilityResponse.
    await charge_point.send(ocpp_call_result_v201.ChangeAvailability(status=status_enum))

    if status_enum == ocpp_enums_v201.ChangeAvailabilityStatusEnumType.Accepted:
        # Envia StatusNotification com o novo status
        await charge_point.send(
            ocpp_call_v201.StatusNotification(
                timestamp=datetime.now(timezone.utc).isoformat(),
                connector_status=new_connector_status,
                evse_id=evse_id,  # Usar evse_id como o ID do conector aqui
                connector_id=evse_id  # Em CPs simples, evse_id e connector_id são os mesmos
            )
        )
        logger.info(
            f"CP {charge_point.id}: Status do conector {evse_id} (EVSE {evse_id}) atualizado para {new_connector_status}.")

    return ocpp_call_result_v201.ChangeAvailability(status=status_enum)


async def start_charge_point(cp_id: str, csms_url: str):
    """
    Inicia um Charge Point simulado e o conecta ao CSMS.
    """
    try:
        # subprotocols para OCPP 2.0.1
        async with websockets.connect(csms_url + f"/{cp_id}", subprotocols=['ocpp2.0.1']) as ws:
            logger.info(f"CP {cp_id}: Conectado ao CSMS em {csms_url}")

            charge_point = OCPPCp(cp_id, ws)

            # Envia BootNotification inicial
            boot_payload = ocpp_call_v201.BootNotification(
                reason=ocpp_enums_v201.BootReasonEnumType.PowerUp,
                charging_station=ocpp_datatypes_v201.ChargingStationType(vendor_name="SIGEC", model="V1.0",
                                                                         serial_number=cp_id)
            )
            response = await charge_point.send(boot_payload)
            logger.info(f"CP {cp_id}: BootNotification enviado. Resposta: {response}")

            if response.status == ocpp_enums_v201.RegistrationStatus.Accepted:
                logger.info(f"CP {cp_id}: Conectado e aceito pelo CSMS.")

                # Enviar StatusNotification para todos os conectores (exemplo)
                # Assumindo 2 conectores por CP
                for i in range(1, 3):
                    await charge_point.send(
                        ocpp_call_v201.StatusNotification(
                            timestamp=datetime.now(timezone.utc).isoformat(),
                            connector_status=ocpp_enums_v201.ConnectorStatusEnumType.Available,
                            evse_id=i,  # No OCPP 2.0.1, evse_id é o identificador da EVSE
                            connector_id=i  # connector_id é o identificador do conector dentro da EVSE
                        )
                    )
                logger.info(f"CP {cp_id}: StatusNotification para conectores enviado.")

                # Mantém a conexão aberta para processar mensagens
                await asyncio.Future()
            else:
                logger.error(f"CP {cp_id}: Não aceito pelo CSMS. Status: {response.status}")

    except websockets.exceptions.ConnectionClosedOK:
        logger.info(f"CP {cp_id}: Conexão fechada normalmente pelo CSMS.")
    except Exception as e:
        logger.error(f"CP {cp_id}: Erro ao conectar Charge Point: {e}")


# --- Execução Principal ---
if __name__ == '__main__':
    # Importar random aqui para uso no main, se necessário (foi movido para _send_meter_values)
    # import random

    CSMS_URL = "ws://localhost:9000"


    async def main():
        logger.info("Iniciando simuladores de Charge Point...")
        # Rodar 2 CPs simulados em paralelo
        cp1_task = asyncio.create_task(start_charge_point("CP-SIGEC-001", CSMS_URL))
        cp2_task = asyncio.create_task(start_charge_point("CP-SIGEC-002", CSMS_URL))

        await asyncio.gather(cp1_task, cp2_task)


    asyncio.run(main())