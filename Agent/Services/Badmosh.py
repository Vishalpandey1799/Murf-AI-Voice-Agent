import asyncio
import websockets
import json

MURF_WS_URL = "wss://api.murf.ai/v1/speech/stream-input"


class MurfStreamer:
    def __init__(self, api_key: str, voice_id="en-US-ken", context_id="static-context-123"):
        self.api_key = api_key
        self.voice_id = voice_id
        self.context_id = context_id
        self.ws = None

    async def connect(self):
        if not self.ws:
            print("🔌 Connecting to Murf WebSocket...")
            self.ws = await websockets.connect(
                f"{MURF_WS_URL}?api-key={self.api_key}&sample_rate=44100&channel_type=MONO&format=WAV&context_id={self.context_id}"
            )
            voice_config_msg = {
                "voice_config": {
                    "voiceId": self.voice_id,
                    "rate": 0,
                    "pitch": 0,
                    "variation": 1,
                    "style": "Conversational",
                }
            }
            await self.ws.send(json.dumps(voice_config_msg))
            print("✅ Voice config sent to Murf")

    async def stream_tts(self, text: str, websocket, final=False):
        await self.connect()

        text_msg = {"text": text, "end": final}
        await self.ws.send(json.dumps(text_msg))

        while True:
            response = await self.ws.recv()
            data = json.loads(response)

            if "audio" in data:
                await websocket.send_json({"type": "audio_chunk", "audio": data["audio"]})

            if data.get("final"):
                break
