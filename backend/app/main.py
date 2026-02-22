from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="SharpPicks", lifespan=lifespan)
app.include_router(api_router, prefix="/api/v1")
