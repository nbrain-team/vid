from minio import Minio
from minio.error import S3Error
import os
import uuid
from typing import BinaryIO, Optional, Tuple
import logging
from core.config import settings
from PIL import Image
import io

logger = logging.getLogger(__name__)


class StorageService:
    def __init__(self):
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_USE_SSL
        )
        self.bucket_name = settings.MINIO_BUCKET_NAME
        self._ensure_bucket()
    
    def _ensure_bucket(self):
        """Ensure storage bucket exists"""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"Created bucket: {self.bucket_name}")
            else:
                logger.info(f"Bucket already exists: {self.bucket_name}")
        except S3Error as e:
            logger.error(f"Error ensuring bucket: {str(e)}")
            raise
    
    def upload_file(
        self, 
        file_data: BinaryIO, 
        original_filename: str,
        content_type: str,
        user_id: Optional[int] = None
    ) -> Tuple[str, int]:
        """Upload file to storage and return path and size"""
        try:
            # Generate unique filename
            file_extension = os.path.splitext(original_filename)[1]
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            
            # Organize by user and date
            from datetime import datetime
            date_path = datetime.now().strftime("%Y/%m/%d")
            
            if user_id:
                object_name = f"users/{user_id}/{date_path}/{unique_filename}"
            else:
                object_name = f"public/{date_path}/{unique_filename}"
            
            # Get file size
            file_data.seek(0, 2)  # Seek to end
            file_size = file_data.tell()
            file_data.seek(0)  # Reset to beginning
            
            # Upload file
            self.client.put_object(
                self.bucket_name,
                object_name,
                file_data,
                file_size,
                content_type=content_type
            )
            
            logger.info(f"Uploaded file: {object_name}")
            return object_name, file_size
        except Exception as e:
            logger.error(f"Error uploading file: {str(e)}")
            raise
    
    def generate_thumbnail(
        self, 
        file_data: BinaryIO,
        original_filename: str,
        max_size: Tuple[int, int] = (300, 300)
    ) -> Optional[str]:
        """Generate and upload thumbnail for image"""
        try:
            # Open image
            image = Image.open(file_data)
            
            # Create thumbnail
            image.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Save to bytes
            thumb_io = io.BytesIO()
            image.save(thumb_io, format='JPEG', quality=85)
            thumb_io.seek(0)
            
            # Upload thumbnail
            thumb_filename = f"thumb_{original_filename}"
            thumb_path, _ = self.upload_file(
                thumb_io,
                thumb_filename,
                "image/jpeg"
            )
            
            return thumb_path
        except Exception as e:
            logger.error(f"Error generating thumbnail: {str(e)}")
            return None
    
    def get_file_url(self, object_name: str, expires: int = 3600) -> str:
        """Get presigned URL for file access"""
        try:
            url = self.client.presigned_get_object(
                self.bucket_name,
                object_name,
                expires=expires
            )
            return url
        except Exception as e:
            logger.error(f"Error getting file URL: {str(e)}")
            raise
    
    def delete_file(self, object_name: str):
        """Delete file from storage"""
        try:
            self.client.remove_object(self.bucket_name, object_name)
            logger.info(f"Deleted file: {object_name}")
        except Exception as e:
            logger.error(f"Error deleting file: {str(e)}")
            raise
    
    def get_file(self, object_name: str) -> bytes:
        """Download file from storage"""
        try:
            response = self.client.get_object(self.bucket_name, object_name)
            data = response.read()
            response.close()
            response.release_conn()
            return data
        except Exception as e:
            logger.error(f"Error getting file: {str(e)}")
            raise
    
    def file_exists(self, object_name: str) -> bool:
        """Check if file exists in storage"""
        try:
            self.client.stat_object(self.bucket_name, object_name)
            return True
        except S3Error as e:
            if e.code == 'NoSuchKey':
                return False
            raise


# Singleton instance
storage_service = StorageService() 