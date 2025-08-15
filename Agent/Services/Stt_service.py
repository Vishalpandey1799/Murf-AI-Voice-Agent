import assemblyai as aai
import os
import logging

logger = logging.getLogger(__name__)
aai.settings.api_key = os.getenv("ASSEMBLY_API_KEY") or "8e9c5b4b248a4528b0734e14f02942f4"


def transcribe_audio(audio_bytes: bytes) -> str:
    try:
        transcriber = aai.Transcriber()
        transcript = transcriber.transcribe(audio_bytes)
        if transcript.status == "error":
            logger.error(f"AssemblyAI error: {transcript.error}")
            raise ValueError(f"AssemblyAI error: {transcript.error}")
        return transcript.text
    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        raise
