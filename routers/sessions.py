from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from database import get_db
from schemas import SessionOut
from services.session_service import start_session, stop_session

router = APIRouter(prefix="/sessions", tags=["sessions"])

@router.post("/{reservation_id}/start", response_model=SessionOut)
async def begin_charging(reservation_id: int, db: AsyncSession = Depends(get_db)):
    try:
        s = await start_session(db, reservation_id)
        return SessionOut(
            id=s.id,
            reservation_id=s.reservation_id,
            start_time=s.start_time or datetime.now(timezone.utc),
            end_time=s.end_time,
            energy_delivered_kwh=s.energy_delivered_kwh,
            status=s.status
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{session_id}/stop", response_model=SessionOut)
async def end_charging(session_id: int, db: AsyncSession = Depends(get_db)):
    try:
        s = await stop_session(db, session_id)
        return SessionOut(
            id=s.id,
            reservation_id=s.reservation_id,
            start_time=s.start_time or datetime.now(timezone.utc),
            end_time=s.end_time,
            energy_delivered_kwh=s.energy_delivered_kwh,
            status=s.status
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))