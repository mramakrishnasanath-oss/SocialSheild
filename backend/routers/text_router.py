"""
Text Scam Detection Router
Uses Regex patterns and HuggingFace API (optional) for phishing/fraud intent classification
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import re
import uuid
import logging
from datetime import datetime
import os
import httpx

from utils.auth import get_current_user
from models.scan_result import ScanResult, MediaType, VerdictLevel

router = APIRouter()
logger = logging.getLogger(__name__)

HF_API_KEY = os.getenv("HUGGINGFACE_API_KEY", "")

# Regex patterns for rule-based scam detection
PHISHING_PATTERNS = [
    (r'(?i)(click here|click now|click immediately)', 0.3, "Urgency-triggering language detected"),
    (r'(?i)(verify your account|confirm your identity|update your information)', 0.35, "Account verification phishing attempt"),
    (r'(?i)(you have won|congratulations.*prize|claim your reward)', 0.4, "Lottery/prize scam pattern"),
    (r'(?i)(act now|limited time|expires in|urgent)', 0.25, "False urgency tactics"),
    (r'(?i)(send.*bitcoin|transfer.*crypto|wire transfer)', 0.45, "Cryptocurrency/wire transfer scam"),
    (r'(?i)(OTP|one.time.pass|verification code)', 0.3, "OTP phishing attempt"),
    (r'(?i)(your account.*suspended|locked|blocked)', 0.35, "Account threat scam pattern"),
    (r'(?i)(social security|SSN|tax.refund)', 0.4, "Government impersonation scam"),
    (r'(?i)(password|login credentials|username)', 0.3, "Credential harvesting attempt"),
    (r'(?i)(free.*gift|free.*money|₹\d+.*free)', 0.35, "Free money scam pattern"),
]

class TextScanRequest(BaseModel):
    text: str


async def get_text_ml_score(text: str) -> float:
    """Uses Hugging Face Inference API to get ML spam score if key is available"""
    if not HF_API_KEY:
        return 0.5
        
    API_URL = "https://api-inference.huggingface.co/models/mrm8488/bert-tiny-finetuned-sms-spam-detection"
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(API_URL, headers=headers, json={"inputs": text[:512]})
            if response.status_code == 200:
                results = response.json()
                if isinstance(results, list) and len(results) > 0:
                    result_list = results[0] if isinstance(results[0], list) else results
                    for item in result_list:
                        label = str(item.get("label", "")).upper()
                        score = item.get("score", 0.5)
                        if 'SPAM' in label or 'FAKE' in label or 'PHISH' in label:
                            return score
                        if 'LABEL_1' in label: # spam class for some models
                            return score
            return 0.5
    except Exception as e:
        logger.error(f"HF Text API error: {e}")
        return 0.5


@router.post("/text")
async def scan_text(
    request: TextScanRequest,
    user_id: str = Depends(get_current_user)
):
    """Scan text for scam, phishing, or fraud intent"""
    text = request.text.strip()
    
    if not text:
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    
    if len(text) > 10000:
        raise HTTPException(status_code=400, detail="Text too long (max 10000 chars)")
    
    # Try calling HF API
    ml_fake_prob = await get_text_ml_score(text)
    
    # Rule-based pattern matching
    pattern_score = 0.0
    pattern_reasons = []
    for pattern, weight, reason in PHISHING_PATTERNS:
        if re.search(pattern, text):
            pattern_score += weight
            pattern_reasons.append(reason)
    
    pattern_score = min(pattern_score, 0.9)
    
    # Combine ML + rule-based
    final_score = (ml_fake_prob * 0.4 + pattern_score * 0.6)
    final_score = min(final_score, 1.0)
    
    if final_score >= 0.65:
        verdict = VerdictLevel.FAKE
        risk = "HIGH"
    elif final_score >= 0.35:
        verdict = VerdictLevel.SUSPICIOUS
        risk = "MEDIUM"
    else:
        verdict = VerdictLevel.REAL
        risk = "LOW"
    
    explanations = pattern_reasons.copy()
    if ml_fake_prob > 0.6:
        explanations.append("Cloud NLP model detected high fraud intent probability")
    if not explanations:
        explanations.append("Text appears legitimate — no scam patterns detected")
    
    scan_id = str(uuid.uuid4())
    result = ScanResult(
        scan_id=scan_id,
        user_id=user_id,
        media_type=MediaType.TEXT,
        verdict=verdict,
        confidence=round(max(final_score, 1 - final_score) * 100, 2),
        fake_probability=round(final_score * 100, 2),
        real_probability=round((1 - final_score) * 100, 2),
        risk_level=risk,
        explanations=explanations,
        metadata={
            "text_length": len(text),
            "ml_score": round(ml_fake_prob * 100, 2),
            "pattern_score": round(pattern_score * 100, 2),
            "patterns_matched": len(pattern_reasons)
        },
        timestamp=datetime.utcnow().isoformat()
    )
    
    return result.dict()
