import os
import httpx
import logging

logger = logging.getLogger(__name__)

HF_API_KEY = os.getenv("HUGGINGFACE_API_KEY", "")

async def scan_image_with_hf(image_bytes: bytes) -> dict:
    """
    Calls the Hugging Face Inference API for deepfake detection.
    Returns a dictionary with 'fake_prob' and 'real_prob'.
    If the API fails, returns None so the router can fallback to heuristic.
    """
    if not HF_API_KEY:
        logger.warning("No HuggingFace API key found.")
        return None

    # Using a public deepfake detection model on Hugging Face
    API_URL = "https://api-inference.huggingface.co/models/dvilasuero/deepfake-detection"
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(API_URL, headers=headers, content=image_bytes)
            
            if response.status_code == 200:
                results = response.json()
                # Results is usually a list of dicts: [{'label': 'fake', 'score': 0.9}, {'label': 'real', 'score': 0.1}]
                if isinstance(results, list) and len(results) > 0:
                    fake_prob = 0.5
                    real_prob = 0.5
                    for item in results:
                        label = item.get("label", "").lower()
                        score = item.get("score", 0.5)
                        if "fake" in label:
                            fake_prob = score
                        elif "real" in label:
                            real_prob = score
                    
                    return {"fake_prob": fake_prob, "real_prob": real_prob}
                
            logger.warning(f"HF API returned {response.status_code}: {response.text}")
            return None
    except Exception as e:
        logger.error(f"Error calling HuggingFace API: {e}")
        return None
