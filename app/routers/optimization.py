from __future__ import annotations

import asyncio
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..db import get_db
from ..models import RoutePlan
from ..workers.tasks import run_route_optimization

router = APIRouter(prefix="/optimization", tags=["Optimization"])


@router.post("/route-plans/{plan_id}/run")
async def optimize_route_plan(plan_id: str, session: AsyncSession = Depends(get_db)):
    plan = (await session.execute(select(RoutePlan).where(RoutePlan.id == plan_id))).scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="RoutePlan not found")

    if plan.status in ("running",):
        raise HTTPException(status_code=409, detail="RoutePlan is already running")

    # Kick off background work (simple, no Celery yet)
    async def _runner():
        try:
            await run_route_optimization(plan_id, session)
        except Exception:
            # If you want: set plan.status="failed" with error here
            pass

    asyncio.create_task(_runner())
    return {"plan_id": plan_id, "status": "queued"}
