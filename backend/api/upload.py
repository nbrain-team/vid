from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import os
import tempfile
import magic
from datetime import datetime
from sqlalchemy import select

from core.database import get_db
from core.config import settings
from models.media import Media, User
from api.auth import get_current_user
from services.storage_service import storage_service
from core.celery_app import process_media_task
from pydantic import BaseModel

router = APIRouter()


class UploadResponse(BaseModel):
    id: int
    filename: str
    original_filename: str
    file_type: str
    status: str
    message: str


def validate_file(file: UploadFile) -> tuple[str, str]:
    """Validate uploaded file"""
    # Check file size
    if file.size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {settings.MAX_UPLOAD_SIZE / 1024 / 1024}MB"
        )
    
    # Check file extension
    file_ext = os.path.splitext(file.filename)[1].lower().replace(".", "")
    if file_ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed types: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )
    
    # Determine file type
    file_type = "image" if file_ext in ["jpg", "jpeg", "png", "gif"] else "video"
    
    return file_ext, file_type


@router.post("/single", response_model=UploadResponse)
async def upload_single(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload a single media file"""
    # Validate file
    file_ext, file_type = validate_file(file)
    
    try:
        # Save file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_ext}") as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name
        
        # Reset file pointer
        await file.seek(0)
        
        # Detect MIME type
        mime = magic.Magic(mime=True)
        mime_type = mime.from_file(tmp_path)
        
        # Upload to storage
        storage_path, file_size = storage_service.upload_file(
            file.file,
            file.filename,
            mime_type,
            current_user.id
        )
        
        # Create database entry
        media_entry = Media(
            filename=os.path.basename(storage_path),
            original_filename=file.filename,
            file_type=file_type,
            mime_type=mime_type,
            file_size=file_size,
            storage_path=storage_path,
            user_id=current_user.id
        )
        
        db.add(media_entry)
        await db.commit()
        await db.refresh(media_entry)
        
        # Queue for AI processing
        process_media_task.delay(media_entry.id, tmp_path)
        
        return UploadResponse(
            id=media_entry.id,
            filename=media_entry.filename,
            original_filename=media_entry.original_filename,
            file_type=media_entry.file_type,
            status="processing",
            message="File uploaded successfully. AI processing started."
        )
        
    except Exception as e:
        # Clean up on error
        if 'tmp_path' in locals() and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bulk", response_model=List[UploadResponse])
async def upload_bulk(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload multiple media files"""
    if len(files) > 10:
        raise HTTPException(
            status_code=400,
            detail="Maximum 10 files can be uploaded at once"
        )
    
    responses = []
    
    for file in files:
        try:
            # Process each file
            response = await upload_single(
                background_tasks,
                file,
                current_user,
                db
            )
            responses.append(response)
        except HTTPException as e:
            responses.append(
                UploadResponse(
                    id=0,
                    filename="",
                    original_filename=file.filename,
                    file_type="unknown",
                    status="error",
                    message=e.detail
                )
            )
    
    return responses


@router.get("/status/{media_id}")
async def get_upload_status(
    media_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Check processing status of uploaded media"""
    result = await db.execute(
        select(Media).where(
            Media.id == media_id,
            Media.user_id == current_user.id
        )
    )
    media = result.scalar_one_or_none()
    
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
    
    status = "completed" if media.processed_at else "processing"
    
    return {
        "id": media.id,
        "status": status,
        "processed_at": media.processed_at,
        "caption": media.caption,
        "tags": media.ai_tags
    } 