"""JWT Authentication utilities for Vedisa CRM.

Usamos bcrypt directamente (no passlib): passlib 1.7.4 es incompatible con
bcrypt >= 4.1 porque sus checks internos (detect_wrap_bug) generan una
password sintetica > 72 bytes al cargar el backend, lo que dispara
ValueError en bcrypt moderno. Como solo necesitamos hash + verify, llamar
a bcrypt directo es mas simple y robusto.
"""
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.config import settings
from app.core.database import get_session
from app.core.models import Usuario

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# bcrypt >= 4.1 lanza ValueError si la password supera 72 bytes; antes
# truncaba silenciosamente. Centralizamos el truncado para mantener el
# comportamiento observable: passwords largas siguen funcionando usando
# sus primeros 72 bytes.
BCRYPT_MAX_BYTES = 72


def _bcrypt_safe(password: str) -> str:
    """Devuelve la password recortada a 72 bytes UTF-8 (firma str->str para
    retrocompatibilidad con tests e imports existentes)."""
    if password is None:
        return ""
    encoded = password.encode("utf-8")
    if len(encoded) <= BCRYPT_MAX_BYTES:
        return password
    return encoded[:BCRYPT_MAX_BYTES].decode("utf-8", errors="ignore")


def _bcrypt_safe_bytes(password: str) -> bytes:
    """Variante interna que devuelve bytes listos para bcrypt."""
    if not password:
        return b""
    return password.encode("utf-8")[:BCRYPT_MAX_BYTES]


def verify_password(plain: str, hashed: str) -> bool:
    if not plain or not hashed:
        return False
    try:
        return bcrypt.checkpw(_bcrypt_safe_bytes(plain), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        # Hash corrupto, plataforma incompatible o input no codificable.
        # No tiene sentido devolver 500 al cliente: tratamos como
        # credencial invalida.
        return False


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_bcrypt_safe_bytes(password), bcrypt.gensalt()).decode("utf-8")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_session),
) -> Usuario:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token invalido o expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(Usuario).where(Usuario.email == email))
    user = result.scalar_one_or_none()
    if user is None or not user.activo:
        raise credentials_exception
    return user


def require_role(*roles: str):
    """Dependency factory: require user to have one of the given roles."""
    async def checker(current_user: Usuario = Depends(get_current_user)) -> Usuario:
        if current_user.rol not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Rol requerido: {', '.join(roles)}",
            )
        return current_user
    return checker
