from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import Slot, Reservation, ChargingSession, Invoice

async def start_session(db: AsyncSession, reservation_id: int) -> ChargingSession:
    stmt = select(Reservation).where(Reservation.id == reservation_id)
    result = await db.execute(stmt)
    reservation = result.scalars().first()

    if not reservation:
        raise ValueError("Reservation not found")
    if reservation.status != "confirmed":
        raise ValueError("Reservation is not in a confirmed state")

    session = ChargingSession(
        reservation_id=reservation.id, 
        status="active",
        start_time=datetime.now(timezone.utc) # Explicitly set
    )
    db.add(session)

    slot_stmt = select(Slot).where(Slot.id == reservation.slot_id).with_for_update()
    slot_result = await db.execute(slot_stmt)
    slot = slot_result.scalars().first()
    if slot:
        slot.status = "charging"

    reservation.status = "active"
    await db.commit()
    await db.refresh(session)
    return session

async def stop_session(db: AsyncSession, session_id: int) -> ChargingSession:
    stmt = select(ChargingSession).where(ChargingSession.id == session_id)
    result = await db.execute(stmt)
    session = result.scalars().first()

    if not session:
        raise ValueError("Session not found")
    if session.status == "completed":
        raise ValueError("Session is already completed")

    session.end_time = datetime.now(timezone.utc)
    session.status = "completed"
    session.energy_delivered_kwh = 50.0 

    res_stmt = select(Reservation).where(Reservation.id == session.reservation_id)
    res_result = await db.execute(res_stmt)
    reservation = res_result.scalars().first()

    if reservation:
        reservation.status = "completed"
        slot_stmt = select(Slot).where(Slot.id == reservation.slot_id).with_for_update()
        slot_result = await db.execute(slot_stmt)
        slot = slot_result.scalars().first()
        
        if slot:
            slot.status = "available" 
            total_cost = round(session.energy_delivered_kwh * slot.price_per_kwh, 2)
            new_invoice = Invoice(
                session_id=session.id,
                user_id=reservation.user_id,
                total_amount=total_cost,
                status="unpaid",
                created_at=datetime.now(timezone.utc) # Explicitly set
            )
            db.add(new_invoice)

    await db.commit()
    await db.refresh(session)
    return session