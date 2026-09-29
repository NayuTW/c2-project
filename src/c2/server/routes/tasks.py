from fastapi import APIRouter, HTTPException
from c2.server.models.api import(
    TaskResultRequest,
    TaskResultResponse,
    Task,
)
from c2.server.services import task_service


router = APIRouter(
    prefix="/api/v1",
    tags=["tasks"],
)


@router.post("/tasks", response_model=Task)
def create_task(request: CreateTaskRequest) -> Task:
    try:
        return task_service.create_task(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/tasks/{task_id}/result",
    response_model=TaskResultResponse,
)
def submit_task_result(
    task_id: str,
    request: TaskResultRequest,
) -> TaskResultResponse:
    try:
        task_service.submit_result(task_id, request)
        return TaskResultResponse(accepted=True)
    except PermissionError as exc:
        raise HTTPException(
            status_code=401,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc
