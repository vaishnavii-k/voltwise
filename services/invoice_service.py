from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import Invoice

async def get_user_invoices(db: AsyncSession, user_id: str):
    stmt = select(Invoice).where(Invoice.user_id == user_id).order_by(Invoice.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()

async def pay_invoice(db: AsyncSession, invoice_id: int) -> Invoice:
    stmt = select(Invoice).where(Invoice.id == invoice_id).with_for_update()
    result = await db.execute(stmt)
    invoice = result.scalars().first()

    if not invoice:
        raise ValueError("Invoice not found")
    if invoice.status == "paid":
        raise ValueError("Invoice is already paid")

    invoice.status = "paid"
    await db.commit()
    await db.refresh(invoice)
    return invoice