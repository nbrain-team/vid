from typing import List, Union
from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl, validator
import os


class Settings(BaseSettings):
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Media Index Platform"
    
    # Database
    DATABASE_URL: str = "postgresql://mediaindex:mediaindex123@localhost:5432/mediaindex_db"
    
    # Vector Database
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION_NAME: str = "media_embeddings"
    QDRANT_API_KEY: str = ""  # For Qdrant Cloud
    
    # Object Storage - with defaults that won't crash if not configured
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET_NAME: str = "media-storage"
    MINIO_USE_SSL: bool = False
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    
    # Authentication
    JWT_SECRET: str = "your-secret-key-change-this-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    
    # AI Models
    CLIP_MODEL_NAME: str = "ViT-B/32"
    BLIP_MODEL_NAME: str = "Salesforce/blip-image-captioning-base"
    DEVICE: str = "cpu"
    
    # CORS - Allow all origins for initial testing
    BACKEND_CORS_ORIGINS: List[str] = ["*"]
    
    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    # Upload Settings
    MAX_UPLOAD_SIZE: int = 104857600  # 100MB
    ALLOWED_EXTENSIONS: List[str] = ["jpg", "jpeg", "png", "gif", "mp4", "mov", "avi", "webm"]
    
    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    
    class Config:
        case_sensitive = True
        env_file = ".env"


settings = Settings() 