from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List

class ConnectorOut(BaseModel):
    id: int
    type: str
    max_power_kw: float
    class Config:
        from_attributes = True

class StationOut(BaseModel):
    id: int
    name: str
    location: str
    total_capacity_kw: float
    connectors: List[ConnectorOut] = []
    class Config:
        from_attributes = True

class SlotOut(BaseModel):
    id: int
    connector_id: int
    start_time: datetime
    end_time: datetime
    status: str
    price_per_kwh: float
    class Config:
        from_attributes = True

class ReservationRequest(BaseModel):
    slot_id: int
    user_id: str = Field(..., min_length=1)
    idempotency_key: Optional[str] = None

class ReservationOut(BaseModel):
    id: int
    slot_id: int
    user_id: str
    allocated_power_kw: float
    status: str
    created_at: Optional[datetime] = None  # <-- Made Optional
    class Config:
        from_attributes = True

class RecommendationRequest(BaseModel):
    user_id: str
    preferred_connector_type: Optional[str] = None
    urgent: bool = False
    max_price_per_kwh: Optional[float] = None

class RecommendationOut(BaseModel):
    slot_id: int
    station_name: str
    connector_type: str
    start_time: datetime
    end_time: datetime
    price_per_kwh: float
    score: float

class SessionOut(BaseModel):
    id: int
    reservation_id: int
    start_time: Optional[datetime] = None # <-- Made Optional
    end_time: Optional[datetime] = None
    energy_delivered_kwh: float
    status: str
    class Config:
        from_attributes = True

class InvoiceOut(BaseModel):
    id: int
    session_id: int
    user_id: str
    total_amount: float
    status: str
    created_at: Optional[datetime] = None # <-- Made Optional
    class Config:
        from_attributes = True