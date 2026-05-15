"""Auth endpoints: login, me, register (admin only)."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_session
from app.core.models import Usuario
from app.core.auth import (
    verify_password, hash_password,
    create_access_token, get_current_user, require_role,
)

router = APIRouter()


class Token(BaseModel):
    access_token: str
    token_type: str
    rol: str
    nombre: str
    email: str


class UserOut(BaseModel):
    id: str
    email: str
    nombre: str
    rol: str
    activo: bool

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    email: str
    nombre: str
    password: str
    rol: str = "comercial"


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_session),
):
    result = await db.execute(select(Usuario).where(Usuario.email == form_data.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contrasena incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.activo:
        raise HTTPException(status_code=403, detail="Usuario desactivado")
    token = create_access_token({"sub": user.email, "rol": user.rol})
    return Token(
        access_token=token,
        token_type="bearer",
        rol=user.rol,
        nombre=user.nombre,
        email=user.email,
    )


@router.get("/me", response_model=UserOut)
async def me(current_user: Usuario = Depends(get_current_user)):
    return current_user


@router.post("/register", response_model=UserOut, status_code=201)
async def register(
    body: UserCreate,
    db: AsyncSession = Depends(get_session),
    _: Usuario = Depends(require_role("admin")),
):
    result = await db.execute(select(Usuario).where(Usuario.email == body.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email ya registrado")
    user = Usuario(
        email=body.email,
        nombre=body.nombre,
        hashed_password=hash_password(body.password),
        rol=body.rol,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
