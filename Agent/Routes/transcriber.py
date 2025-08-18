# transcriber.py
import os
import assemblyai as aai
from assemblyai.streaming.v3 import (
    StreamingClient, StreamingClientOptions,
    StreamingParameters, StreamingSessionParameters,
    StreamingEvents, BeginEvent, TurnEvent,
    TerminationEvent, StreamingError
)

aai.settings.api_key = "8e9c5b4b248a4528b0734e14f02942f4"


def on_begin(self, event: BeginEvent):
    print(f"Session started: {event.id}")


def on_turn(self, event: TurnEvent):
    print(f"{event.transcript} (end_of_turn={event.end_of_turn})")
    if event.end_of_turn and not event.turn_is_formatted:
        params = StreamingSessionParameters(format_turns=True)
        self.set_params(params)


def on_termination(self, event: TerminationEvent):
    print(f"Session terminated after {event.audio_duration_seconds} s")


def on_error(self, error: StreamingError):
    print("Error:", error)


class AssemblyAIStreamingTranscriber:
    def __init__(self, sample_rate=16000):
        self.client = StreamingClient(
            StreamingClientOptions(
                api_key=aai.settings.api_key, api_host="streaming.assemblyai.com")
        )
        self.client.on(StreamingEvents.Begin, on_begin)
        self.client.on(StreamingEvents.Turn, on_turn)
        self.client.on(StreamingEvents.Termination, on_termination)
        self.client.on(StreamingEvents.Error, on_error)

        self.client.connect(StreamingParameters(
            sample_rate=sample_rate, format_turns=False))

    def stream_audio(self, audio_chunk: bytes):
        self.client.stream(audio_chunk)

    def close(self):
        self.client.disconnect(terminate=True)
