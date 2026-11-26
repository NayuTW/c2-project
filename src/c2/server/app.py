import asyncio
import contextlib
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from c2.server.db import init_db
from c2.server.routes import agents, operator, tasks
from c2.server.services.agent_service import check_agent_timeouts


async def _timeout_loop() -> None:
    """Periodically mark stale agents as timed_out."""
    while True:
        await asyncio.sleep(30)
        check_agent_timeouts()


@asynccontextmanager
# Here we will run the db on server start
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    init_db()
    task = asyncio.create_task(_timeout_loop())
    try:
        yield
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


app = FastAPI(
    title="Lightweight C2 Server",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(agents.router)
app.include_router(tasks.router)
app.include_router(operator.router)

@app.get("/")
def redirect_to_docs():
    return RedirectResponse("/docs")

@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status":"ok"}
