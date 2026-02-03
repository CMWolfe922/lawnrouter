from fastapi import FastAPI
from mangum import Mangum

from app.routers import (
    photos,
    optimization,
    customers,
    location,
    companies,
    vehicles,
    crews,
    service_plan,
    route_plans,
    depots,
)
from app.dashboard import router as dashboard_router
from app.dashboard import map_api as dashboard_map_api

app = FastAPI(title="LawnRouter API")

# API Routers
app.include_router(photos.router)
app.include_router(optimization.router)
app.include_router(customers.router)
app.include_router(location.router)
app.include_router(companies.router)
app.include_router(vehicles.router)
app.include_router(crews.router)
app.include_router(service_plan.router)
app.include_router(route_plans.router)
app.include_router(depots.router)

# Dashboard Routers
app.include_router(dashboard_router.router)
app.include_router(dashboard_map_api.router)

handler = Mangum(app)
