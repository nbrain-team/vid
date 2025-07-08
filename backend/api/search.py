from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_
from typing import List, Optional
from pydantic import BaseModel

from core.database import get_db
from models.media import Media, Tag, User
from api.auth import get_current_user
from services.ai_service import ai_service
from services.vector_service import vector_service
from services.storage_service import storage_service

router = APIRouter()


class SearchResult(BaseModel):
    id: int
    filename: str
    original_filename: str
    file_type: str
    caption: Optional[str]
    tags: List[str]
    score: Optional[float]
    thumbnail_url: Optional[str]
    preview_url: str
    width: Optional[int]
    height: Optional[int]
    duration: Optional[float]


class SearchRequest(BaseModel):
    query: str
    file_type: Optional[str] = None
    tags: Optional[List[str]] = None
    limit: int = 20
    min_score: float = 0.7


@router.post("/semantic", response_model=List[SearchResult])
async def semantic_search(
    search_request: SearchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Perform semantic search using natural language"""
    try:
        # Convert query to embedding
        query_embedding = ai_service.search_by_text(search_request.query)
        
        # Search in vector database
        filters = {}
        if search_request.file_type:
            filters["file_type"] = search_request.file_type
        if search_request.tags:
            filters["tags"] = search_request.tags
        
        vector_results = vector_service.search_similar(
            query_embedding.tolist(),
            limit=search_request.limit,
            score_threshold=search_request.min_score,
            filters=filters
        )
        
        # Get media details from database
        media_ids = [r["media_id"] for r in vector_results]
        if not media_ids:
            return []
        
        result = await db.execute(
            select(Media).where(
                and_(
                    Media.id.in_(media_ids),
                    Media.user_id == current_user.id
                )
            )
        )
        media_items = {m.id: m for m in result.scalars().all()}
        
        # Build response
        search_results = []
        for vr in vector_results:
            media = media_items.get(vr["media_id"])
            if media:
                # Generate URLs
                preview_url = storage_service.get_file_url(media.storage_path)
                thumbnail_url = None
                if media.thumbnail_path:
                    thumbnail_url = storage_service.get_file_url(media.thumbnail_path)
                
                search_results.append(SearchResult(
                    id=media.id,
                    filename=media.filename,
                    original_filename=media.original_filename,
                    file_type=media.file_type,
                    caption=media.caption,
                    tags=media.ai_tags or [],
                    score=vr["score"],
                    thumbnail_url=thumbnail_url,
                    preview_url=preview_url,
                    width=media.width,
                    height=media.height,
                    duration=media.duration
                ))
        
        return search_results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/keyword", response_model=List[SearchResult])
async def keyword_search(
    q: str = Query(..., description="Search query"),
    file_type: Optional[str] = None,
    tags: Optional[List[str]] = Query(None),
    limit: int = Query(20, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Perform keyword search on metadata"""
    try:
        # Build query
        query = select(Media).where(Media.user_id == current_user.id)
        
        # Add search conditions
        search_conditions = []
        
        # Search in filename, title, description, caption
        search_pattern = f"%{q}%"
        search_conditions.append(
            or_(
                Media.original_filename.ilike(search_pattern),
                Media.title.ilike(search_pattern),
                Media.description.ilike(search_pattern),
                Media.caption.ilike(search_pattern)
            )
        )
        
        if search_conditions:
            query = query.where(and_(*search_conditions))
        
        # Filter by file type
        if file_type:
            query = query.where(Media.file_type == file_type)
        
        # Filter by tags (using JSON contains)
        if tags:
            for tag in tags:
                query = query.where(Media.ai_tags.contains([tag]))
        
        # Execute query
        query = query.limit(limit)
        result = await db.execute(query)
        media_items = result.scalars().all()
        
        # Build response
        search_results = []
        for media in media_items:
            # Generate URLs
            preview_url = storage_service.get_file_url(media.storage_path)
            thumbnail_url = None
            if media.thumbnail_path:
                thumbnail_url = storage_service.get_file_url(media.thumbnail_path)
            
            search_results.append(SearchResult(
                id=media.id,
                filename=media.filename,
                original_filename=media.original_filename,
                file_type=media.file_type,
                caption=media.caption,
                tags=media.ai_tags or [],
                score=None,  # No relevance score for keyword search
                thumbnail_url=thumbnail_url,
                preview_url=preview_url,
                width=media.width,
                height=media.height,
                duration=media.duration
            ))
        
        return search_results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tags")
async def get_popular_tags(
    limit: int = Query(50, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get popular tags from user's media"""
    try:
        # Get all tags from user's media
        result = await db.execute(
            select(Media.ai_tags).where(
                and_(
                    Media.user_id == current_user.id,
                    Media.ai_tags.isnot(None)
                )
            )
        )
        
        # Count tag occurrences
        tag_counts = {}
        for row in result:
            if row[0]:  # ai_tags
                for tag in row[0]:
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        # Sort by count and return top tags
        sorted_tags = sorted(
            tag_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]
        
        return [
            {"tag": tag, "count": count}
            for tag, count in sorted_tags
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 