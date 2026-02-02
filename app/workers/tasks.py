from __future__ import annotations

import asyncio
from datetime import timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import RoutePlan, Company, Vehicle, Crew, ServicePlan, Location, RouteDay, RouteStop, Depot
from app.services.costs import CostModel
from app.services.optimizer_mapbox import Stop, solve_profit_vrp_with_mapbox


async def run_route_optimization(plan_id: str, session: AsyncSession) -> dict:
    plan = (await session.execute(select(RoutePlan).where(RoutePlan.id == plan_id))).scalar_one()
    company = (await session.execute(select(Company).where(Company.id == plan.company_id))).scalar_one()
    depot = (await session.execute(select(Depot).where(Depot.id == plan.depot_id))).scalar_one()
    vehicle = (await session.execute(select(Vehicle).where(Vehicle.company_id == company.id).limit(1))).scalar_one()
    crew = (await session.execute(select(Crew).where(Crew.company_id == company.id).limit(1))).scalar_one()

    rows = (await session.execute(
        select(ServicePlan, Location)
        .join(Location, ServicePlan.location_id == Location.id)
        .where(ServicePlan.is_active == True)  # noqa: E712
    )).all()

    stops = [
        Stop(
            location_id=str(loc.id),
            lat=float(loc.lat),
            lng=float(loc.lng),
            revenue=sp.revenue_per_visit,
            service_minutes=int(loc.avg_service_minutes),
        )
        for sp, loc in rows
    ]

    gas_price = plan.gas_price_per_gallon or company.default_gas_price
    labor_cost = crew.labor_cost_per_hour or company.default_labor_per_hour

    cost_model = CostModel(
        gas_price_per_gallon=gas_price,
        mpg=vehicle.mpg,
        maintenance_cost_per_mile=vehicle.maintenance_cost_per_mile,
        depreciation_cost_per_mile=getattr(vehicle, "depreciation_cost_per_mile", 0) or 0,
        labor_cost_per_hour=labor_cost,
        avg_speed_mph=25,  # unused now; Mapbox provides durations
    )

    plan.status = "running"
    await session.commit()

    # Build routes (Mapbox is async; OR-Tools is inside but still heavy)
    # We keep the event loop safe by running the whole solve call in a thread:
    routes = await asyncio.to_thread(
        lambda: asyncio.run(
            solve_profit_vrp_with_mapbox(
                (float(depot.lat), float(depot.lng)),
                stops,
                cost_model,
                int(plan.days),
                profile="driving",
                max_coords_per_request=25,  # see docs for profile caps :contentReference[oaicite:10]{index=10}
            )
        )
    )

    # Persist results (same as before)
    # (Implement your clean delete+insert approach here)

    plan.status = "complete"
    await session.commit()

    return {"plan_id": str(plan.id), "status": plan.status, "routes_built": len(routes)}
