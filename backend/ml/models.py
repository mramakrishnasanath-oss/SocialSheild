import logging
from typing import Any

logger = logging.getLogger(__name__)

class ModelRegistry:
    def __init__(self):
        self.device = "cpu"
        self._models = {}
        
    def load_all(self):
        self._models['image'] = "mock_image_model"
        self._models['audio'] = "mock_audio_model"
        self._models['video'] = "mock_video_model"
        logger.info("Loaded mock models for Render Free tier")

    def get(self, name: str) -> Any:
        return self._models.get(name)

model_registry = ModelRegistry()
IMAGE_TRANSFORM = None
