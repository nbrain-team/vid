from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from core.database import get_db
from models.media import Media, Tag, User
from api.auth import get_current_user
from services.storage_service import storage_service
from services.vector_service import vector_service

router = APIRouter()


class MediaResponse(BaseModel):
    id: int
    filename: str
    original_filename: str
    file_type: str
    mime_type: str
    file_size: int
    width: Optional[int]
    height: Optional[int]
    duration: Optional[float]
    caption: Optional[str]
    tags: List[str]
    title: Optional[str]
    description: Optional[str]
    license_type: str
    price: float
    preview_url: str
    thumbnail_url: Optional[str]
    created_at: datetime
    processed_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class MediaUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    license_type: Optional[str] = None
    price: Optional[float] = None
    tags: Optional[List[str]] = None


class MediaListResponse(BaseModel):
    items: List[MediaResponse]
    total: int
    page: int
    pages: int


@router.get("/{media_id}", response_model=MediaResponse)
async def get_media(
    media_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get details of a specific media item"""
    result = await db.execute(
        select(Media).where(
            and_(
                Media.id == media_id,
                Media.user_id == current_user.id
            )
        )
    )
    media = result.scalar_one_or_none()
    
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
    
    # Generate URLs
    preview_url = storage_service.get_file_url(media.storage_path)
    thumbnail_url = None
    if media.thumbnail_path:
        thumbnail_url = storage_service.get_file_url(media.thumbnail_path)
    
    return MediaResponse(
        id=media.id,
        filename=media.filename,
        original_filename=media.original_filename,
        file_type=media.file_type,
        mime_type=media.mime_type,
        file_size=media.file_size,
        width=media.width,
        height=media.height,
        duration=media.duration,
        caption=media.caption,
        tags=media.ai_tags or [],
        title=media.title,
        description=media.description,
        license_type=media.license_type,
        price=media.price,
        preview_url=preview_url,
        thumbnail_url=thumbnail_url,
        created_at=media.created_at,
        processed_at=media.processed_at
    )


@router.get("/", response_model=MediaListResponse)
async def list_media(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    file_type: Optional[str] = None,
    processed_only: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List user's media with pagination"""
    # Build query
    query = select(Media).where(Media.user_id == current_user.id)
    
    if file_type:
        query = query.where(Media.file_type == file_type)
    
    if processed_only:
        query = query.where(Media.processed_at.isnot(None))
    
    # Get total count
    count_query = select(func.count()).select_from(Media).where(Media.user_id == current_user.id)
    if file_type:
        count_query = count_query.where(Media.file_type == file_type)
    if processed_only:
        count_query = count_query.where(Media.processed_at.isnot(None))
    
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Calculate pagination
    total_pages = (total + page_size - 1) // page_size
    offset = (page - 1) * page_size
    
    # Get items
    query = query.order_by(Media.created_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(query)
    media_items = result.scalars().all()
    
    # Build response
    items = []
    for media in media_items:
        preview_url = storage_service.get_file_url(media.storage_path)
        thumbnail_url = None
        if media.thumbnail_path:
            thumbnail_url = storage_service.get_file_url(media.thumbnail_path)
        
        items.append(MediaResponse(
            id=media.id,
            filename=media.filename,
            original_filename=media.original_filename,
            file_type=media.file_type,
            mime_type=media.mime_type,
            file_size=media.file_size,
            width=media.width,
            height=media.height,
            duration=media.duration,
            caption=media.caption,
            tags=media.ai_tags or [],
            title=media.title,
            description=media.description,
            license_type=media.license_type,
            price=media.price,
            preview_url=preview_url,
            thumbnail_url=thumbnail_url,
            created_at=media.created_at,
            processed_at=media.processed_at
        ))
    
    return MediaListResponse(
        items=items,
        total=total,
        page=page,
        pages=total_pages
    )


@router.put("/{media_id}", response_model=MediaResponse)
async def update_media(
    media_id: int,
    media_update: MediaUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update media metadata"""
    result = await db.execute(
        select(Media).where(
            and_(
                Media.id == media_id,
                Media.user_id == current_user.id
            )
        )
    )
    media = result.scalar_one_or_none()
    
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
    
    # Update fields
    if media_update.title is not None:
        media.title = media_update.title
    if media_update.description is not None:
        media.description = media_update.description
    if media_update.license_type is not None:
        media.license_type = media_update.license_type
    if media_update.price is not None:
        media.price = media_update.price
    if media_update.tags is not None:
        media.ai_tags = media_update.tags
        # Update vector database metadata
        if media.embedding_id:
            vector_service.update_metadata(
                media.embedding_id,
                {"tags": media_update.tags}
            )
    
    media.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(media)
    
    # Generate URLs
    preview_url = storage_service.get_file_url(media.storage_path)
    thumbnail_url = None
    if media.thumbnail_path:
        thumbnail_url = storage_service.get_file_url(media.thumbnail_path)
    
    return MediaResponse(
        id=media.id,
        filename=media.filename,
        original_filename=media.original_filename,
        file_type=media.file_type,
        mime_type=media.mime_type,
        file_size=media.file_size,
        width=media.width,
        height=media.height,
        duration=media.duration,
        caption=media.caption,
        tags=media.ai_tags or [],
        title=media.title,
        description=media.description,
        license_type=media.license_type,
        price=media.price,
        preview_url=preview_url,
        thumbnail_url=thumbnail_url,
        created_at=media.created_at,
        processed_at=media.processed_at
    )


@router.delete("/{media_id}")
async def delete_media(
    media_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a media item"""
    result = await db.execute(
        select(Media).where(
            and_(
                Media.id == media_id,
                Media.user_id == current_user.id
            )
        )
    )
    media = result.scalar_one_or_none()
    
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
    
    try:
        # Delete from storage
        storage_service.delete_file(media.storage_path)
        if media.thumbnail_path:
            storage_service.delete_file(media.thumbnail_path)
        
        # Delete from vector database
        if media.embedding_id:
            vector_service.delete_embedding(media.embedding_id)
        
        # Delete from database
        await db.delete(media)
        await db.commit()
        
        return {"message": "Media deleted successfully"}
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e)) 