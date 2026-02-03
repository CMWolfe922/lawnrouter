from __future__ import annotations

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..db import get_db
from ..auth import get_current_user
from ..models import ServicePlan, Location, Customer
from ..schemas import ServicePlanCreate, ServicePlanRead, ServicePlanUpdate

router = APIRouter(prefix="/service-plans", tags=["Service Plans"])


@router.post("", response_model=ServicePlanRead)
async def create_service_plan(
    data: ServicePlanCreate,
    session: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Create a service plan for a location."""
    company_id = user.get("custom:company_id") or user.get("company_id")
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id not found in token")

    # Verify location belongs to a customer of this company
    result = await session.execute(
        select(Location)
        .join(Customer, Location.customer_id == Customer.id)
        .where(
            Location.id == data.location_id,
            Customer.company_id == company_id,
        )
    )
    location = result.scalar_one_or_none()
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")

    service_plan = ServicePlan(
        company_id=company_id,
        location_id=data.location_id,
        frequency=data.frequency,
        revenue_per_visit=data.revenue_per_visit,
    )
    session.add(service_plan)
    await session.commit()
    await session.refresh(service_plan)
    return service_plan


@router.get("", response_model=list[ServicePlanRead])
async def list_service_plans(
    session: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """List all service plans for the company."""
    company_id = user.get("custom:company_id") or user.get("company_id")
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id not found in token")

    result = await session.execute(
        select(ServicePlan).where(ServicePlan.company_id == company_id)
    )
    return result.scalars().all()


@router.get("/location/{location_id}", response_model=list[ServicePlanRead])
async def list_service_plans_for_location(
    location_id: UUID,
    session: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """List all service plans for a specific location."""
    company_id = user.get("custom:company_id") or user.get("company_id")
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id not found in token")

    # Verify location belongs to company
    result = await session.execute(
        select(Location)
        .join(Customer, Location.customer_id == Customer.id)
        .where(
            Location.id == location_id,
            Customer.company_id == company_id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Location not found")

    result = await session.execute(
        select(ServicePlan).where(
            ServicePlan.location_id == location_id,
            ServicePlan.company_id == company_id,
        )
    )
    return result.scalars().all()


@router.get("/{plan_id}", response_model=ServicePlanRead)
async def get_service_plan(
    plan_id: UUID,
    session: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Get a specific service plan."""
    company_id = user.get("custom:company_id") or user.get("company_id")
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id not found in token")

    result = await session.execute(
        select(ServicePlan).where(
            ServicePlan.id == plan_id,
            ServicePlan.company_id == company_id,
        )
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Service plan not found")
    return plan


@router.patch("/{plan_id}", response_model=ServicePlanRead)
async def update_service_plan(
    plan_id: UUID,
    data: ServicePlanUpdate,
    session: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Update a service plan."""
    company_id = user.get("custom:company_id") or user.get("company_id")
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id not found in token")

    result = await session.execute(
        select(ServicePlan).where(
            ServicePlan.id == plan_id,
            ServicePlan.company_id == company_id,
        )
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Service plan not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(plan, field, value)

    await session.commit()
    await session.refresh(plan)
    return plan


@router.delete("/{plan_id}")
async def delete_service_plan(
    plan_id: UUID,
    session: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Delete a service plan (sets inactive)."""
    company_id = user.get("custom:company_id") or user.get("company_id")
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id not found in token")

    result = await session.execute(
        select(ServicePlan).where(
            ServicePlan.id == plan_id,
            ServicePlan.company_id == company_id,
        )
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Service plan not found")

    plan.is_active = False
    await session.commit()
    return {"detail": "Service plan deactivated"}
