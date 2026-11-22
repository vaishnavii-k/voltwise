from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models import Reservation, Connector, User


async def create_reservation(
    db: AsyncSession,
    connector_id: int,
    user_id: UUID,
    start_time: datetime,
    end_time: datetime
) -> Reservation:

    # Validate reservation time
    if start_time >= end_time:
        raise ValueError("End time must be after start time")

    # Check whether the user exists
    user_result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = user_result.scalars().first()

    if not user:
        raise ValueError("User not found")

    # Lock the connector while creating a reservation
    connector_result = await db.execute(
        select(Connector)
        .where(Connector.id == connector_id)
        .with_for_update()
    )
    connector = connector_result.scalars().first()

    if not connector:
        raise ValueError("Connector not found")

    if connector.status != "available":
        raise ValueError("Connector is not available")

    # Check for overlapping reservations
    overlap_result = await db.execute(
        select(Reservation).where(
            and_(
                Reservation.connector_id == connector_id,
                Reservation.start_time < end_time,
                Reservation.end_time > start_time,
                Reservation.status != "cancelled"
            )
        )
    )

    existing_reservation = overlap_result.scalars().first()

    if existing_reservation:
        raise ValueError("Connector is already reserved during this time")

    # Create reservation
    new_reservation = Reservation(
        user_id=user_id,
        connector_id=connector_id,
        start_time=start_time,
        end_time=end_time,
        created_at=datetime.now(timezone.utc)
    )

    db.add(new_reservation)

    await db.commit()
    await db.refresh(new_reservation)

    return new_reservation


async def cancel_reservation(
    db: AsyncSession,
    reservation_id: int
) -> Reservation:

    result = await db.execute(
        select(Reservation)
        .where(Reservation.id == reservation_id)
        .with_for_update()
    )

    reservation = result.scalars().first()

    if not reservation:
        raise ValueError("Reservation not found")

    if reservation.status == "cancelled":
        raise ValueError("Reservation is already cancelled")

    reservation.status = "cancelled"

    await db.commit()
    await db.refresh(reservation)

    return reservation


async def get_user_reservations(
    db: AsyncSession,
    user_id: UUID
):
    result = await db.execute(
        select(Reservation)
        .where(Reservation.user_id == user_id)
        .order_by(Reservation.created_at.desc())
    )

    return result.scalars().all()