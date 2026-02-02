import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/lawnroute"
)

MAPBOX_ACCESS_TOKEN = os.getenv("MAPBOX_ACCESS_TOKEN", "")
MAPBOX_MATRIX_PROFILE = os.getenv("MAPBOX_MATRIX_PROFILE", "driving")
MAPBOX_BASE_URL = os.getenv("MAPBOX_BASE_URL", "https://api.mapbox.com")
