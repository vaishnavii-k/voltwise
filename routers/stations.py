from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from database import get_db
from models import Station
from schemas import StationOut

router = APIRouter(prefix="/stations", tags=["stations"])


# GET ALL STATIONS
@router.get("/", response_model=list[StationOut])
async def list_stations(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Station).options(joinedload(Station.connectors))
    )

    return result.scalars().unique().all()


# GET STATION BY ID
@router.get("/{station_id}", response_model=StationOut)
async def get_station(
    station_id: int,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Station)
        .where(Station.id == station_id)
        .options(joinedload(Station.connectors))
    )

    station = result.scalars().unique().first()

    if not station:
        raise HTTPException(
            status_code=404,
            detail="Station not found"
        )

    return station