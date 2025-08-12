import google.generativeai as genai
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


chat_store = {}
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
                 


def getReponsefromGemini(conversation_history: list) -> str:
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")

        
        messages = []
        for msg in conversation_history:
            role = "user" if msg["role"] == "user" else "model"
            messages.append({"role": role, "parts": [msg["text"]]})

        response = model.generate_content(messages)
        return response.text.strip()
    except Exception as e:
        print(f"Gemini error: {e}")
        return "Sorry, I couldn't process that."


@app.post("/agent/chat/{session_id}")
async def chat_with_history(session_id: str, file: UploadFile = File(...)):
    allowed_types = ["audio/mp3", "audio/webm", "audio/wav", "audio/ogg"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid file type")

    try:
        # 1. Transcribe audio
        audio_bytes = await file.read()
        transcriber = aai.Transcriber()
        transcript = transcriber.transcribe(audio_bytes)

        if transcript.status == "error":
            raise HTTPException(
                status_code=500, detail=f"AssemblyAI error: {transcript.error}")

        user_message = {"role": "user", "text": transcript.text}

        # 2. Manage conversation history
        if session_id not in chat_store:
            chat_store[session_id] = []

        chat_store[session_id].append(user_message)

        # 3. Get AI response with full context
        ai_reply = getReponsefromGemini(chat_store[session_id])
        assistant_message = {"role": "assistant", "text": ai_reply}
        chat_store[session_id].append(assistant_message)

        # 4. Generate speech
        murf_response = requests.post(
            "https://api.murf.ai/v1/speech/generate",
            headers={
                "api-key": MURF_API_KEY,
                "Content-Type": "application/json"
            },
            json={
                "text": ai_reply,
                "voiceId": "en-US-ken"
            }
        )

        if murf_response.status_code != 200:
            raise HTTPException(
                status_code=500, detail=f"Murf API failed: {murf_response.text}")

        return {
            "audio_url": murf_response.json().get("audioFile"),
            "text": ai_reply,
            "history": chat_store[session_id]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
