from fastapi import FastAPI, HTTPException, File, UploadFile
import time
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import requests
import os
from dotenv import load_dotenv
import assemblyai as aai

load_dotenv()

MURF_API_KEY = os.getenv("MURF_API_KEY")
aai.settings.api_key = os.getenv(
    "ASSEMBLYAI_API_KEY")

app = FastAPI()


class TextPayload(BaseModel):
    text: str


class TranscribeRequest(BaseModel):
    filename: str


@app.get("/")
def get_homepage():
    return FileResponse("index.html", media_type="text/html")


@app.get("/style.css")
def get_style():
    return FileResponse("style.css", media_type="text/css")


@app.get("/script.js")
def get_script():
    return FileResponse("script.js", media_type="application/javascript")


@app.post("/tts/echo")
async def tts_echo(file: UploadFile = File(...)):
    allowed_types = ["audio/mp3", "audio/webm", "audio/wav", "audio/ogg"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid file type")

    try:
        # Read audio in memory
        audio_bytes = await file.read()

        # Transcribe with AssemblyAI directly from bytes
        transcriber = aai.Transcriber()
        transcript = transcriber.transcribe(audio_bytes)

        print(transcript)
        if transcript.status == "error":
            raise HTTPException(
                status_code=500, detail=f"AssemblyAI error: {transcript.error}")

        text = transcript.text

        # Send transcript to Murf API
        murf_url = "https://api.murf.ai/v1/speech/generate"
        headers = {
            "api-key": MURF_API_KEY,
            "Content-Type": "application/json"
        }
        body = {
            "text": text,
            "voiceId": "en-US-ken"
        }

        murf_response = requests.post(murf_url, headers=headers, json=body)

        if murf_response.status_code != 200:
            raise HTTPException(
                status_code=500, detail=f"Murf API failed: {murf_response.text}")

        audio_url = murf_response.json().get("audioFile")
        return {"audio_url": audio_url}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
