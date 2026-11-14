from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from models import Slot, Connector
from schemas import SlotOut, RecommendationRequest, RecommendationOut
from services.recommendation_service import get_recommendations

router = APIRouter(prefix="/slots", tags=["slots"])

@router.get("/", response_model=list[SlotOut])
async def list_slots(
    station_id: int | None = Query(None),
    status: str | None = Query("available"),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Slot).join(Connector, Slot.connector_id == Connector.id)
    if station_id:
        stmt = stmt.where(Connector.station_id == station_id)
    if status:
        stmt = stmt.where(Slot.status == status)
    result = await db.execute(stmt.order_by(Slot.start_time))
    return result.scalars().all()

@router.post("/recommend", response_model=list[RecommendationOut])
async def recommend(body: RecommendationRequest, db: AsyncSession = Depends(get_db)):
    ranked = await get_recommendations(
        db,
        preferred_type=body.preferred_connector_type,
        urgent=body.urgent,
        max_price=body.max_price_per_kwh,
    )
    out = []
    for score, s in ranked:
        out.append(
            RecommendationOut(
                slot_id=s.id,
                station_name=s.connector.station.name,
                connector_type=s.connector.type,
                start_time=s.start_time,
                end_time=s.end_time,
                price_per_kwh=s.price_per_kwh,
                score=score,
            )
        )
    return out