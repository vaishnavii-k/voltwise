from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from database import get_db
from schemas import ReservationRequest, ReservationOut
from services.reservation_service import (
    create_reservation,
    cancel_reservation,
    get_user_reservations
)

router = APIRouter(prefix="/reservations", tags=["reservations"])


# CREATE RESERVATION
@router.post(
    "/",
    response_model=ReservationOut,
    status_code=status.HTTP_201_CREATED
)
async def book_reservation(
    body: ReservationRequest,
    db: AsyncSession = Depends(get_db)
):
    try:
        return await create_reservation(
            db=db,
            connector_id=body.connector_id,
            user_id=body.user_id,
            start_time=body.start_time,
            end_time=body.end_time
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# CANCEL RESERVATION
@router.delete("/{reservation_id}", response_model=ReservationOut)
async def cancel_booking(
    reservation_id: int,
    db: AsyncSession = Depends(get_db)
):
    try:
        return await cancel_reservation(db, reservation_id)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# GET USER RESERVATIONS
@router.get("/user/{user_id}", response_model=List[ReservationOut])
async def list_my_reservations(
    user_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    return await get_user_reservations(db, user_id)