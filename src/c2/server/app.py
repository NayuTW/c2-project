from fastapi import FastAPI
from c2.server.routes import agents, tasks

app = FastAPI(
    title="Lightweight C2 Server",
    version="0.1.0",
)

app.include_router(agents.router)
app.include_router(tasks.router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status":"ok"}
