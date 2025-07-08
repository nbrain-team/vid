import torch
import clip
from PIL import Image
from transformers import BlipProcessor, BlipForConditionalGeneration
import numpy as np
from typing import List, Dict, Tuple
import logging
from core.config import settings

logger = logging.getLogger(__name__)


class AIService:
    def __init__(self):
        self.device = settings.DEVICE
        self.clip_model = None
        self.clip_preprocess = None
        self.blip_processor = None
        self.blip_model = None
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize AI models"""
        try:
            # Load CLIP model
            logger.info(f"Loading CLIP model: {settings.CLIP_MODEL_NAME}")
            self.clip_model, self.clip_preprocess = clip.load(
                settings.CLIP_MODEL_NAME, 
                device=self.device
            )
            
            # Load BLIP model for captioning
            logger.info(f"Loading BLIP model: {settings.BLIP_MODEL_NAME}")
            self.blip_processor = BlipProcessor.from_pretrained(settings.BLIP_MODEL_NAME)
            self.blip_model = BlipForConditionalGeneration.from_pretrained(
                settings.BLIP_MODEL_NAME
            ).to(self.device)
            
            logger.info("AI models initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing AI models: {str(e)}")
            raise
    
    def extract_image_embedding(self, image_path: str) -> np.ndarray:
        """Extract CLIP embedding from image"""
        try:
            image = Image.open(image_path).convert("RGB")
            image_input = self.clip_preprocess(image).unsqueeze(0).to(self.device)
            
            with torch.no_grad():
                image_features = self.clip_model.encode_image(image_input)
                image_features = image_features / image_features.norm(dim=-1, keepdim=True)
            
            return image_features.cpu().numpy().flatten()
        except Exception as e:
            logger.error(f"Error extracting embedding: {str(e)}")
            raise
    
    def generate_caption(self, image_path: str) -> str:
        """Generate caption using BLIP"""
        try:
            image = Image.open(image_path).convert("RGB")
            inputs = self.blip_processor(image, return_tensors="pt").to(self.device)
            
            with torch.no_grad():
                out = self.blip_model.generate(**inputs, max_length=50)
                caption = self.blip_processor.decode(out[0], skip_special_tokens=True)
            
            return caption
        except Exception as e:
            logger.error(f"Error generating caption: {str(e)}")
            raise
    
    def extract_tags_from_caption(self, caption: str) -> List[str]:
        """Extract relevant tags from caption"""
        # Simple implementation - can be enhanced with NLP
        import re
        
        # Common stop words to filter out
        stop_words = {
            'a', 'an', 'the', 'is', 'are', 'was', 'were', 'in', 'on', 
            'at', 'to', 'for', 'of', 'with', 'by', 'from', 'and', 'or'
        }
        
        # Extract words
        words = re.findall(r'\b\w+\b', caption.lower())
        
        # Filter and return unique tags
        tags = []
        for word in words:
            if len(word) > 2 and word not in stop_words:
                tags.append(word)
        
        return list(set(tags))
    
    def process_image(self, image_path: str) -> Dict:
        """Process image to extract all AI metadata"""
        try:
            # Generate caption
            caption = self.generate_caption(image_path)
            
            # Extract embedding
            embedding = self.extract_image_embedding(image_path)
            
            # Extract tags from caption
            tags = self.extract_tags_from_caption(caption)
            
            # Add object detection tags (simplified for now)
            # In production, you'd use a proper object detection model
            object_tags = self._detect_objects(image_path)
            tags.extend(object_tags)
            
            return {
                "caption": caption,
                "embedding": embedding.tolist(),
                "tags": list(set(tags)),
                "embedding_dim": len(embedding)
            }
        except Exception as e:
            logger.error(f"Error processing image: {str(e)}")
            raise
    
    def _detect_objects(self, image_path: str) -> List[str]:
        """Placeholder for object detection - would use YOLO or similar in production"""
        # This is a simplified version - in production, use proper object detection
        return []
    
    def search_by_text(self, query: str) -> np.ndarray:
        """Convert text query to CLIP embedding for search"""
        try:
            text = clip.tokenize([query]).to(self.device)
            
            with torch.no_grad():
                text_features = self.clip_model.encode_text(text)
                text_features = text_features / text_features.norm(dim=-1, keepdim=True)
            
            return text_features.cpu().numpy().flatten()
        except Exception as e:
            logger.error(f"Error encoding text: {str(e)}")
            raise


# Singleton instance
ai_service = AIService() 