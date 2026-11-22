from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Connector
from schemas import ConnectorOut, RecommendationRequest, RecommendationOut
from services.recommendation_service import get_recommendations

router = APIRouter(prefix="/connectors", tags=["connectors"])


# LIST AVAILABLE CONNECTORS
@router.get("/", response_model=list[ConnectorOut])
async def list_connectors(
    station_id: int | None = Query(None),
    status: str | None = Query("available"),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Connector)

    if station_id is not None:
        stmt = stmt.where(Connector.station_id == station_id)

    if status:
        stmt = stmt.where(Connector.status == status)

    result = await db.execute(stmt.order_by(Connector.id))

    return result.scalars().all()


# RECOMMEND CONNECTORS
@router.post("/recommend", response_model=list[RecommendationOut])
async def recommend(
    body: RecommendationRequest,
    db: AsyncSession = Depends(get_db)
):
    recommendations = await get_recommendations(
        db,
        preferred_type=body.preferred_connector_type,
        urgent=body.urgent,
        max_price=body.max_price_per_kwh,
    )

    return [
        RecommendationOut(**item)
        for item in recommendations
    ]