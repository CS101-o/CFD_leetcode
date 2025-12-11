from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.endpoints import agent, simulations, chat

app = FastAPI(
    title=settings.APP_NAME, 
    description="AirfoilLearner - AI Agent + Ultra-fast CFD",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware, 
    allow_origins=settings.CORS_ORIGINS, 
    allow_credentials=True, 
    allow_methods=["*"], 
    allow_headers=["*"]
)

# Include all routers
app.include_router(agent.router, prefix=f"{settings.API_V1_PREFIX}/agent", tags=["Agent"])
app.include_router(simulations.router, prefix=f"{settings.API_V1_PREFIX}/simulations", tags=["Simulations"])
app.include_router(chat.router, prefix=f"{settings.API_V1_PREFIX}/chat", tags=["Chat"])

@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME, 
        "status": "running", 
        "docs": "/docs",
        "endpoints": {
            "agent": "/api/v1/agent",
            "simulations": "/api/v1/simulations",
            "chat": "/api/v1/chat"
        }
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy", 
        "agent": "FREE", 
        "cfd": "NeuralFoil",
        "features": ["agent", "simulations", "chat"]
    }