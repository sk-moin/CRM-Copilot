from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.auth_service import AuthService
from app.services.exceptions import InvalidCredentialsError
from app.api.schemas.auth import LoginRequest, LoginResponse
from app.api.schemas.auth import RegisterRequest

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    service = AuthService(db)

    try:
        tokens = await service.login(
            email=request.email,
            password=request.password,
        )
        return LoginResponse(**tokens)

    except InvalidCredentialsError:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )


@router.post("/register")
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    service = AuthService(db)

    return await service.register(
        email=request.email,
        password=request.password,
        subdomain=request.subdomain,
        org_name=request.org_name,
    )