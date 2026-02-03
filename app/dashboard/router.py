from __future__ import annotations

import uuid
from decimal import Decimal
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..db import get_db
from ..models import RoutePlan, RouteDay, Route, RouteStop, Location
import datetime
from ..config import STATIC_URL, MAPBOX_PUBLIC_TOKEN, MAP_STYLE


router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

TEMPLATE_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))


def _template_context(request: Request, **kwargs) -> dict:
    """Build common template context with config values."""
    return {
        "request": request,
        "STATIC_URL": STATIC_URL,
        "MAPBOX_PUBLIC_TOKEN": MAPBOX_PUBLIC_TOKEN,
        "MAP_STYLE": MAP_STYLE,
        **kwargs,
    }


@router.get("", response_class=HTMLResponse)
async def dashboard_page(
    request: Request,
    company_id: uuid.UUID = Query(...),
    session: AsyncSession = Depends(get_db),
):
    """Render full dashboard page."""
    # Find latest RoutePlan for company
    stmt = (
        select(RoutePlan)
        .where(RoutePlan.company_id == company_id)
        .order_by(desc(RoutePlan.id))
        .limit(1)
    )
    result = await session.execute(stmt)
    plan = result.scalar_one_or_none()

    plan_id = str(plan.id) if plan else None

    ctx = _template_context(
        request,
        company_id=str(company_id),
        plan_id=plan_id,
    )
    return templates.TemplateResponse("dashboard.html", ctx)


@router.get("/partials/kpis", response_class=HTMLResponse)
async def partials_kpis(
    request: Request,
    company_id: uuid.UUID = Query(...),
    plan_id: Optional[uuid.UUID] = Query(None),
    session: AsyncSession = Depends(get_db),
):
    """Return KPI summary partial."""
    totals = {
        "total_revenue": Decimal("0"),
        "total_cost": Decimal("0"),
        "total_profit": Decimal("0"),
        "total_miles": Decimal("0"),
        "total_drive_minutes": 0,
        "total_service_minutes": 0,
    }

    if plan_id:
        stmt = select(
            func.coalesce(func.sum(RouteDay.total_revenue), 0).label("total_revenue"),
            func.coalesce(func.sum(RouteDay.total_cost), 0).label("total_cost"),
            func.coalesce(func.sum(RouteDay.total_profit), 0).label("total_profit"),
        ).where(RouteDay.plan_id == plan_id)

        result = await session.execute(stmt)
        row = result.one_or_none()
        if row:
            totals["total_revenue"] = Decimal(str(row.total_revenue or 0))
            totals["total_cost"] = Decimal(str(row.total_cost or 0))
            totals["total_profit"] = Decimal(str(row.total_profit or 0))

        # Sum miles and minutes from Routes
        route_stmt = select(
            func.coalesce(func.sum(Route.total_miles), 0).label("total_miles"),
            func.coalesce(func.sum(Route.total_drive_minutes), 0).label("total_drive_minutes"),
            func.coalesce(func.sum(Route.total_service_minutes), 0).label("total_service_minutes"),
        ).where(Route.plan_id == plan_id)

        route_result = await session.execute(route_stmt)
        route_row = route_result.one_or_none()
        if route_row:
            totals["total_miles"] = Decimal(str(route_row.total_miles or 0))
            totals["total_drive_minutes"] = int(route_row.total_drive_minutes or 0)
            totals["total_service_minutes"] = int(route_row.total_service_minutes or 0)

    ctx = _template_context(request, totals=totals, plan_id=str(plan_id) if plan_id else None)
    return templates.TemplateResponse("partials/kpis.html", ctx)


@router.get("/partials/route-days", response_class=HTMLResponse)
async def partials_route_days(
    request: Request,
    company_id: uuid.UUID = Query(...),
    plan_id: Optional[uuid.UUID] = Query(None),
    session: AsyncSession = Depends(get_db),
):
    """Return route days list partial."""
    route_days = []

    if plan_id:
        stmt = (
            select(RouteDay)
            .where(RouteDay.plan_id == plan_id)
            .order_by(RouteDay.date.asc())
        )
        result = await session.execute(stmt)
        route_days = list(result.scalars().all())

    ctx = _template_context(request, route_days=route_days, company_id=str(company_id))
    return templates.TemplateResponse("partials/route_days.html", ctx)


@router.get("/partials/routes-for-day", response_class=HTMLResponse)
async def partials_routes_for_day(
    request: Request,
    route_day_id: uuid.UUID = Query(...),
    session: AsyncSession = Depends(get_db),
):
    """Return routes list for a specific day partial."""
    # First get the RouteDay to know the plan and date
    day_stmt = select(RouteDay).where(RouteDay.id == route_day_id)
    day_result = await session.execute(day_stmt)
    route_day = day_result.scalar_one_or_none()

    routes = []
    if route_day:
        # Load routes from the same plan
        stmt = (
            select(Route)
            .where(Route.plan_id == route_day.plan_id)
            .order_by(Route.day.asc(), Route.created_at.asc())
        )
        result = await session.execute(stmt)
        routes = list(result.scalars().all())

    ctx = _template_context(request, routes=routes, route_day_id=str(route_day_id))
    return templates.TemplateResponse("partials/routes_for_day.html", ctx)


@router.get("/partials/route-detail", response_class=HTMLResponse)
async def partials_route_detail(
    request: Request,
    route_id: uuid.UUID = Query(...),
    session: AsyncSession = Depends(get_db),
):
    """Return route stops detail partial."""
    # First try to load stops by route_id directly
    stmt = (
        select(RouteStop)
        .options(selectinload(RouteStop.location))
        .where(RouteStop.route_id == route_id)
        .order_by(RouteStop.order.asc())
    )
    result = await session.execute(stmt)
    stops = list(result.scalars().all())

    # Fallback: load via RouteDay if no direct route_id match
    if not stops:
        route_stmt = select(Route).where(Route.id == route_id)
        route_result = await session.execute(route_stmt)
        route = route_result.scalar_one_or_none()

        if route and route.plan_id:
            plan_stmt = select(RoutePlan).where(RoutePlan.id == route.plan_id)
            plan_result = await session.execute(plan_stmt)
            plan = plan_result.scalar_one_or_none()

            if plan:
                target_date = plan.start_date + datetime.timedelta(days=route.day)

                day_stmt = select(RouteDay).where(
                    RouteDay.plan_id == route.plan_id,
                    RouteDay.date == target_date
                )
                day_result = await session.execute(day_stmt)
                route_day = day_result.scalar_one_or_none()

                if route_day:
                    stmt = (
                        select(RouteStop)
                        .options(selectinload(RouteStop.location))
                        .where(RouteStop.route_day_id == route_day.id)
                        .order_by(RouteStop.order.asc())
                    )
                    result = await session.execute(stmt)
                    stops = list(result.scalars().all())

    ctx = _template_context(request, stops=stops, route_id=str(route_id))
    return templates.TemplateResponse("partials/route_detail.html", ctx)


@router.get("/partials/customer-card", response_class=HTMLResponse)
async def partials_customer_card(
    request: Request,
    location_id: uuid.UUID = Query(...),
    session: AsyncSession = Depends(get_db),
):
    """Return customer card partial."""
    stmt = (
        select(Location)
        .options(selectinload(Location.customer))
        .where(Location.id == location_id)
    )
    result = await session.execute(stmt)
    location = result.scalar_one_or_none()

    ctx = _template_context(request, location=location)
    return templates.TemplateResponse("partials/customer_card.html", ctx)
