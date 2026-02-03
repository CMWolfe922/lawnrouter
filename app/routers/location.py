from __future__ import annotations

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..db import get_db
from ..auth import get_current_user
from ..models import Location, Customer
from ..schemas import LocationCreate, LocationRead
from ..services.geo import geocode_address

router = APIRouter(prefix="/properties", tags=["Properties"])


@router.post("", response_model=LocationRead)
async def create_property(
    data: LocationCreate,
    session: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    company_id = user.get("custom:company_id") or user.get("company_id")
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id not found in token")

    # Verify customer belongs to this company
    result = await session.execute(
        select(Customer).where(
            Customer.id == data.customer_id,
            Customer.company_id == company_id,
        )
    )
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Geocode the address
    try:
        lat, lng = await geocode_address(data.address)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    location = Location(
        customer_id=data.customer_id,
        address=data.address,
        lat=lat,
        lng=lng,
        avg_service_minutes=data.avg_service_minutes,
    )
    session.add(location)
    await session.commit()
    await session.refresh(location)
    return location


@router.get("", response_model=list[LocationRead])
async def list_properties(
    session: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    company_id = user.get("custom:company_id") or user.get("company_id")
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id not found in token")

    # Get all locations for customers belonging to this company
    result = await session.execute(
        select(Location)
        .join(Customer, Location.customer_id == Customer.id)
        .where(Customer.company_id == company_id)
    )
    return result.scalars().all()


@router.get("/{location_id}", response_model=LocationRead)
async def get_property(
    location_id: UUID,
    session: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    company_id = user.get("custom:company_id") or user.get("company_id")
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id not found in token")

    # Get location if it belongs to a customer of this company
    result = await session.execute(
        select(Location)
        .join(Customer, Location.customer_id == Customer.id)
        .where(
            Location.id == location_id,
            Customer.company_id == company_id,
        )
    )
    location = result.scalar_one_or_none()
    if not location:
        raise HTTPException(status_code=404, detail="Property not found")
    return location
