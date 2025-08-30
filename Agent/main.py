import os
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from Routes.transcriber import AssemblyAIStreamingTranscriber
from utils.logging import setup_logger

setup_logger()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SESSION_KEYS = {}
OUTPUT_DIR = os.path.join("Agent", "Output")
os.makedirs(OUTPUT_DIR, exist_ok=True)


@app.get("/")
def get_homepage():
    return FileResponse("index.html", media_type="text/html")


@app.get("/style.css")
def get_style():
    return FileResponse("style.css", media_type="text/css")


@app.get("/script.js")
def get_script():
    return FileResponse("script.js", media_type="application/javascript")


@app.post("/set_keys/{session_id}")
async def set_keys(session_id: str, request: Request):
    try:
        body = await request.json()
        SESSION_KEYS[session_id] = {
            "gemini": body.get("gemini"),
            "murf": body.get("murf"),
            "stt": body.get("stt"),
        }
        return JSONResponse({"status": "ok", "message": "Keys saved"})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    session_id = websocket.query_params.get("session_id")
    if not session_id or session_id not in SESSION_KEYS:
        await websocket.send_json({"error": "API keys missing"})
        await websocket.close()
        return

    keys = SESSION_KEYS[session_id]
    loop = asyncio.get_running_loop()

    transcriber = AssemblyAIStreamingTranscriber(
        websocket, loop,
        stt_key=keys["stt"],
        gemini_key=keys["gemini"],
        murf_key=keys["murf"]
    )

    try:
        while True:
            data = await websocket.receive_bytes()
            transcriber.stream_audio(data)
    except WebSocketDisconnect:
        print(f"Client disconnected: {session_id}")
    finally:
        await transcriber.close()
