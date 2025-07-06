import cv2
import numpy as np
import insightface
import logging
from PIL import Image
from io import BytesIO

logger = logging.getLogger(__name__)

class FaceEncoder:
    def __init__(self, model_name="buffalo_l"):
        self.model = self._load_model(model_name)
        
    def _load_model(self, model_name):
        try:
            model = insightface.app.FaceAnalysis(name=model_name)
            model.prepare(ctx_id=0)
            logger.info("Face model loaded successfully")
            return model
        except Exception as e:
            logger.error(f"Failed to load face model: {str(e)}")
            return None

    def encode_faces(self, image_bytes):
        """Process image bytes and extract face embeddings"""
        if not self.model:
            return []
        
        try:
            # Convert bytes to image array
            img = np.array(Image.open(BytesIO(image_bytes)))
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            # Detect faces
            faces = self.model.get(img_rgb)
            return [face.embedding for face in faces] if faces else []
        except Exception as e:
            logger.error(f"Face encoding failed: {str(e)}")
            return []
