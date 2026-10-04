import httpx


class C2Client:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.http = httpx.Client(timeout=10.0)

    def register(
        self,
        enrollment_token: str,
        agent_version: str,
        platform: str,
        architecture: str,
    ) -> dict:
        response = self.http.post(
            f"{self.base_url}/api/v1/agents/register",
            json={
                "enrollment_token": enrollment_token,
                "agent_version": agent_version,
                "platform": platform,
                "architecture": architecture,
            }
        )
        response.raise_for_status()
        return response.json()
    
    def poll(
        self,
        agent_id: str,
        session_token: str,
    ) -> dict:
        response = self.http.post(
            f"{self.base_url}/api/v1/agents/poll",
            json={
                "agent_id": agent_id,
                "session_token": session_token,
            }
        )
        response.raise_for_status()
        return response.json()

    def submit_result(
        self,
        agent_id: str,
        session_token: str,
        task_id: str,
        status: str,
        result: dict | None = None,
        error: str | None = None,
    ) -> dict:
        response = self.http.post(
            f"{self.base_url}/api/v1/tasks/{task_id}/result",
            json={
                "agent_id": agent_id,
                "task_id": task_id,
                "session_token": session_token,
                "status": status,
                "result": result,
                "error": error,
            },
        )
        response.raise_for_status()
        return response.json()