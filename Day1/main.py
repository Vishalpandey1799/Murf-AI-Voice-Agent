from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


app = FastAPI()


@app.get("/")
def read_index():
    return FileResponse("index.html")


@app.get("/script.js")
def read_script():
    return FileResponse("script.js")
