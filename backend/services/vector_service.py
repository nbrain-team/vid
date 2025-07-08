from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, Range
from typing import List, Dict, Optional
import uuid
import logging
from core.config import settings

logger = logging.getLogger(__name__)


class VectorService:
    def __init__(self):
        # Support both local and cloud Qdrant
        if settings.QDRANT_API_KEY:
            # Qdrant Cloud configuration
            self.client = QdrantClient(
                url=f"https://{settings.QDRANT_HOST}",
                api_key=settings.QDRANT_API_KEY,
            )
        else:
            # Local Qdrant configuration
            self.client = QdrantClient(
                host=settings.QDRANT_HOST,
                port=settings.QDRANT_PORT
            )
        self.collection_name = settings.QDRANT_COLLECTION_NAME
        self._ensure_collection()
    
    def _ensure_collection(self):
        """Ensure vector collection exists"""
        try:
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]
            
            if self.collection_name not in collection_names:
                # Create collection with CLIP embedding dimensions (512 for ViT-B/32)
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=512,  # CLIP ViT-B/32 dimension
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created collection: {self.collection_name}")
            else:
                logger.info(f"Collection already exists: {self.collection_name}")
        except Exception as e:
            logger.error(f"Error ensuring collection: {str(e)}")
            raise
    
    def add_embedding(self, embedding: List[float], media_id: int, metadata: Dict) -> str:
        """Add embedding to vector database"""
        try:
            point_id = str(uuid.uuid4())
            
            point = PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    "media_id": media_id,
                    "file_type": metadata.get("file_type", "image"),
                    "caption": metadata.get("caption", ""),
                    "tags": metadata.get("tags", []),
                    "filename": metadata.get("filename", ""),
                    "created_at": metadata.get("created_at", "")
                }
            )
            
            self.client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )
            
            logger.info(f"Added embedding {point_id} for media {media_id}")
            return point_id
        except Exception as e:
            logger.error(f"Error adding embedding: {str(e)}")
            raise
    
    def search_similar(
        self, 
        query_embedding: List[float], 
        limit: int = 20,
        score_threshold: float = 0.7,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """Search for similar media using embedding"""
        try:
            # Build filter if provided
            qdrant_filter = None
            if filters:
                conditions = []
                
                if "file_type" in filters:
                    conditions.append(
                        FieldCondition(
                            key="file_type",
                            match={"value": filters["file_type"]}
                        )
                    )
                
                if "tags" in filters and filters["tags"]:
                    for tag in filters["tags"]:
                        conditions.append(
                            FieldCondition(
                                key="tags",
                                match={"any": [tag]}
                            )
                        )
                
                if conditions:
                    qdrant_filter = Filter(must=conditions)
            
            # Perform search
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=qdrant_filter
            )
            
            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "id": result.id,
                    "score": result.score,
                    "media_id": result.payload.get("media_id"),
                    "caption": result.payload.get("caption"),
                    "tags": result.payload.get("tags", []),
                    "filename": result.payload.get("filename"),
                    "file_type": result.payload.get("file_type")
                })
            
            return formatted_results
        except Exception as e:
            logger.error(f"Error searching similar: {str(e)}")
            raise
    
    def delete_embedding(self, embedding_id: str):
        """Delete embedding from vector database"""
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=[embedding_id]
            )
            logger.info(f"Deleted embedding: {embedding_id}")
        except Exception as e:
            logger.error(f"Error deleting embedding: {str(e)}")
            raise
    
    def update_metadata(self, embedding_id: str, metadata: Dict):
        """Update metadata for existing embedding"""
        try:
            self.client.update_payload(
                collection_name=self.collection_name,
                payload=metadata,
                points=[embedding_id]
            )
            logger.info(f"Updated metadata for embedding: {embedding_id}")
        except Exception as e:
            logger.error(f"Error updating metadata: {str(e)}")
            raise
    
    def get_collection_info(self) -> Dict:
        """Get information about the collection"""
        try:
            info = self.client.get_collection(self.collection_name)
            return {
                "name": info.name,
                "vector_size": info.config.params.vectors.size,
                "distance": info.config.params.vectors.distance,
                "points_count": info.points_count
            }
        except Exception as e:
            logger.error(f"Error getting collection info: {str(e)}")
            raise


# Singleton instance
vector_service = VectorService() 