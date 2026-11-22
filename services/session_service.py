from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Reservation, ChargingSession


async def start_session(
    db: AsyncSession,
    reservation_id: int
) -> ChargingSession:

    result = await db.execute(
        select(Reservation)
        .where(Reservation.id == reservation_id)
        .with_for_update()
    )

    reservation = result.scalars().first()

    if not reservation:
        raise ValueError("Reservation not found")

    if reservation.status != "confirmed":
        raise ValueError("Reservation is not in a confirmed state")

    session = ChargingSession(
        reservation_id=reservation.id,
        status="active",
        start_time=datetime.now(timezone.utc)
    )

    db.add(session)
    reservation.status = "active"

    await db.commit()
    await db.refresh(session)

    return session


async def stop_session(
    db: AsyncSession,
    session_id: int
) -> ChargingSession:

    result = await db.execute(
        select(ChargingSession)
        .where(ChargingSession.id == session_id)
        .with_for_update()
    )

    session = result.scalars().first()

    if not session:
        raise ValueError("Session not found")

    if session.status == "completed":
        raise ValueError("Session is already completed")

    session.end_time = datetime.now(timezone.utc)
    session.status = "completed"

    if session.reservation_id is not None:
        reservation_result = await db.execute(
            select(Reservation)
            .where(Reservation.id == session.reservation_id)
            .with_for_update()
        )

        reservation = reservation_result.scalars().first()

        if reservation:
            reservation.status = "completed"

    await db.commit()
    await db.refresh(session)

    return session