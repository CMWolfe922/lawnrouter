from __future__ import annotations

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..db import get_db
from ..auth import get_current_user
from ..models import Vehicle
from ..schemas import VehicleCreate, VehicleRead, VehicleUpdate

router = APIRouter(prefix="/vehicles", tags=["Vehicles"])


@router.post("", response_model=VehicleRead)
async def create_vehicle(
    data: VehicleCreate,
    session: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Create a new vehicle for the company."""
    company_id = user.get("custom:company_id") or user.get("company_id")
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id not found in token")

    vehicle = Vehicle(
        company_id=company_id,
        name=data.name,
        mpg=data.mpg,
        maintenance_cost_per_mile=data.maintenance_cost_per_mile,
    )
    session.add(vehicle)
    await session.commit()
    await session.refresh(vehicle)
    return vehicle


@router.get("", response_model=list[VehicleRead])
async def list_vehicles(
    session: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """List all vehicles for the company."""
    company_id = user.get("custom:company_id") or user.get("company_id")
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id not found in token")

    result = await session.execute(
        select(Vehicle).where(Vehicle.company_id == company_id)
    )
    return result.scalars().all()


@router.get("/{vehicle_id}", response_model=VehicleRead)
async def get_vehicle(
    vehicle_id: UUID,
    session: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Get a specific vehicle."""
    company_id = user.get("custom:company_id") or user.get("company_id")
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id not found in token")

    result = await session.execute(
        select(Vehicle).where(
            Vehicle.id == vehicle_id,
            Vehicle.company_id == company_id,
        )
    )
    vehicle = result.scalar_one_or_none()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return vehicle


@router.patch("/{vehicle_id}", response_model=VehicleRead)
async def update_vehicle(
    vehicle_id: UUID,
    data: VehicleUpdate,
    session: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Update a vehicle."""
    company_id = user.get("custom:company_id") or user.get("company_id")
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id not found in token")

    result = await session.execute(
        select(Vehicle).where(
            Vehicle.id == vehicle_id,
            Vehicle.company_id == company_id,
        )
    )
    vehicle = result.scalar_one_or_none()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(vehicle, field, value)

    await session.commit()
    await session.refresh(vehicle)
    return vehicle


@router.delete("/{vehicle_id}")
async def delete_vehicle(
    vehicle_id: UUID,
    session: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Delete a vehicle."""
    company_id = user.get("custom:company_id") or user.get("company_id")
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id not found in token")

    result = await session.execute(
        select(Vehicle).where(
            Vehicle.id == vehicle_id,
            Vehicle.company_id == company_id,
        )
    )
    vehicle = result.scalar_one_or_none()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    await session.delete(vehicle)
    await session.commit()
    return {"detail": "Vehicle deleted"}
