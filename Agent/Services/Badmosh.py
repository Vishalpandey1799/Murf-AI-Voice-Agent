import asyncio
import websockets
import json
import os

MURF_API_KEY = os.getenv(
    "MURF_API_KEY") or "ap2_3555f842-b5fe-495d-9a7c-f437b5905799"
MURF_WS_URL = "wss://api.murf.ai/v1/speech/stream-input"


class MurfStreamer:
    def __init__(self, voice_id="en-US-ken", context_id="static-context-123"):
        self.voice_id = voice_id
        self.context_id = context_id   

    async def stream_tts(self, text: str):
        """Send text to Murf via WebSocket and print base64 audio"""
        async with websockets.connect(
            f"{MURF_WS_URL}?api-key={MURF_API_KEY}&sample_rate=44100&channel_type=MONO&format=WAV&context_id={self.context_id}"
        ) as ws:
         
            voice_config_msg = {
                "voice_config": {
                    "voiceId": self.voice_id,
                    "style": "Conversational",
                    "rate": 0,
                    "pitch": 0,
                    "variation": 1
                }
            }
            await ws.send(json.dumps(voice_config_msg))

            # Send text
            text_msg = {
                "text": text,
                "end": True
            }
            await ws.send(json.dumps(text_msg))

         
            while True:
                response = await ws.recv()
                data = json.loads(response)
                if "audio" in data:
                    # print prefix for LinkedIn
                    print("🎶 Murf Audio (base64):", data["audio"][:60], "...")
                if data.get("final"):
                    break
