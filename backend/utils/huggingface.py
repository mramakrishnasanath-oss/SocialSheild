import os
import httpx
import logging

logger = logging.getLogger(__name__)

HF_API_KEY = os.getenv("HUGGINGFACE_API_KEY", "")

async def scan_image_with_hf(image_bytes: bytes) -> dict:
    """
    Calls the Hugging Face Inference API for deepfake detection.
    Model: dvilasuero/deepfake-detection
      - LABEL_0 = Real (authentic)
      - LABEL_1 = Fake (AI-generated / deepfake)
      - OR labels may be named 'Fake' / 'Real' directly.
    Returns a dict with 'fake_prob' and 'real_prob', or None on failure.
    """
    if not HF_API_KEY:
        logger.warning("No HuggingFace API key found.")
        return None

    API_URL = "https://api-inference.huggingface.co/models/dvilasuero/deepfake-detection"
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(API_URL, headers=headers, content=image_bytes)

            if response.status_code == 200:
                results = response.json()
                logger.info(f"HF API raw response: {results}")

                # The API can return either:
                #   [{'label': 'Fake', 'score': 0.9}, {'label': 'Real', 'score': 0.1}]
                # OR numeric labels:
                #   [{'label': 'LABEL_0', 'score': 0.9}, {'label': 'LABEL_1', 'score': 0.1}]
                # For dvilasuero/deepfake-detection: LABEL_0 = Real, LABEL_1 = Fake

                if isinstance(results, list) and len(results) > 0:
                    fake_prob = None
                    real_prob = None

                    for item in results:
                        label = str(item.get("label", "")).strip().lower()
                        score = float(item.get("score", 0.5))

                        # Named labels
                        if label in ("fake", "ai-generated", "deepfake", "manipulated"):
                            fake_prob = score
                        elif label in ("real", "authentic", "genuine", "natural"):
                            real_prob = score
                        # Numeric labels (LABEL_0 = Real, LABEL_1 = Fake for this model)
                        elif label == "label_1":
                            fake_prob = score
                        elif label == "label_0":
                            real_prob = score

                    if fake_prob is not None and real_prob is not None:
                        return {"fake_prob": fake_prob, "real_prob": real_prob}
                    elif fake_prob is not None:
                        return {"fake_prob": fake_prob, "real_prob": 1.0 - fake_prob}
                    elif real_prob is not None:
                        return {"fake_prob": 1.0 - real_prob, "real_prob": real_prob}

            logger.warning(f"HF API returned {response.status_code}: {response.text}")
            return None

    except Exception as e:
        logger.error(f"Error calling HuggingFace API: {e}")
        return None
