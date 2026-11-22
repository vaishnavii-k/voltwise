from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from uuid import UUID


# USERS
class UserOut(BaseModel):
    id: UUID
    full_name: str
    email: str
    phone: Optional[str] = None
    role: Optional[str] = None

    class Config:
        from_attributes = True


# CONNECTORS
class ConnectorOut(BaseModel):
    id: int
    station_id: int
    connector_type: str
    max_power_kw: float
    status: Optional[str] = None

    class Config:
        from_attributes = True


# STATIONS
class StationOut(BaseModel):
    id: int
    station_name: str
    location: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    max_capacity_kw: float
    is_active: Optional[bool] = None
    connectors: list[ConnectorOut] = []

    class Config:
        from_attributes = True


# RESERVATIONS
class ReservationRequest(BaseModel):
    connector_id: int
    user_id: UUID
    start_time: datetime
    end_time: datetime


class ReservationOut(BaseModel):
    id: int
    user_id: UUID
    connector_id: int
    start_time: datetime
    end_time: datetime
    status: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# RECOMMENDATIONS
class RecommendationRequest(BaseModel):
    user_id: UUID
    preferred_connector_type: Optional[str] = None
    urgent: bool = False
    max_price_per_kwh: Optional[float] = None


# CHARGING SESSIONS
class SessionOut(BaseModel):
    id: int
    reservation_id: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    energy_consumed_kwh: Optional[float] = None
    status: Optional[str] = None

    class Config:
        from_attributes = True


# PAYMENTS
class PaymentOut(BaseModel):
    id: int
    session_id: int
    amount: float
    payment_status: Optional[str] = None
    payment_method: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class RecommendationOut(BaseModel):
    connector_id: int
    station_name: str
    connector_type: str
    max_power_kw: float
    price_per_kwh: float
    is_reserved: bool
    score: float        