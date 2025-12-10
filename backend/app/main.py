from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.endpoints import agent

app = FastAPI(title=settings.APP_NAME, version="1.0.0")

app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

app.include_router(agent.router, prefix=f"{settings.API_V1_PREFIX}/agent", tags=["Agent"])

@app.get("/")
async def root():
    return {"app": settings.APP_NAME, "status": "running", "docs": "/docs"}

@app.get("/health")
async def health():
    return {"status": "healthy", "agent": "FREE", "cfd": "NeuralFoil"}
