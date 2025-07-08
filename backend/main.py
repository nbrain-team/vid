from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from core.config import settings
from core.database import engine, Base

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up...")
    try:
        # Create database tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        # Continue anyway - tables might already exist
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# Set up CORS - simplified for testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import routers with error handling
try:
    from api import auth, media, search, upload
    app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
    app.include_router(upload.router, prefix=f"{settings.API_V1_STR}/upload", tags=["upload"])
    app.include_router(media.router, prefix=f"{settings.API_V1_STR}/media", tags=["media"])
    app.include_router(search.router, prefix=f"{settings.API_V1_STR}/search", tags=["search"])
    logger.info("All routers loaded successfully")
except Exception as e:
    logger.error(f"Error loading routers: {e}")


@app.get("/")
async def root():
    return {
        "message": "Media Index Platform API",
        "version": "1.0.0",
        "docs": f"{settings.API_V1_STR}/docs",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "mediaindex-api"}


@app.get("/test")
async def test_endpoint():
    return {
        "message": "Test endpoint working",
        "cors_origins": settings.BACKEND_CORS_ORIGINS,
        "database_url_configured": bool(settings.DATABASE_URL),
        "redis_url_configured": bool(settings.REDIS_URL)
    } 