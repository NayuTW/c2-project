from fastapi import Header, HTTPException, status
from c2.server.config import get_operator_api_key

def require_operator(x_operator_key: str = Header(...)) -> None:
    """FastAPI dependency — rejects requests with the wrong operator key."""
    if x_operator_key != get_operator_api_key():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid operator key",
        )