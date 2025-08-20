import google.generativeai as genai
import os
import asyncio
import assemblyai as aai

from google import generativeai

from assemblyai.streaming.v3 import (
    StreamingClient, StreamingClientOptions,
    StreamingParameters, StreamingSessionParameters,
    StreamingEvents, BeginEvent, TurnEvent,
    TerminationEvent, StreamingError
)
from fastapi import WebSocket

aai.settings.api_key = ""


# genai.configure(api_key=)

gemini_model = genai.GenerativeModel("gemini-1.5-flash")


class AssemblyAIStreamingTranscriber:
    def __init__(self, websocket: WebSocket, loop, sample_rate=16000):
        self.websocket = websocket
        self.loop = loop  # main FastAPI event loop

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
            StreamingParameters(sample_rate=sample_rate, format_turns=False)
        )

    def on_begin(self, client, event: BeginEvent):
        print(f"🎤 Session started: {event.id}")

    def on_turn(self, client, event: TurnEvent):
        print(f"{event.transcript} (end_of_turn={event.end_of_turn})")

        if event.end_of_turn and event.transcript.strip():
            try:

                asyncio.run_coroutine_threadsafe(
                    self.websocket.send_json({
                        "type": "transcript",
                        "text": event.transcript
                    }),
                    self.loop
                )

                self.start_ai_response(event.transcript)

            except Exception as e:
                print("⚠️ Failed in on_turn:", e)

            if not event.turn_is_formatted:
                client.set_params(
                    StreamingSessionParameters(format_turns=True)
                )

    def start_ai_response(self, user_text: str):
        """Stream AI response from Gemini and send to WebSocket"""
        try:
            response = gemini_model.generate_content(
                user_text,
                stream=True
            )

            for chunk in response:
                if chunk.text:
                    print(chunk.text)

                    asyncio.run_coroutine_threadsafe(
                        self.websocket.send_json({
                            "type": "ai_response",
                            "text": chunk.text
                        }),
                        self.loop
                    )
        except Exception as e:
            print("⚠️ Gemini streaming error:", e)

    def on_termination(self, client, event: TerminationEvent):
        print(f"🛑 Session terminated after {event.audio_duration_seconds} s")

    def on_error(self, client, error: StreamingError):
        print("❌ Error:", error)

    def stream_audio(self, audio_chunk: bytes):
        self.client.stream(audio_chunk)

    def close(self):
        self.client.disconnect(terminate=True)
