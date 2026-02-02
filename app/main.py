from fastapi import FastAPI
from .routers import route_plans

app = FastAPI(title="Lawn Route Optimizer")

app.include_router(route_plans.router)
