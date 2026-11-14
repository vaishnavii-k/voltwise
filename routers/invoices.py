from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from database import get_db
from schemas import InvoiceOut
from services.invoice_service import get_user_invoices, pay_invoice

router = APIRouter(prefix="/invoices", tags=["invoices"])

@router.get("/user/{user_id}", response_model=List[InvoiceOut])
async def list_user_invoices(user_id: str, db: AsyncSession = Depends(get_db)):
    return await get_user_invoices(db, user_id)

@router.post("/{invoice_id}/pay", response_model=InvoiceOut)
async def pay_user_invoice(invoice_id: int, db: AsyncSession = Depends(get_db)):
    try:
        return await pay_invoice(db, invoice_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))