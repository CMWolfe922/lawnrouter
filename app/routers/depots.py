from __future__ import annotations

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..db import get_db
from ..auth import get_current_user
from ..models import Depot
from ..schemas import DepotCreate, DepotRead, DepotUpdate
from ..services.geo import geocode_address

router = APIRouter(prefix="/depots", tags=["Depots"])


@router.post("", response_model=DepotRead)
async def create_depot(
    data: DepotCreate,
    session: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Create a new depot (starting location for routes)."""
    company_id = user.get("custom:company_id") or user.get("company_id")
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id not found in token")

    # Geocode the address
    try:
        lat, lng = await geocode_address(data.address)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    depot = Depot(
        company_id=company_id,
        name=data.name,
        address=data.address,
        lat=lat,
        lng=lng,
    )
    session.add(depot)
    await session.commit()
    await session.refresh(depot)
    return depot


@router.get("", response_model=list[DepotRead])
async def list_depots(
    session: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """List all depots for the company."""
    company_id = user.get("custom:company_id") or user.get("company_id")
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id not found in token")

    result = await session.execute(
        select(Depot).where(Depot.company_id == company_id)
    )
    return result.scalars().all()


@router.get("/{depot_id}", response_model=DepotRead)
async def get_depot(
    depot_id: UUID,
    session: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Get a specific depot."""
    company_id = user.get("custom:company_id") or user.get("company_id")
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id not found in token")

    result = await session.execute(
        select(Depot).where(
            Depot.id == depot_id,
            Depot.company_id == company_id,
        )
    )
    depot = result.scalar_one_or_none()
    if not depot:
        raise HTTPException(status_code=404, detail="Depot not found")
    return depot


@router.patch("/{depot_id}", response_model=DepotRead)
async def update_depot(
    depot_id: UUID,
    data: DepotUpdate,
    session: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Update a depot. If address changes, re-geocode."""
    company_id = user.get("custom:company_id") or user.get("company_id")
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id not found in token")

    result = await session.execute(
        select(Depot).where(
            Depot.id == depot_id,
            Depot.company_id == company_id,
        )
    )
    depot = result.scalar_one_or_none()
    if not depot:
        raise HTTPException(status_code=404, detail="Depot not found")

    update_data = data.model_dump(exclude_unset=True)

    # If address is being updated, re-geocode
    if "address" in update_data:
        try:
            lat, lng = await geocode_address(update_data["address"])
            depot.lat = lat
            depot.lng = lng
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    for field, value in update_data.items():
        setattr(depot, field, value)

    await session.commit()
    await session.refresh(depot)
    return depot


@router.delete("/{depot_id}")
async def delete_depot(
    depot_id: UUID,
    session: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Delete a depot (sets inactive)."""
    company_id = user.get("custom:company_id") or user.get("company_id")
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id not found in token")

    result = await session.execute(
        select(Depot).where(
            Depot.id == depot_id,
            Depot.company_id == company_id,
        )
    )
    depot = result.scalar_one_or_none()
    if not depot:
        raise HTTPException(status_code=404, detail="Depot not found")

    depot.is_active = False
    await session.commit()
    return {"detail": "Depot deactivated"}
