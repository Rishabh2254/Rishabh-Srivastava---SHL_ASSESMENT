"""FastAPI application factory."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.logging import setup_logging


@asynccontextmanager
async def lifespan(_: FastAPI):
    setup_logging()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="SHL Assessment Recommender",
        version="1.0.0",
        description="Conversational agent for SHL Individual Test Solutions recommendations",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )
    app.include_router(router)
    return app
