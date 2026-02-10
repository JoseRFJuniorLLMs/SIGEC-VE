from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from ocpp.v201 import enums as ocpp_enums_v201

# --- EV Event Models ---
class EVPlugIn(BaseModel):
    ev_id: str
    charge_point_id: str
    connector_id: int

class EVUnPlug(BaseModel):
    ev_id: str
    charge_point_id: str
    connector_id: int
    transaction_id: str

# --- Charge Point Models ---
class ChargePointCreate(BaseModel):
    charge_point_id: str = Field(..., description="Unique ID of the Charge Point")
    vendor_name: str = Field("Unknown", description="Vendor name of the Charge Point")
    model: str = Field("Unknown", description="Model of the Charge Point")

class ChargePointResponse(BaseModel):
    charge_point_id: str
    vendor_name: str
    model: str
    status: str
    created_at: datetime

    class Config:
        orm_mode = True

# --- User Models ---
class UserCreate(BaseModel):
    user_id: str
    name: str
    email: str
    phone: Optional[str] = None
    id_tag: Optional[str] = None
    is_active: bool = True

class UserResponse(BaseModel):
    user_id: str
    name: str
    email: str
    phone: Optional[str]
    id_tag: Optional[str]
    is_active: bool
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        orm_mode = True

# --- Command Models ---
class RemoteStartRequest(BaseModel):
    connector_id: int
    id_token: str
    id_token_type: str = "ISO15118Certificate"

class RemoteStopRequest(BaseModel):
    transaction_id: str

class ResetRequest(BaseModel):
    reset_type: str = Field(..., description="Type of reset (Hard or Soft)")

class ChangeAvailabilityRequest(BaseModel):
    connector_id: int
    operational_status: str = Field(..., description="Availability status (Operative or Inoperative)")
