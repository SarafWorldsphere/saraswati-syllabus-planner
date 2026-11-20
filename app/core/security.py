"""Bearer tokens. The role on the token is decided at login; this module only reads it."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt

from app.core.config import settings

# Login uses these names. "Admin" is the same person as "School Admin".
# "Teacher" is the same person as "Faculty". Class scope is not on the token yet.
ROLE_ALIASES = {
    "Admin": "School Admin",
    "Teacher": "Faculty",
}

PLAN_WRITERS = {"School Admin", "Headmaster"}
FACULTY = {"Faculty"}
KNOWN_ROLES = PLAN_WRITERS | FACULTY


def canonical_role(role: str | None) -> str | None:
    if not role:
        return None
    cleaned = role.strip()
    return ROLE_ALIASES.get(cleaned, cleaned)


def create_access_token(role: str, user_id: str, tenant_id: str) -> str:
    """Mint a token this service can check. Login will do this later."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "role": canonical_role(role),
        "sub": user_id,
        "tenant_id": tenant_id,
        "exp": expire,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None
