from __future__ import annotations

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..db import get_db
from ..auth import get_current_user
from ..models import Customer
from ..schemas import CustomerCreate, CustomerRead

router = APIRouter(prefix="/customers", tags=["Customers"])


@router.post("", response_model=CustomerRead)
async def create_customer(
    data: CustomerCreate,
    session: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    company_id = user.get("custom:company_id") or user.get("company_id")
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id not found in token")

    customer = Customer(
        company_id=company_id,
        name=data.name,
        email=data.email,
        phone=data.phone,
    )
    session.add(customer)
    await session.commit()
    await session.refresh(customer)
    return customer


@router.get("", response_model=list[CustomerRead])
async def list_customers(
    session: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    company_id = user.get("custom:company_id") or user.get("company_id")
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id not found in token")

    result = await session.execute(
        select(Customer).where(Customer.company_id == company_id)
    )
    return result.scalars().all()


@router.get("/{customer_id}", response_model=CustomerRead)
async def get_customer(
    customer_id: UUID,
    session: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    company_id = user.get("custom:company_id") or user.get("company_id")
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id not found in token")

    result = await session.execute(
        select(Customer).where(
            Customer.id == customer_id,
            Customer.company_id == company_id,
        )
    )
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer
