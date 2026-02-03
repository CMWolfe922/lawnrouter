from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from typing import AsyncIterator
import ssl
from .config import DATABASE_URL

# Convert postgresql:// to postgresql+asyncpg:// for async driver
# Also remove sslmode and channel_binding params as asyncpg handles SSL differently
_async_url = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
# Remove query params that asyncpg doesn't understand
if "?" in _async_url:
    base, params = _async_url.split("?", 1)
    # Filter out incompatible params
    kept_params = []
    for param in params.split("&"):
        if not param.startswith(("sslmode=", "channel_binding=")):
            kept_params.append(param)
    _async_url = base + ("?" + "&".join(kept_params) if kept_params else "")

# Create SSL context for Neon (requires SSL)
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

engine = create_async_engine(
    _async_url,
    echo=False,
    pool_pre_ping=True,
    connect_args={"ssl": ssl_context}
)

SessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession
)

async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
