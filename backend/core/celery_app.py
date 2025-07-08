from celery import Celery
from core.config import settings
import os
from datetime import datetime
from PIL import Image
import cv2

# Create Celery instance
celery_app = Celery(
    "media_index",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["core.celery_app"]
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
)


@celery_app.task(bind=True, max_retries=3)
def process_media_task(self, media_id: int, file_path: str):
    """Process uploaded media file"""
    try:
        # Import here to avoid circular imports
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from models.media import Media
        from services.ai_service import ai_service
        from services.vector_service import vector_service
        from services.storage_service import storage_service
        
        # Create sync database session
        engine = create_engine(settings.DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        try:
            # Get media record
            media = db.query(Media).filter(Media.id == media_id).first()
            if not media:
                raise ValueError(f"Media {media_id} not found")
            
            # Process based on file type
            if media.file_type == "image":
                # Get image dimensions
                with Image.open(file_path) as img:
                    media.width, media.height = img.size
                
                # Generate thumbnail
                with open(file_path, 'rb') as f:
                    thumbnail_path = storage_service.generate_thumbnail(
                        f, 
                        media.original_filename
                    )
                    media.thumbnail_path = thumbnail_path
                
                # Process with AI
                ai_results = ai_service.process_image(file_path)
                
                # Update media record
                media.caption = ai_results["caption"]
                media.ai_tags = ai_results["tags"]
                
                # Add to vector database
                embedding_id = vector_service.add_embedding(
                    ai_results["embedding"],
                    media_id,
                    {
                        "file_type": media.file_type,
                        "caption": ai_results["caption"],
                        "tags": ai_results["tags"],
                        "filename": media.original_filename,
                        "created_at": media.created_at.isoformat()
                    }
                )
                media.embedding_id = embedding_id
                
            elif media.file_type == "video":
                # Get video properties
                cap = cv2.VideoCapture(file_path)
                media.width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                media.height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = cap.get(cv2.CAP_PROP_FPS)
                frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                media.duration = frame_count / fps if fps > 0 else 0
                
                # Extract key frame for thumbnail and AI processing
                cap.set(cv2.CAP_PROP_POS_FRAMES, min(30, frame_count // 2))
                ret, frame = cap.read()
                cap.release()
                
                if ret:
                    # Save frame as temporary image
                    temp_image_path = f"{file_path}_frame.jpg"
                    cv2.imwrite(temp_image_path, frame)
                    
                    # Generate thumbnail from frame
                    with open(temp_image_path, 'rb') as f:
                        thumbnail_path = storage_service.generate_thumbnail(
                            f,
                            media.original_filename
                        )
                        media.thumbnail_path = thumbnail_path
                    
                    # Process frame with AI
                    ai_results = ai_service.process_image(temp_image_path)
                    
                    # Update media record
                    media.caption = f"Video: {ai_results['caption']}"
                    media.ai_tags = ai_results["tags"]
                    
                    # Add to vector database
                    embedding_id = vector_service.add_embedding(
                        ai_results["embedding"],
                        media_id,
                        {
                            "file_type": media.file_type,
                            "caption": media.caption,
                            "tags": ai_results["tags"],
                            "filename": media.original_filename,
                            "created_at": media.created_at.isoformat()
                        }
                    )
                    media.embedding_id = embedding_id
                    
                    # Clean up temp file
                    os.unlink(temp_image_path)
            
            # Mark as processed
            media.processed_at = datetime.utcnow()
            db.commit()
            
            # Clean up original temp file
            if os.path.exists(file_path):
                os.unlink(file_path)
            
            return {"status": "success", "media_id": media_id}
            
        finally:
            db.close()
            
    except Exception as e:
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=2 ** self.request.retries) 