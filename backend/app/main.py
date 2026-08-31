from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import os

from app.core.config import settings
from app.api.endpoints import agent, simulations, chat
from app.api.endpoints.flowsense import router as flowsense_router
from app.api.endpoints.simulate import router as simulate_router
from app.api.endpoints.module01 import router as module01_router, public_router as artifact_router
from app.api.endpoints.tutor import router as tutor_router

app = FastAPI(
    title=settings.APP_NAME,
    description="AirfoilLearner — Aerospace Design Tool",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agent.router, prefix=f"{settings.API_V1_PREFIX}/agent", tags=["Agent"])
app.include_router(simulations.router, prefix=f"{settings.API_V1_PREFIX}/simulations", tags=["Simulations"])
app.include_router(chat.router, prefix=f"{settings.API_V1_PREFIX}/chat", tags=["Chat"])
app.include_router(flowsense_router, prefix=f"{settings.API_V1_PREFIX}/flowsense", tags=["FlowSense"])
app.include_router(simulate_router, prefix=f"{settings.API_V1_PREFIX}/simulate", tags=["Simulate"])
app.include_router(module01_router, prefix=f"{settings.API_V1_PREFIX}/module01", tags=["Module01"])
app.include_router(tutor_router, prefix=f"{settings.API_V1_PREFIX}/tutor", tags=["Tutor"])
app.include_router(artifact_router, tags=["Artifacts"])

_STATIC = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=_STATIC), name="static")


@app.get("/observe")
def observe_panel():
    return FileResponse(os.path.join(_STATIC, "observe.html"))


@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "status": "running",
        "docs": "/docs",
        "observe": "/observe",
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "cfd": "NeuralFoil"}
