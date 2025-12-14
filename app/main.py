from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.optics.schema import Scene
from app.optics.simulate import simulate_scene


app = FastAPI(title="Light-sim 2D")


@app.get("/")
def index():
    return FileResponse("frontend/index.html")


app.mount("/static", StaticFiles(directory="frontend"), name="static")


@app.post("/api/simulate")
def api_simulate(scene: Scene):
    return simulate_scene(scene)

