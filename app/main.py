import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.api.routes import router
from app.db.base import Base
from app.db.session import engine
from app.models import Review  # noqa: F401


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("Initializing database schema")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        if engine.dialect.name == "postgresql":
            await connection.execute(text("ALTER TABLE reviews ADD COLUMN IF NOT EXISTS tone VARCHAR(32)"))
            await connection.execute(text("ALTER TABLE reviews ADD COLUMN IF NOT EXISTS parent_id INTEGER"))
    yield


app = FastAPI(title="Reviews App", lifespan=lifespan)
app.include_router(router)
