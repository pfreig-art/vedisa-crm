"""Resetea la password de un usuario por email.

Uso:
    python scripts/reset_admin_password.py admin@vedisa.com NuevaPassword123

Lee DATABASE_URL del entorno (o del .env via app.core.config) y aplica el
mismo hashing que el endpoint /auth/login (app.core.auth.hash_password,
incluido el truncado defensivo a 72 bytes).

NO se persiste la password en logs. Pensado para Windows / produccion
local cuando se ha perdido el password del admin tras un seed antiguo.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Permitir ejecutar desde backend/ o desde la raiz del repo.
HERE = Path(__file__).resolve().parent
BACKEND = HERE.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from sqlalchemy import select  # noqa: E402

from app.core.auth import hash_password  # noqa: E402
from app.core.database import AsyncSessionLocal  # noqa: E402
from app.core.models import Usuario  # noqa: E402


async def reset(email: str, new_password: str) -> int:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Usuario).where(Usuario.email == email)
        )
        user = result.scalar_one_or_none()
        if user is None:
            print(f"[ERROR] No existe usuario con email={email}")
            return 2
        user.hashed_password = hash_password(new_password)
        user.activo = True
        session.add(user)
        await session.commit()
        print(
            f"[OK] Password actualizada para {user.email} "
            f"(rol={user.rol}, activo={user.activo})"
        )
        return 0


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "Uso: python scripts/reset_admin_password.py "
            "<email> <nueva_password>"
        )
        return 1
    email = sys.argv[1].strip()
    new_password = sys.argv[2]
    if len(new_password) < 6:
        print("[ERROR] La password debe tener al menos 6 caracteres")
        return 1
    return asyncio.run(reset(email, new_password))


if __name__ == "__main__":
    raise SystemExit(main())
