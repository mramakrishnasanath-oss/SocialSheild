import os
import httpx
import logging
import asyncio

logger = logging.getLogger(__name__)

HF_API_KEY = os.getenv("HUGGINGFACE_API_KEY", "")

# Ensemble of free models to catch different types of AI fakes
# 1. Generalized deepfake detector
# 2. Specialized facial deepfake detector
# 3. AI-generated art/image detector
MODELS = [
    "https://api-inference.huggingface.co/models/prithivMLmods/Deep-Fake-Detector-Model",
    "https://api-inference.huggingface.co/models/dvilasuero/deepfake-detection",
    "https://api-inference.huggingface.co/models/umm-maybe/AI-image-detector"
]

async def call_hf_model(client: httpx.AsyncClient, url: str, headers: dict, image_bytes: bytes):
    try:
        response = await client.post(url, headers=headers, content=image_bytes)
        if response.status_code == 200:
            results = response.json()
            
            # Handle nested lists if the API returns [[{...}]]
            if isinstance(results, list) and len(results) > 0 and isinstance(results[0], list):
                results = results[0]

            if isinstance(results, list) and len(results) > 0:
                fake_prob = None
                real_prob = None

                for item in results:
                    label = str(item.get("label", "")).strip().lower()
                    score = float(item.get("score", 0.5))

                    # Map various model labels to our binary Fake/Real
                    if label in ("fake", "ai-generated", "deepfake", "manipulated", "artificial"):
                        fake_prob = score
                    elif label in ("real", "authentic", "genuine", "natural", "human"):
                        real_prob = score
                    elif label == "label_1": # dvilasuero fake label
                        fake_prob = score
                    elif label == "label_0": # dvilasuero real label
                        real_prob = score

                if fake_prob is not None:
                    return fake_prob
                elif real_prob is not None:
                    return 1.0 - real_prob
    except Exception as e:
        logger.error(f"Error calling {url}: {e}")
        
    return None

async def scan_image_with_hf(image_bytes: bytes) -> dict:
    """
    Calls an ensemble of Hugging Face Inference APIs for better deepfake detection.
    Returns a dict with 'fake_prob' and 'real_prob'.
    """
    if not HF_API_KEY:
        logger.warning("No HuggingFace API key found.")
        return None

    headers = {"Authorization": f"Bearer {HF_API_KEY}"}

    async with httpx.AsyncClient(timeout=25.0) as client:
        # Request all 3 models at the EXACT same time (Concurrency)
        tasks = [call_hf_model(client, url, headers, image_bytes) for url in MODELS]
        results = await asyncio.gather(*tasks)
        
        valid_scores = [score for score in results if score is not None]
        
        if not valid_scores:
            return None
            
        # ENSEMBLE LOGIC: Take the HIGHEST fake probability. 
        # If any single specialized model detects a fake, we flag it. 
        # This vastly improves detection across different AI generators.
        final_fake_prob = max(valid_scores)
        final_real_prob = 1.0 - final_fake_prob
        
        return {"fake_prob": final_fake_prob, "real_prob": final_real_prob}
