from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import Slot, Reservation, Connector

async def create_reservation(db: AsyncSession, slot_id: int, user_id: str, idempotency_key: str | None) -> Reservation:
    if idempotency_key:
        stmt = select(Reservation).where(Reservation.idempotency_key == idempotency_key)
        result = await db.execute(stmt)
        existing = result.scalars().first()
        if existing:
            return existing

    stmt = select(Slot).where(Slot.id == slot_id).with_for_update()
    result = await db.execute(stmt)
    slot = result.scalars().first()

    if not slot:
        raise ValueError("Slot not found")
    if slot.status != "available":
        raise ValueError("Slot is already booked or unavailable")

    conn_stmt = select(Connector).where(Connector.id == slot.connector_id)
    conn_result = await db.execute(conn_stmt)
    connector = conn_result.scalars().first()
    allocated_power = connector.max_power_kw if connector else 50.0

    slot.status = "reserved"
    
    # THE FIX: Explicitly set created_at here
    new_reservation = Reservation(
        slot_id=slot.id,
        user_id=user_id,
        status="confirmed",
        idempotency_key=idempotency_key,
        allocated_power_kw=allocated_power,
        created_at=datetime.now(timezone.utc) 
    )
    
    db.add(new_reservation)
    await db.commit()
    await db.refresh(new_reservation)
    return new_reservation

async def cancel_reservation(db: AsyncSession, reservation_id: int) -> Reservation:
    stmt = select(Reservation).where(Reservation.id == reservation_id)
    result = await db.execute(stmt)
    reservation = result.scalars().first()

    if not reservation:
        raise ValueError("Reservation not found")
    if reservation.status == "cancelled":
        raise ValueError("Reservation is already cancelled")

    reservation.status = "cancelled"

    slot_stmt = select(Slot).where(Slot.id == reservation.slot_id).with_for_update()
    slot_result = await db.execute(slot_stmt)
    slot = slot_result.scalars().first()
    
    if slot:
        slot.status = "available"

    await db.commit()
    await db.refresh(reservation)
    return reservation

async def get_user_reservations(db: AsyncSession, user_id: str):
    stmt = select(Reservation).where(Reservation.user_id == user_id).order_by(Reservation.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()