from fastapi import FastAPI, HTTPException, File, UploadFile
import time
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
def get_homepage():
    return FileResponse("index.html", media_type="text/html")


@app.get("/style.css")
def get_style():
    return FileResponse("style.css", media_type="text/css")


@app.get("/script.js")
def get_script():
    return FileResponse("script.js", media_type="application/javascript")


@app.post("/generate-voice")
def generate_voice(payload: TextPayload):

    murf_url = "https://api.murf.ai/v1/speech/generate"

    headers = {
        "api-key": MURF_API_KEY,
        "Content-Type": "application/json"
    }

    body = {
        "text": payload.text,
        "voiceId": "en-US-ken"
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


UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.post("/upload")
def upload_audio(file: UploadFile = File(...)):
    allowed_types = ["audio/mp3", "audio/webm", "audio/wav", "audio/ogg"]

    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid file type")

    

    ext = file.content_type.split("/")[1]
    print
    filename = f"{int(time.time())}.{ext}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    with open(filepath, "wb") as buffer:
        buffer.write(file.file.read())

    return {
        "filename": filename,
        "fileSize": os.path.getsize(filepath),
        "fileType": file.content_type,
        "message": "File uploaded successfully"
    }
