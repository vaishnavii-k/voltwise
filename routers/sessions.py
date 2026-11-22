from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from schemas import SessionOut
from services.session_service import start_session, stop_session

router = APIRouter(prefix="/sessions", tags=["sessions"])


# START CHARGING SESSION
@router.post("/{reservation_id}/start", response_model=SessionOut)
async def begin_charging(
    reservation_id: int,
    db: AsyncSession = Depends(get_db)
):
    try:
        return await start_session(db, reservation_id)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# STOP CHARGING SESSION
@router.post("/{session_id}/stop", response_model=SessionOut)
async def end_charging(
    session_id: int,
    db: AsyncSession = Depends(get_db)
):
    try:
        return await stop_session(db, session_id)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))