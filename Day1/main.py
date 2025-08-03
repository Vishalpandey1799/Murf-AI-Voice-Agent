from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import requests
import os
from dotenv import load_dotenv

load_dotenv()

MURF_API_KEY = os.getenv("MURF_API_KEY")

app = FastAPI()


class TextPayload(BaseModel):
    text: str


@app.get("/")
def read_index():
    return FileResponse("index.html")


@app.post("/generate-voice")
def generate_voice(payload: TextPayload):
    murf_url = "https://api.murf.ai/v1/speech/generate"

    headers = {
        "api-key": MURF_API_KEY,
        "Content-Type": "application/json"
    }

    body = {
        "text": payload.text,
        "voiceId": "en-US-terrell"
    }

    response = requests.post(murf_url, headers=headers, json=body)
    print(response.json())

    if response.status_code == 200:
        audio_url = response.json().get("audioFile")
        return {"audio_url": audio_url}
    else:
        print("Error:", response.text)
        raise HTTPException(
            status_code=500, detail=f"Murf API failed: {response.text}")
