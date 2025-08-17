import os
from fastapi import FastAPI, WebSocket
from fastapi.responses import FileResponse
from Routes import agent_chat
from utils.logging import setup_logger

setup_logger()

app = FastAPI()


# Make sure output folder exists
OUTPUT_DIR = os.path.join("Agent", "Output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Serve static files


@app.get("/")
def get_homepage():
    return FileResponse("index.html", media_type="text/html")


@app.get("/style.css")
def get_style():
    return FileResponse("style.css", media_type="text/css")


@app.get("/script.js")
def get_script():
    return FileResponse("script.js", media_type="application/javascript")

 


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("Client connected")

    file_path = os.path.join(OUTPUT_DIR, "recorded_audio.webm")

  
    if os.path.exists(file_path):
        os.remove(file_path)

    try:
        with open(file_path, "ab") as f:
            while True:
               
                data = await websocket.receive_bytes()
            
                f.write(data)
    except Exception as e:
        print(f"WebSocket connection closed: {e}")
    finally:
        print(f"Audio saved at {file_path}")


# Include API routes
app.include_router(agent_chat.router)
