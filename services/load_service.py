from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from models import Slot, Connector, Station

async def get_projected_load(
    db: AsyncSession,
    station_id: int,
    start_time,
    end_time,
    exclude_slot_id: int | None = None,
):
    stmt = (
        select(Slot)
        .join(Connector, Slot.connector_id == Connector.id)
        .where(
            Connector.station_id == station_id,
            Slot.status == "booked",
            Slot.start_time < end_time,
            Slot.end_time > start_time,
        )
        .options(joinedload(Slot.connector))
    )
    if exclude_slot_id:
        stmt = stmt.where(Slot.id != exclude_slot_id)

    result = await db.execute(stmt)
    overlapping = result.scalars().all()
    projected = sum(c.connector.max_power_kw for c in overlapping)

    station = await db.get(Station, station_id)
    return projected, station.total_capacity_kw if station else 0.0


async def can_allocate(
    db: AsyncSession, station_id: int, start_time, end_time, requested_kw: float
) -> tuple[bool, float]:
    projected, capacity = await get_projected_load(db, station_id, start_time, end_time)
    headroom = capacity - projected

    if headroom <= 0:
        return False, 0.0

    allocated = min(requested_kw, headroom)
    return True, allocated