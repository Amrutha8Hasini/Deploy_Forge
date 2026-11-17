"""Login endpoints."""

from fastapi import APIRouter, Depends, HTTPException

from app.auth import check_credentials, create_token, require_user
from app.schemas import LoginRequest, LoginResponse

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest):
    if not check_credentials(body.username, body.password):
        raise HTTPException(status_code=401, detail="Wrong username or password")
    return LoginResponse(token=create_token(body.username), username=body.username)


@router.get("/me")
def who_am_i(username: str = Depends(require_user)):
    return {"username": username}
