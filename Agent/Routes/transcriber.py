import asyncio
import assemblyai as aai
from Services.Badmosh import MurfStreamer
from Services.Gemini_service import AIAgent

from assemblyai.streaming.v3 import (
    StreamingClient, StreamingClientOptions,
    StreamingParameters, StreamingSessionParameters,
    StreamingEvents, BeginEvent, TurnEvent,
    TerminationEvent, StreamingError
)
from fastapi import WebSocket

aai.settings.api_key = ""


class AssemblyAIStreamingTranscriber:
    def __init__(self, websocket: WebSocket, loop, sample_rate=16000):
        self.murf = MurfStreamer()
        self.websocket = websocket
        self.loop = loop

        # init AI agent with Murf + WebSocket
        self.ai_agent = AIAgent(self.websocket, self.loop, self.murf)

        self.client = StreamingClient(
            StreamingClientOptions(
                api_key=aai.settings.api_key,
                api_host="streaming.assemblyai.com"
            )
        )

        self.client.on(StreamingEvents.Begin, self.on_begin)
        self.client.on(StreamingEvents.Turn, self.on_turn)
        self.client.on(StreamingEvents.Termination, self.on_termination)
        self.client.on(StreamingEvents.Error, self.on_error)

        self.client.connect(
            StreamingParameters(sample_rate=sample_rate, format_turns=True)
        )

    def on_begin(self, client, event: BeginEvent):
        print(f"🎤 Session started: {event.id}")

    def on_turn(self, client, event: TurnEvent):
        print(
            f"{event.transcript} (end_of_turn={event.end_of_turn}, formatted={event.turn_is_formatted})")

        if not event.end_of_turn:
            return

        if not event.turn_is_formatted:
            client.set_params(StreamingSessionParameters(format_turns=True))
            return

        text = (event.transcript or "").strip()
        if not text:
            return

        try:
            asyncio.run_coroutine_threadsafe(
                self.websocket.send_json({"type": "transcript", "text": text}),
                self.loop
            )

            # 🔥 Send user text to AI agent
            self.ai_agent.stream_ai_response(text)

        except Exception as e:
            print("⚠️ Failed in on_turn:", e)

    def on_termination(self, client, event: TerminationEvent):
        print(f"🛑 Session terminated after {event.audio_duration_seconds} s")

    def on_error(self, client, error: StreamingError):
        print("❌ Error:", error)

    def stream_audio(self, audio_chunk: bytes):
        self.client.stream(audio_chunk)

    def close(self):
        self.client.disconnect(terminate=True)
