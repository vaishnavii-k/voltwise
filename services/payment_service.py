from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from models import Payment, ChargingSession, Reservation


# GET PAYMENTS FOR A USER
async def get_user_payments(db: AsyncSession, user_id: UUID):

    stmt = (
        select(Payment)
        .join(
            ChargingSession,
            Payment.session_id == ChargingSession.id
        )
        .join(
            Reservation,
            ChargingSession.reservation_id == Reservation.id
        )
        .where(Reservation.user_id == user_id)
        .order_by(Payment.created_at.desc())
    )

    result = await db.execute(stmt)

    return result.scalars().all()


# GET A SINGLE PAYMENT
async def get_payment(db: AsyncSession, payment_id: int):

    stmt = select(Payment).where(Payment.id == payment_id)

    result = await db.execute(stmt)

    payment = result.scalars().first()

    if not payment:
        raise ValueError("Payment not found")

    return payment