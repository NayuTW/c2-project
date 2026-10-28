from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from c2.server.db import init_db
from c2.server.routes import agents, tasks


@asynccontextmanager
# Here we will run the db on server start
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    init_db()
    yield


app = FastAPI(
    title="Lightweight C2 Server",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(agents.router)
app.include_router(tasks.router)

@app.get("/")
def redirect_to_docs():
    return RedirectResponse("/docs")

@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status":"ok"}
