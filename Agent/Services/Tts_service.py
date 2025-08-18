import requests
import os
import logging

logger = logging.getLogger(__name__)
MURF_API_KEY = os.getenv(
    "MURF_API_KEY") or "ap2_3555f842-b5fe-495d-9a7c-f437b5905799"


def generate_speech(text: str, voice_id: str = "en-US-ken") -> str:
    response = requests.post(
        "https://api.murf.ai/v1/speech/generate",
        headers={
            "api-key": MURF_API_KEY,
            "Content-Type": "application/json"
        },
        json={
            "text": text,
            "voiceId": voice_id
        }
    )
    if response.status_code != 200:
        logger.error(f"Murf API failed: {response.text}")
        raise ValueError(f"Murf API failed: {response.text}")
    return response.json().get("audioFile")
