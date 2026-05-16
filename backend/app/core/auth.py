"""JWT Authentication utilities for Vedisa CRM."""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.config import settings
from app.core.database import get_session
from app.core.models import Usuario

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# bcrypt >= 4.1 lanza ValueError si la password supera 72 bytes; antes
# truncaba silenciosamente. Centralizamos el truncado para que el resto
# del codigo no tenga que preocuparse y para no cambiar el comportamiento
# observable (passwords largas seguian funcionando con sus primeros 72
# bytes en versiones anteriores).
BCRYPT_MAX_BYTES = 72


def _bcrypt_safe(password: str) -> str:
    if password is None:
        return ""
    encoded = password.encode("utf-8")
    if len(encoded) <= BCRYPT_MAX_BYTES:
        return password
    return encoded[:BCRYPT_MAX_BYTES].decode("utf-8", errors="ignore")


def verify_password(plain: str, hashed: str) -> bool:
    if not plain or not hashed:
        return False
    try:
        return pwd_context.verify(_bcrypt_safe(plain), hashed)
    except (ValueError, TypeError):
        # Hash corrupto, plataforma incompatible con bcrypt o input no
        # codificable. No tiene sentido devolver 500 al cliente: tratamos
        # como credencial invalida.
        return False


def hash_password(password: str) -> str:
    return pwd_context.hash(_bcrypt_safe(password))


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
