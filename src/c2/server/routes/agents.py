from fastapi import APIRouter, HTTPException, status
from c2.server.models.api import (
    PollRequest,
    PollResponse,
    RegisterRequest,
    RegisterResponse,
)
from c2.server.services import agent_service


router = APIRouter(
    prefix="/api/v1/agents",
    tags=["agents"],
)


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)

def register_agent(request: RegisterRequest) -> RegisterResponse:
    try:
        return agent_service.register_agent(request)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc


@router.post(
    "/poll",
    response_model=PollResponse,
)

def poll_for_tasks(request: PollRequest) -> PollResponse:
    try:
        return agent_service.poll_for_tasks(request)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc),
        ) from exc
