from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from database import get_db
from schemas import PaymentOut
from services.payment_service import get_user_payments, get_payment

router = APIRouter(prefix="/payments", tags=["payments"])


# GET ALL PAYMENTS FOR A USER
@router.get("/user/{user_id}", response_model=List[PaymentOut])
async def list_user_payments(
    user_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    return await get_user_payments(db, user_id)


# GET PAYMENT BY ID
@router.get("/{payment_id}", response_model=PaymentOut)
async def get_payment_details(
    payment_id: int,
    db: AsyncSession = Depends(get_db)
):
    try:
        return await get_payment(db, payment_id)

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))