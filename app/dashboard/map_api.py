from __future__ import annotations

import uuid
from decimal import Decimal, InvalidOperation
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..db import get_db
from ..models import Route, RouteStop, Location, Depot, Company


router = APIRouter(prefix="/dashboard/api", tags=["Dashboard API"])


class CostModel:
    """Simple cost model for route pricing calculations."""

    def __init__(
        self,
        gas_price_per_gallon: float = 3.0,
        mpg: float = 15.0,
        maintenance_cost_per_mile: float = 0.20,
        labor_cost_per_hour: float = 20.0,
    ):
        self.gas_price_per_gallon = Decimal(str(gas_price_per_gallon))
        self.mpg = Decimal(str(mpg)) if mpg > 0 else Decimal("15")
        self.maintenance_cost_per_mile = Decimal(str(maintenance_cost_per_mile))
        self.labor_cost_per_hour = Decimal(str(labor_cost_per_hour))

    def cost_per_mile(self) -> Decimal:
        """Calculate cost per mile (fuel + maintenance)."""
        fuel_cost = self.gas_price_per_gallon / self.mpg
        return fuel_cost + self.maintenance_cost_per_mile

    def labor_cost_per_minute(self) -> Decimal:
        """Calculate labor cost per minute."""
        return self.labor_cost_per_hour / Decimal("60")


def _build_cost_model(route: Route, company: Optional[Company] = None) -> CostModel:
    """Build a CostModel from route snapshots with company defaults as fallback."""
    gas_price = route.gas_price_per_gallon or (company.default_gas_price if company else None) or 3.0
    mpg = route.mpg or 15.0
    maintenance = route.maintenance_cost_per_mile or 0.20
    labor = route.labor_cost_per_hour or (company.default_labor_per_hour if company else None) or 20.0

    return CostModel(
        gas_price_per_gallon=float(gas_price),
        mpg=float(mpg),
        maintenance_cost_per_mile=float(maintenance),
        labor_cost_per_hour=float(labor),
    )


@router.get("/route-geojson")
async def get_route_geojson(
    route_id: uuid.UUID = Query(...),
    session: AsyncSession = Depends(get_db),
):
    """
    Return GeoJSON FeatureCollection with:
    - depot point feature (kind: "depot")
    - stop point features (kind: "stop") with profitability
    - route line feature (kind: "route_line")
    """
    # Load route with depot
    route_stmt = (
        select(Route)
        .options(selectinload(Route.depot))
        .where(Route.id == route_id)
    )
    result = await session.execute(route_stmt)
    route = result.scalar_one_or_none()

    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    # Try loading stops by route_id first, then fall back to route_day
    stops_stmt = (
        select(RouteStop)
        .options(selectinload(RouteStop.location))
        .where(RouteStop.route_id == route_id)
        .order_by(RouteStop.order.asc())
    )
    stops_result = await session.execute(stops_stmt)
    stops = list(stops_result.scalars().all())

    # If no stops found by route_id, try to find via RouteDay matching
    if not stops and route.plan_id:
        # Find RouteDay for this route's plan and day
        from ..models import RouteDay, RoutePlan

        plan_stmt = select(RoutePlan).where(RoutePlan.id == route.plan_id)
        plan_result = await session.execute(plan_stmt)
        plan = plan_result.scalar_one_or_none()

        if plan:
            import datetime
            target_date = plan.start_date + datetime.timedelta(days=route.day)

            day_stmt = (
                select(RouteDay)
                .where(RouteDay.plan_id == route.plan_id, RouteDay.date == target_date)
            )
            day_result = await session.execute(day_stmt)
            route_day = day_result.scalar_one_or_none()

            if route_day:
                stops_stmt = (
                    select(RouteStop)
                    .options(selectinload(RouteStop.location))
                    .where(RouteStop.route_day_id == route_day.id)
                    .order_by(RouteStop.order.asc())
                )
                stops_result = await session.execute(stops_stmt)
                stops = list(stops_result.scalars().all())

    # Build cost model for profitability calculation
    cost_model = _build_cost_model(route)

    features = []
    coordinates = []

    # Depot feature
    depot = route.depot
    if depot and depot.lat and depot.lng:
        depot_coords = [float(depot.lng), float(depot.lat)]
        coordinates.append(depot_coords)

        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": depot_coords,
            },
            "properties": {
                "kind": "depot",
                "name": depot.name,
                "address": depot.address,
            },
        })

    # Stop features
    for stop in stops:
        loc = stop.location
        if not loc or not loc.lat or not loc.lng:
            continue

        stop_coords = [float(loc.lng), float(loc.lat)]
        coordinates.append(stop_coords)

        # Calculate profit for this stop
        revenue = Decimal(str(stop.revenue or 0))
        segment_miles = Decimal(str(stop.segment_miles or 0))
        service_minutes = stop.total_route_stop_minutes or (loc.avg_service_minutes if loc else 0) or 0

        travel_cost = segment_miles * cost_model.cost_per_mile()
        labor_cost = Decimal(str(service_minutes)) * cost_model.labor_cost_per_minute()
        total_cost = travel_cost + labor_cost
        profit = revenue - total_cost

        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": stop_coords,
            },
            "properties": {
                "kind": "stop",
                "order": stop.order,
                "location_id": str(stop.location_id),
                "revenue": str(revenue.quantize(Decimal("0.01"))),
                "service_minutes": service_minutes,
                "profit": float(profit.quantize(Decimal("0.01"))),
            },
        })

    # Add return to depot
    if depot and depot.lat and depot.lng:
        coordinates.append([float(depot.lng), float(depot.lat)])

    # Route line feature
    if len(coordinates) >= 2:
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": coordinates,
            },
            "properties": {
                "kind": "route_line",
            },
        })

    return {
        "type": "FeatureCollection",
        "features": features,
    }


