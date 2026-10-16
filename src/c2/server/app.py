from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from c2.server.routes import agents, tasks

app = FastAPI(
    title="Lightweight C2 Server",
    version="0.1.0",
)

app.include_router(agents.router)
app.include_router(tasks.router)

@app.get("/")
def redirect_to_docs():
    return RedirectResponse("/docs")

@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status":"ok"}
