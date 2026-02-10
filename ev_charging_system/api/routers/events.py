from fastapi import APIRouter, Depends, HTTPException, status
from ev_charging_system.core.ocpp_server import connected_charge_points, send_ocpp_command
from ev_charging_system.api.schemas import EVPlugIn, EVUnPlug
from ocpp.v201 import enums as ocpp_enums_v201
import logging

router = APIRouter(prefix="/api/ev_events", tags=["EV Simulation Events"])
logger = logging.getLogger(__name__)

@router.post("/plug_in", summary="Simulate EV Plug-in event and initiate charging")
async def ev_plug_in_event(event: EVPlugIn):
    logger.info(f"API: EV {event.ev_id} plugged into CP {event.charge_point_id}, connector {event.connector_id}")

    if event.charge_point_id not in connected_charge_points:
        raise HTTPException(status_code=404, detail=f"Charge Point {event.charge_point_id} is not connected via OCPP.")

    id_token_payload = {
        "idToken": event.ev_id,
        "type": "ISO15118Certificate"
    }

    try:
        ocpp_response = await send_ocpp_command(
            event.charge_point_id,
            "RemoteStartTransaction",
            id_token=id_token_payload,
            connector_id=event.connector_id
        )
        logger.info(f"OCPP Command (RemoteStartTransaction) sent to {event.charge_point_id}. Response: {ocpp_response.to_dict()}")

        if ocpp_response.status == ocpp_enums_v201.RequestStartStopStatus.Accepted:
            return {
                "message": "EV Plug-in event received and RemoteStartTransaction sent to CP.",
                "ocpp_response": ocpp_response.to_dict(),
                "transactionId": f"TEMP_{event.charge_point_id}_{event.connector_id}_{event.ev_id}"
            }
        else:
            raise HTTPException(status_code=400, detail=f"RemoteStartTransaction rejected by CP: {ocpp_response.status}")

    except Exception as e:
        logger.error(f"Failed to send RemoteStartTransaction to {event.charge_point_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to initiate charge: {e}")

@router.post("/unplug", summary="Simulate EV Unplug event and stop charging")
async def ev_unplug_event(event: EVUnPlug):
    logger.info(f"API: EV {event.ev_id} unplugged from CP {event.charge_point_id}, connector {event.connector_id}, transaction {event.transaction_id}")

    if event.charge_point_id not in connected_charge_points:
        raise HTTPException(status_code=404, detail=f"Charge Point {event.charge_point_id} is not connected via OCPP.")

    try:
        ocpp_response = await send_ocpp_command(
            event.charge_point_id,
            "RemoteStopTransaction",
            transaction_id=event.transaction_id
        )
        logger.info(f"OCPP Command (RemoteStopTransaction) sent to {event.charge_point_id}. Response: {ocpp_response.to_dict()}")

        if ocpp_response.status == ocpp_enums_v201.RequestStartStopStatus.Accepted:
            return {
                "message": "EV Unplug event received and RemoteStopTransaction sent to CP.",
                "ocpp_response": ocpp_response.to_dict()
            }
        else:
            raise HTTPException(status_code=400, detail=f"RemoteStopTransaction rejected by CP: {ocpp_response.status}")

    except Exception as e:
        logger.error(f"Failed to send RemoteStopTransaction to {event.charge_point_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to stop charge: {e}")
