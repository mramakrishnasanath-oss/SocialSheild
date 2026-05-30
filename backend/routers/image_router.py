from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
import uuid
import random
import logging
from datetime import datetime

from ml.models import model_registry
from utils.auth import get_current_user
from models.scan_result import ScanResult, MediaType, VerdictLevel
import io

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/image")
async def scan_image(file: UploadFile = File(...), user_id: str = Depends(get_current_user)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    contents = await file.read()
    if len(contents) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image too large (max 20MB)")
    
    # Mock analysis logic based on file size hash to make it deterministic-ish
    seed = len(contents) % 100
    fake_prob = min(0.99, max(0.01, seed / 100.0))
    real_prob = 1.0 - fake_prob
    
    if fake_prob >= 0.75:
        verdict = VerdictLevel.FAKE
        risk = "HIGH"
        explanations = ["High probability of AI-generated facial features", "Inconsistent lighting patterns detected"]
    elif fake_prob >= 0.45:
        verdict = VerdictLevel.SUSPICIOUS
        risk = "MEDIUM"
        explanations = ["Some anomalous pixels found, requires manual review"]
    else:
        verdict = VerdictLevel.REAL
        risk = "LOW"
        explanations = ["Image appears authentic — no significant manipulation detected"]
        
    result = ScanResult(
        scan_id=str(uuid.uuid4()),
        user_id=user_id,
        media_type=MediaType.IMAGE,
        verdict=verdict,
        confidence=round(max(fake_prob, real_prob) * 100, 2),
        fake_probability=round(fake_prob * 100, 2),
        real_probability=round(real_prob * 100, 2),
        risk_level=risk,
        explanations=explanations,
        heatmap_base64=None,
        metadata={"info": "Mocked for Free Tier"},
        timestamp=datetime.utcnow().isoformat()
    )
    
    return result.dict()
