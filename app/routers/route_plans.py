from __future__ import annotations

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..db import get_db
from ..auth import get_current_user
from ..models import RoutePlan, Route, RouteStop
from ..schemas import RoutePlanCreate, RoutePlanRead, RoutePlanUpdate, RouteRead, RouteStopRead

router = APIRouter(prefix="/route-plans", tags=["Route Plans"])


@router.post("", response_model=RoutePlanRead)
async def create_route_plan(
    data: RoutePlanCreate,
    session: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Create a new route plan."""
    company_id = user.get("custom:company_id") or user.get("company_id")
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id not found in token")

    route_plan = RoutePlan(
        company_id=company_id,
        start_date=data.start_date,
        days=data.days,
        status="pending",
    )
    session.add(route_plan)
    await session.commit()
    await session.refresh(route_plan)
    return route_plan


@router.get("", response_model=list[RoutePlanRead])
async def list_route_plans(
    session: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """List all route plans for the company."""
    company_id = user.get("custom:company_id") or user.get("company_id")
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id not found in token")

    result = await session.execute(
        select(RoutePlan).where(RoutePlan.company_id == company_id)
    )
    return result.scalars().all()


@router.get("/{plan_id}", response_model=RoutePlanRead)
async def get_route_plan(
    plan_id: UUID,
    session: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Get a specific route plan."""
    company_id = user.get("custom:company_id") or user.get("company_id")
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id not found in token")

    result = await session.execute(
        select(RoutePlan).where(
            RoutePlan.id == plan_id,
            RoutePlan.company_id == company_id,
        )
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Route plan not found")
    return plan


@router.patch("/{plan_id}", response_model=RoutePlanRead)
async def update_route_plan(
    plan_id: UUID,
    data: RoutePlanUpdate,
    session: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Update a route plan."""
    company_id = user.get("custom:company_id") or user.get("company_id")
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id not found in token")

    result = await session.execute(
        select(RoutePlan).where(
            RoutePlan.id == plan_id,
            RoutePlan.company_id == company_id,
        )
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Route plan not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(plan, field, value)

    await session.commit()
    await session.refresh(plan)
    return plan


@router.delete("/{plan_id}")
async def delete_route_plan(
    plan_id: UUID,
    session: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Delete a route plan."""
    company_id = user.get("custom:company_id") or user.get("company_id")
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id not found in token")

    result = await session.execute(
        select(RoutePlan).where(
            RoutePlan.id == plan_id,
            RoutePlan.company_id == company_id,
        )
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Route plan not found")

    await session.delete(plan)
    await session.commit()
    return {"detail": "Route plan deleted"}


# -----------------
# ROUTES WITHIN A PLAN
# -----------------

@router.get("/{plan_id}/routes", response_model=list[RouteRead])
async def list_routes_for_plan(
    plan_id: UUID,
    session: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """List all routes for a specific route plan."""
    company_id = user.get("custom:company_id") or user.get("company_id")
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id not found in token")

    # Verify plan belongs to company
    result = await session.execute(
        select(RoutePlan).where(
            RoutePlan.id == plan_id,
            RoutePlan.company_id == company_id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Route plan not found")

    result = await session.execute(
        select(Route).where(Route.plan_id == plan_id)
    )
    return result.scalars().all()


@router.get("/{plan_id}/routes/{route_id}", response_model=RouteRead)
async def get_route(
    plan_id: UUID,
    route_id: UUID,
    session: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Get a specific route."""
    company_id = user.get("custom:company_id") or user.get("company_id")
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id not found in token")

    # Verify plan belongs to company
    result = await session.execute(
        select(RoutePlan).where(
            RoutePlan.id == plan_id,
            RoutePlan.company_id == company_id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Route plan not found")

    result = await session.execute(
        select(Route).where(
            Route.id == route_id,
            Route.plan_id == plan_id,
        )
    )
    route = result.scalar_one_or_none()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    return route


@router.get("/{plan_id}/routes/{route_id}/stops", response_model=list[RouteStopRead])
async def list_route_stops(
    plan_id: UUID,
    route_id: UUID,
    session: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """List all stops for a specific route, ordered by sequence."""
    company_id = user.get("custom:company_id") or user.get("company_id")
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id not found in token")

    # Verify plan belongs to company
    result = await session.execute(
        select(RoutePlan).where(
            RoutePlan.id == plan_id,
            RoutePlan.company_id == company_id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Route plan not found")

    # Verify route belongs to plan
    result = await session.execute(
        select(Route).where(
            Route.id == route_id,
            Route.plan_id == plan_id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Route not found")

    result = await session.execute(
        select(RouteStop)
        .where(RouteStop.route_id == route_id)
        .order_by(RouteStop.order)
    )
    return result.scalars().all()
