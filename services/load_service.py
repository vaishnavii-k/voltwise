from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models import Reservation, Connector, Station


async def get_projected_load(
    db: AsyncSession,
    station_id: int,
    start_time,
    end_time,
    exclude_reservation_id: int | None = None,
):
    stmt = (
        select(Reservation, Connector)
        .join(Connector, Reservation.connector_id == Connector.id)
        .where(
            and_(
                Connector.station_id == station_id,
                Reservation.start_time < end_time,
                Reservation.end_time > start_time,
                Reservation.status.notin_(["cancelled", "completed"])
            )
        )
    )

    if exclude_reservation_id is not None:
        stmt = stmt.where(
            Reservation.id != exclude_reservation_id
        )

    result = await db.execute(stmt)
    overlapping = result.all()

    projected = sum(
        float(connector.max_power_kw)
        for reservation, connector in overlapping
    )

    station = await db.get(Station, station_id)

    capacity = (
        float(station.max_capacity_kw)
        if station else 0.0
    )

    return projected, capacity


async def can_allocate(
    db: AsyncSession,
    station_id: int,
    start_time,
    end_time,
    requested_kw: float
) -> tuple[bool, float]:

    projected, capacity = await get_projected_load(
        db, station_id, start_time, end_time
    )

    headroom = capacity - projected

    if headroom <= 0:
        return False, 0.0

    allocated = min(requested_kw, headroom)

    return True, allocated