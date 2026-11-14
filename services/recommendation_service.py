from datetime import datetime, timezone
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from models import Slot, Connector, Station

def score_slot(slot: Slot, connector: Connector, urgent: bool, max_price: float | None) -> float:
    score = 0.0
    now = datetime.now(timezone.utc)
    
    start_time = slot.start_time
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)
        
    wait_min = max(0, (start_time - now).total_seconds() / 60)
    score += max(0, 40 - (wait_min / 15))
    score += max(0, 30 - slot.price_per_kwh)
    score += min(10, connector.max_power_kw / 10)

    if urgent:
        end_time = slot.end_time
        if end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=timezone.utc)
        duration_min = (end_time - start_time).total_seconds() / 60
        score += 20 if duration_min <= 60 else 5 if duration_min <= 120 else 0

    if max_price is not None and slot.price_per_kwh > max_price:
        score -= 50
        
    return round(score, 2)

async def get_recommendations(
    db: AsyncSession, preferred_type: str | None, urgent: bool, max_price: float | None, limit: int = 5,
):
    now = datetime.now(timezone.utc)
    stmt = (
        select(Slot)
        .join(Connector, Slot.connector_id == Connector.id)
        .join(Station, Connector.station_id == Station.id)
        .options(joinedload(Slot.connector).joinedload(Connector.station))
        .where(Slot.status == "available", Slot.start_time > now)
    )
    
    if preferred_type:
        stmt = stmt.where(func.lower(Connector.type) == preferred_type.lower())

    result = await db.execute(stmt)
    slots = result.scalars().all()
    ranked = [(score_slot(s, s.connector, urgent, max_price), s) for s in slots]
    ranked.sort(key=lambda x: x[0], reverse=True)
    return ranked[:limit]