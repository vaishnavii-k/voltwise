from sqlalchemy import (
    Column, BigInteger, String, Numeric, Boolean,
    DateTime, ForeignKey
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database import Base


# 1. USERS
class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True)
    full_name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    role = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=True)

    reservations = relationship("Reservation", back_populates="user")


# 2. STATIONS
class Station(Base):
    __tablename__ = "stations"

    id = Column(BigInteger, primary_key=True, index=True)
    station_name = Column(String, nullable=False)
    location = Column(String, nullable=False)
    latitude = Column(Numeric, nullable=True)
    longitude = Column(Numeric, nullable=True)
    max_capacity_kw = Column(Numeric, nullable=False)
    is_active = Column(Boolean, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=True)

    connectors = relationship("Connector", back_populates="station")
    tariffs = relationship("Tariff", back_populates="station")


# 3. CONNECTORS
class Connector(Base):
    __tablename__ = "connectors"

    id = Column(BigInteger, primary_key=True, index=True)
    station_id = Column(
        BigInteger, ForeignKey("stations.id"), nullable=False
    )
    connector_type = Column(String, nullable=False)
    max_power_kw = Column(Numeric, nullable=False)
    status = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=True)

    station = relationship("Station", back_populates="connectors")
    reservations = relationship("Reservation", back_populates="connector")


# 4. TARIFFS
class Tariff(Base):
    __tablename__ = "tariffs"

    id = Column(BigInteger, primary_key=True, index=True)
    station_id = Column(
        BigInteger, ForeignKey("stations.id"), nullable=True
    )
    price_per_kwh = Column(Numeric, nullable=False)
    valid_from = Column(DateTime(timezone=True), nullable=True)
    valid_until = Column(DateTime(timezone=True), nullable=True)

    station = relationship("Station", back_populates="tariffs")


# 5. RESERVATIONS
class Reservation(Base):
    __tablename__ = "reservations"

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    connector_id = Column(
        BigInteger, ForeignKey("connectors.id"), nullable=False
    )
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    status = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="reservations")
    connector = relationship("Connector", back_populates="reservations")
    sessions = relationship("ChargingSession", back_populates="reservation")


# 6. CHARGING SESSIONS
class ChargingSession(Base):
    __tablename__ = "charging_sessions"

    id = Column(BigInteger, primary_key=True, index=True)
    reservation_id = Column(
        BigInteger, ForeignKey("reservations.id"), nullable=True
    )
    start_time = Column(DateTime(timezone=True), nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=True)
    energy_consumed_kwh = Column(Numeric, nullable=True)
    status = Column(String, nullable=True)

    reservation = relationship("Reservation", back_populates="sessions")
    energy_readings = relationship(
        "EnergyReading", back_populates="session"
    )
    payments = relationship("Payment", back_populates="session")


# 7. ENERGY READINGS
class EnergyReading(Base):
    __tablename__ = "energy_readings"

    id = Column(BigInteger, primary_key=True, index=True)
    session_id = Column(
        BigInteger, ForeignKey("charging_sessions.id"), nullable=False
    )
    recorded_at = Column(DateTime(timezone=True), nullable=True)
    energy_kwh = Column(Numeric, nullable=False)
    power_kw = Column(Numeric, nullable=True)

    session = relationship("ChargingSession", back_populates="energy_readings")


# 8. PAYMENTS
class Payment(Base):
    __tablename__ = "payments"

    id = Column(BigInteger, primary_key=True, index=True)
    session_id = Column(
        BigInteger, ForeignKey("charging_sessions.id"), nullable=False
    )
    amount = Column(Numeric, nullable=False)
    payment_status = Column(String, nullable=True)
    payment_method = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=True)

    session = relationship("ChargingSession", back_populates="payments")