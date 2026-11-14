from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime, timezone

class Station(Base):
    __tablename__ = "stations"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    location = Column(String)
    total_capacity_kw = Column(Float)
    connectors = relationship("Connector", back_populates="station")

class Connector(Base):
    __tablename__ = "connectors"
    id = Column(Integer, primary_key=True, index=True)
    station_id = Column(Integer, ForeignKey("stations.id"))
    type = Column(String)
    max_power_kw = Column(Float)
    station = relationship("Station", back_populates="connectors")
    slots = relationship("Slot", back_populates="connector")

class Slot(Base):
    __tablename__ = "slots"
    id = Column(Integer, primary_key=True, index=True)
    connector_id = Column(Integer, ForeignKey("connectors.id"))
    start_time = Column(DateTime(timezone=True))
    end_time = Column(DateTime(timezone=True))
    status = Column(String, default="available")
    price_per_kwh = Column(Float)
    connector = relationship("Connector", back_populates="slots")
    reservations = relationship("Reservation", back_populates="slot")

class Reservation(Base):
    __tablename__ = "reservations"
    id = Column(Integer, primary_key=True, index=True)
    slot_id = Column(Integer, ForeignKey("slots.id"), nullable=False)
    user_id = Column(String, index=True, nullable=False)
    idempotency_key = Column(String, unique=True, index=True, nullable=True)
    allocated_power_kw = Column(Float, nullable=False)
    status = Column(String, default="confirmed")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    slot = relationship("Slot", back_populates="reservations")
    session = relationship("ChargingSession", back_populates="reservation", uselist=False)

class ChargingSession(Base):
    __tablename__ = "charging_sessions"
    id = Column(Integer, primary_key=True, index=True)
    reservation_id = Column(Integer, ForeignKey("reservations.id"), nullable=False)
    start_time = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    end_time = Column(DateTime(timezone=True), nullable=True)
    energy_delivered_kwh = Column(Float, default=0.0)
    status = Column(String, default="active")
    reservation = relationship("Reservation", back_populates="session")
    invoice = relationship("Invoice", back_populates="session", uselist=False)

class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("charging_sessions.id"), unique=True, nullable=False)
    user_id = Column(String, index=True, nullable=False)
    total_amount = Column(Float, nullable=False)
    status = Column(String, default="unpaid")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    session = relationship("ChargingSession", back_populates="invoice")