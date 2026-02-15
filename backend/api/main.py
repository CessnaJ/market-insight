"""FastAPI Main Application"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application Settings"""
    api_host: str = "0.0.0.0"
    api_port: int = 3000
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    from storage.db import init_database
    init_database()
    print("Database initialized")
    yield
    # Shutdown
    print("Application shutdown")


# Create FastAPI app
app = FastAPI(
    title="Market Insight API",
    description="Personal Investment Intelligence System API",
    version="0.1.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──── Health Check ────
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "message": "Market Insight API is running"}


# ──── API Routes ────
from api.routes import portfolio, thoughts, content, reports, websocket

app.include_router(portfolio.router, prefix="/api/v1/portfolio", tags=["Portfolio"])
app.include_router(thoughts.router, prefix="/api/v1/thoughts", tags=["Thoughts"])
app.include_router(content.router, prefix="/api/v1", tags=["Content"])
app.include_router(reports.router, prefix="/api/v1", tags=["Reports"])
app.include_router(websocket.router, prefix="/api/v1", tags=["WebSocket"])


# ──── Root Endpoint ────
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Market Insight API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
        log_level=settings.log_level.lower()
    )
