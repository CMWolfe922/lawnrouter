import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    'postgresql://neondb_owner:npg_ytG73EfmYpzR@ep-frosty-bird-ahx2boom-pooler.c-3.us-east-1.aws.neon.tech/thelawnrouter?sslmode=require&channel_binding=require'
)

MAPBOX_ACCESS_TOKEN = os.environ.get("MAPBOX_ACCESS_TOKEN", "")
MAPBOX_MATRIX_PROFILE = os.environ.get("MAPBOX_MATRIX_PROFILE", "driving")
MAPBOX_BASE_URL = os.environ.get("MAPBOX_BASE_URL", "https://api.mapbox.com")

# Mapbox tokens - load from environment, no hardcoded secrets
MAPBOX_API_KEY = os.environ.get("MAPBOX_API_KEY", "")
MAPBOX_PUBLIC_API_KEY = os.environ.get("MAPBOX_PUBLIC_API_KEY", "")
AWS_S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME", "lawnrouter-storage-bucket")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

# Dashboard / Static Assets
STATIC_URL = os.environ.get("STATIC_URL", "")
MAPBOX_PUBLIC_TOKEN = os.environ.get("MAPBOX_PUBLIC_TOKEN", MAPBOX_PUBLIC_API_KEY)
MAP_STYLE = os.environ.get("MAP_STYLE", "mapbox://styles/mapbox/streets-v12")