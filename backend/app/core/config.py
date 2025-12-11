from typing import List
from pydantic_settings import BaseSettings
from pydantic import field_validator

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "AirfoilLearner"
    ENV: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]
    
    # Database (optional)
    DATABASE_URL: str = "sqlite:///./airfoil.db"
    DATABASE_URL_SYNC: str = "sqlite:///./airfoil.db"
    
    # Redis (optional)
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # JWT (optional)
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # AI APIs (optional)
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    AI_PROVIDER: str = "free"
    AI_MODEL: str = "claude-3-5-sonnet-20241022"
    
    # XFoil (optional)
    XFOIL_PATH: str = "/usr/local/bin/xfoil"
    XFOIL_TIMEOUT: int = 60
    MAX_ITERATIONS: int = 100
    
    # PINN (optional)
    PINN_MODEL_PATH: str = "./models/pinn_airfoil.pth"
    ENABLE_PINN: bool = False
    
    # Rate limiting (optional)
    MAX_SIMULATIONS_PER_HOUR: int = 20
    MAX_CHAT_MESSAGES_PER_MINUTE: int = 10
    
    # File storage (optional)
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 10
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v):
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"

# CREATE THE SETTINGS INSTANCE HERE!
settings = Settings()