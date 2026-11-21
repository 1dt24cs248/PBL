from contextlib import asynccontextmanager

from fastapi import FastAPI

from .routers import auth, energy, floorplan, optimizer, proposals, rooms, timetable


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield


app = FastAPI(title="PBL API", version="0.1.0", lifespan=lifespan)
app.include_router(auth.router)
app.include_router(rooms.router)
app.include_router(timetable.router)
app.include_router(floorplan.router)
app.include_router(energy.router)
app.include_router(optimizer.router)
app.include_router(proposals.router)


@app.get("/health")
def health():
    return {"status": "ok", "app": "PBL"}
