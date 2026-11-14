from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from datetime import datetime, timezone
from database import get_db
from schemas import ReservationRequest, ReservationOut
from services.reservation_service import create_reservation, cancel_reservation, get_user_reservations

router = APIRouter(prefix="/reservations", tags=["reservations"])

@router.post("/", response_model=ReservationOut, status_code=status.HTTP_201_CREATED)
async def book_slot(body: ReservationRequest, db: AsyncSession = Depends(get_db)):
    try:
        res = await create_reservation(db, body.slot_id, body.user_id, body.idempotency_key)
        
        # MANUAL FIX: Construct the output explicitly
        return ReservationOut(
            id=res.id,
            slot_id=res.slot_id,
            user_id=res.user_id,
            allocated_power_kw=res.allocated_power_kw,
            status=res.status,
            created_at=res.created_at or datetime.now(timezone.utc)
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{reservation_id}", response_model=ReservationOut)
async def cancel_booking(reservation_id: int, db: AsyncSession = Depends(get_db)):
    try:
        res = await cancel_reservation(db, reservation_id)
        return ReservationOut(
            id=res.id,
            slot_id=res.slot_id,
            user_id=res.user_id,
            allocated_power_kw=res.allocated_power_kw,
            status=res.status,
            created_at=res.created_at or datetime.now(timezone.utc)
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/user/{user_id}", response_model=List[ReservationOut])
async def list_my_reservations(user_id: str, db: AsyncSession = Depends(get_db)):
    return await get_user_reservations(db, user_id)