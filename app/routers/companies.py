from __future__ import annotations

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..db import get_db
from ..auth import get_current_user
from ..models import Company
from ..schemas import CompanyRead, CompanyUpdate, CompanySettingsRead, CompanySettingsUpdate

router = APIRouter(prefix="/companies", tags=["Companies"])


@router.get("/me", response_model=CompanyRead)
async def get_my_company(
    session: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Get the current user's company."""
    company_id = user.get("custom:company_id") or user.get("company_id")
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id not found in token")

    result = await session.execute(
        select(Company).where(Company.id == company_id)
    )
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company


@router.patch("/me", response_model=CompanyRead)
async def update_my_company(
    data: CompanyUpdate,
    session: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Update the current user's company."""
    company_id = user.get("custom:company_id") or user.get("company_id")
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id not found in token")

    result = await session.execute(
        select(Company).where(Company.id == company_id)
    )
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(company, field, value)

    await session.commit()
    await session.refresh(company)
    return company


@router.get("/me/settings", response_model=CompanySettingsRead)
async def get_company_settings(
    session: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Get company default settings for routing calculations."""
    company_id = user.get("custom:company_id") or user.get("company_id")
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id not found in token")

    result = await session.execute(
        select(Company).where(Company.id == company_id)
    )
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    return CompanySettingsRead(
        default_gas_price=float(company.default_gas_price),
        default_labor_per_hour=float(company.default_labor_per_hour),
        default_maintenance_cost_per_mile=0.0,  # Not in model, default to 0
    )


@router.patch("/me/settings", response_model=CompanySettingsRead)
async def update_company_settings(
    data: CompanySettingsUpdate,
    session: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Update company default settings."""
    company_id = user.get("custom:company_id") or user.get("company_id")
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id not found in token")

    result = await session.execute(
        select(Company).where(Company.id == company_id)
    )
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    if data.default_gas_price is not None:
        company.default_gas_price = data.default_gas_price
    if data.default_labor_per_hour is not None:
        company.default_labor_per_hour = data.default_labor_per_hour

    await session.commit()
    await session.refresh(company)

    return CompanySettingsRead(
        default_gas_price=float(company.default_gas_price),
        default_labor_per_hour=float(company.default_labor_per_hour),
        default_maintenance_cost_per_mile=0.0,
    )
