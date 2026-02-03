# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LawnRouter is a serverless FastAPI application for optimizing lawn service routing and crew scheduling. It uses Prize-Collecting Vehicle Routing Problem (VRP) optimization to maximize profit by selecting which service stops to visit and determining optimal routes.

## Tech Stack

- **Backend**: FastAPI with async/await, Mangum for Lambda
- **Database**: Neon Serverless PostgreSQL via SQLAlchemy 2.0 async ORM (asyncpg driver)
- **Optimization**: Google OR-Tools VRP solver + Mapbox Matrix API for road-network distances
- **Infrastructure**: AWS SAM (Lambda, API Gateway, S3, Cognito, SQS)
- **Auth**: AWS Cognito with RS256 JWT tokens

## Commands

```bash
# Install dependencies
uv sync

# Run locally
uvicorn app.main:app --reload

# Deploy to AWS
sam build && sam deploy

# Database migrations (Alembic)
alembic upgrade head
alembic revision --autogenerate -m "description"
```

## Architecture

### Request Flow
```
HTTP Request → FastAPI Router → Service Layer → Worker Task → OR-Tools Solver
                    ↓                            ↓
              Cognito JWT Auth           Mapbox Matrix API
                    ↓
              AsyncSession DB
```

### Key Layers

**API Layer** (`app/routers/`): FastAPI endpoints with Cognito JWT auth dependency
- `optimization.py`: Triggers background VRP optimization jobs

**Worker Layer** (`app/workers/tasks.py`): Background job orchestration
- Fetches entities, builds Stop objects, invokes OR-Tools solver via `asyncio.to_thread()` to protect the event loop from CPU-heavy computation

**Optimization Engine** (`app/services/optimizer_mapbox.py`): Prize-Collecting VRP solver
- Fetches Mapbox distance/duration matrix (chunked requests, max 25 coords each)
- Configures OR-Tools with travel cost + labor cost objectives
- Uses disjunctions with revenue as penalty to allow profitable stop skipping
- Returns routes sorted by profit

**Data Layer** (`app/models.py`): SQLAlchemy 2.0 async models
- Multi-tenant via `company_id` on all entities
- Core: Company, Customer, Location, ServicePlan
- Operations: Vehicle, Employee, Crew, CrewEmployee
- Routing: Route, RoutePlan, RouteDay, RouteStop

### Cost Model

VRP profit optimization objective:
```
total_profit = total_revenue - (travel_cost + labor_cost)
travel_cost = distance_miles × (gas_cost + maintenance_cost + depreciation_cost)
labor_cost = (drive_minutes + service_minutes) × (labor_per_hour / 60)
```

### Multi-Tenant Pattern

All queries must be filtered by `company_id`. The pattern is consistent across:
- Models: Company as root entity
- Routers: Filter queries by company_id from auth context
- Services: Company-specific cost parameters passed to solver
- S3: Upload keys prefixed with `company/{company_id}/`

### Event Loop Protection Pattern

CPU-bound OR-Tools solver must run in a thread pool:
```python
routes = await asyncio.to_thread(
    lambda: asyncio.run(solve_profit_vrp_with_mapbox(...))
)
```

## Entry Points

- `app/main.py`: FastAPI app with Mangum Lambda handler (`handler`)
- `template.yaml`: AWS SAM infrastructure (expects `app.worker_handler.handler` for SQS)