@router.get("/stop-detail")
async def get_stop_detail(
    location_id: uuid.UUID = Query(...),
    session: AsyncSession = Depends(get_db),
):
    """Return stop/location details with customer info."""
    stmt = (
        select(Location)
        .options(selectinload(Location.customer))
        .where(Location.id == location_id)
    )
    result = await session.execute(stmt)
    location = result.scalar_one_or_none()

    if not location:
        raise HTTPException(status_code=404, detail="Location not found")

    customer = location.customer

    return {
        "location_id": str(location.id),
        "address": location.address,
        "lat": float(location.lat) if location.lat else None,
        "lng": float(location.lng) if location.lng else None,
        "customer_name": customer.name if customer else None,
        "email": customer.email if customer else None,
        "phone": customer.phone if customer else None,
    }


@router.get("/stop-pricing")
async def get_stop_pricing(
    route_id: uuid.UUID = Query(...),
    location_id: uuid.UUID = Query(...),
    target_margin: float = Query(0.30, ge=0, lt=1),
    session: AsyncSession = Depends(get_db),
):
    """
    Return pricing analysis for a specific stop including suggested price.
    """
    # Load route
    route_stmt = select(Route).where(Route.id == route_id)
    route_result = await session.execute(route_stmt)
    route = route_result.scalar_one_or_none()

    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    # Try loading stop by route_id first
    stop_stmt = (
        select(RouteStop)
        .options(selectinload(RouteStop.location))
        .where(RouteStop.route_id == route_id, RouteStop.location_id == location_id)
    )
    stop_result = await session.execute(stop_stmt)
    stop = stop_result.scalar_one_or_none()

    # Fallback: find stop via RouteDay
    if not stop and route.plan_id:
        from ..models import RouteDay, RoutePlan
        import datetime

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
                stop_stmt = (
                    select(RouteStop)
                    .options(selectinload(RouteStop.location))
                    .where(RouteStop.route_day_id == route_day.id, RouteStop.location_id == location_id)
                )
                stop_result = await session.execute(stop_stmt)
                stop = stop_result.scalar_one_or_none()

    if not stop:
        raise HTTPException(status_code=404, detail="Stop not found for this route")

    # Build cost model
    cost_model = _build_cost_model(route)

    # Calculate costs
    segment_miles = Decimal(str(stop.segment_miles or 0))
    loc = stop.location
    service_minutes = stop.total_route_stop_minutes or (loc.avg_service_minutes if loc else 0) or 0

    travel_cost = segment_miles * cost_model.cost_per_mile()
    labor_cost = Decimal(str(service_minutes)) * cost_model.labor_cost_per_minute()
    total_cost = travel_cost + labor_cost

    revenue = Decimal(str(stop.revenue or 0))
    profit = revenue - total_cost

    # Calculate margin
    if revenue > 0:
        margin = (profit / revenue) * 100
    else:
        margin = Decimal("0")

    # Calculate suggested price for target margin
    # suggested_price = total_cost / (1 - target_margin)
    try:
        if target_margin < 1:
            suggested_price = total_cost / Decimal(str(1 - target_margin))
        else:
            suggested_price = total_cost * 2  # Fallback if margin >= 1
    except (InvalidOperation, ZeroDivisionError):
        suggested_price = total_cost * 2

    return {
        "cost": str(total_cost.quantize(Decimal("0.01"))),
        "revenue": str(revenue.quantize(Decimal("0.01"))),
        "profit": str(profit.quantize(Decimal("0.01"))),
        "margin": float(margin.quantize(Decimal("0.1"))),
        "suggested_price": str(suggested_price.quantize(Decimal("0.01"))),
    }
