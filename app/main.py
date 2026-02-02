from fastapi import FastAPI
from mangum import Mangum

from app.routers import photos, optimization

app = FastAPI()

app.include_router(photos.router)
app.include_router(optimization.router)

handler = Mangum(app)
