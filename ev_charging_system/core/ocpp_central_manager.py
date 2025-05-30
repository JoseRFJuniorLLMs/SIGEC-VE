# ev_charging_system/core/ocpp_central_manager.py

import logging
from typing import Dict
from ocpp.v16 import ChargePoint as OCPPCp # Garanta que esta classe é a correta para a instância do CP

logger = logging.getLogger(__name__)

# Dicionário para armazenar as instâncias de ChargePoint conectadas
# Key: charge_point_id (string), Value: OCPPCp instance
connected_charge_points: Dict[str, OCPPCp] = {}

async def send_ocpp_command_to_cp(charge_point_id: str, command_name: str, payload: dict) -> bool:
    """
    Envia um comando OCPP para um Charge Point específico.
    Args:
        charge_point_id: O ID do Charge Point de destino.
        command_name: O nome do comando OCPP (ex: "RemoteStartTransaction", "Reset", "ChangeConfiguration", "ChangeAvailability").
                      Deve corresponder aos métodos 'send_<command_name.lower()>' na instância do ChargePoint.
        payload: Um dicionário contendo os parâmetros do comando.
    Returns:
        True se o comando foi enviado com sucesso e a resposta foi recebida (ou sem erro), False caso contrário.
    """
    if charge_point_id not in connected_charge_points:
        logger.warning(f"Charge Point {charge_point_id} not connected. Cannot send command {command_name}.")
        return False

    charge_point = connected_charge_points[charge_point_id]

    try:
        # A biblioteca OCPP dinamicamente cria métodos como send_remotestarttransaction
        # baseados nos nomes das ações.
        # Precisamos converter o command_name para o formato esperado pelo método send_
        method_name = f"send_{command_name.lower()}"
        if not hasattr(charge_point, method_name):
            logger.error(f"Charge Point instance does not have method '{method_name}' for command '{command_name}'.")
            return False

        # Chama o método dinamicamente
        ocpp_response = await getattr(charge_point, method_name)(**payload)

        # Loga a resposta do CP
        logger.info(f"CP {charge_point_id} response to {command_name}: {ocpp_response}")

        # Verifica o status da resposta (ex: "Accepted", "Rejected")
        # Isso pode variar por comando, mas muitos têm um campo 'status'.
        if hasattr(ocpp_response, 'status') and ocpp_response.status.upper() == 'ACCEPTED':
            return True
        elif hasattr(ocpp_response, 'status'):
            logger.warning(f"Command {command_name} to CP {charge_point_id} was not accepted. Status: {ocpp_response.status}")
            return False
        else:
            # Comando sem status explícito ou outro tipo de resposta
            return True # Assumimos sucesso se não houver erro

    except Exception as e:
        logger.error(f"Error sending command {command_name} to CP {charge_point_id}: {e}", exc_info=True)
        return False