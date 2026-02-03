from fastapi import FastAPI
from mangum import Mangum

from app.routers import photos, optimization
from app.dashboard import router as dashboard_router
from app.dashboard import map_api as dashboard_map_api

app = FastAPI(title="LawnRouter API")

# API Routers
app.include_router(photos.router)
app.include_router(optimization.router)

# Dashboard Routers
app.include_router(dashboard_router.router)
app.include_router(dashboard_map_api.router)

handler = Mangum(app)
