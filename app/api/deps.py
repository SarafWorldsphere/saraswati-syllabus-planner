"""Who is calling. The role comes from the token. Class scope is not checked yet."""

from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from saraswati_tenant import current_school
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import KNOWN_ROLES, PLAN_WRITERS, canonical_role, decode_token
from app.db.session import get_db

bearer_scheme = HTTPBearer()

# Development stand-ins so Swagger can be clicked before login mints a real token.
# They exist only when APP_ENV is development. Each one is a role, not a class.
DEV_TOKENS = {
    "dev-admin": ("School Admin", "dev-admin"),
    "dev-headmaster": ("Headmaster", "dev-headmaster"),
    "dev-faculty": ("Faculty", "dev-faculty"),
}


@dataclass
class Caller:
    role: str
    user_id: str
    tenant_id: str


def _caller_from_token(token: str) -> Caller:
    school_id = current_school().tenant_id
    if settings.APP_ENV == "development" and token in DEV_TOKENS:
        role, user_id = DEV_TOKENS[token]
        return Caller(role=role, user_id=user_id, tenant_id=school_id)

    payload = decode_token(token)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    role = canonical_role(payload.get("role"))
    if role not in KNOWN_ROLES:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing a known role")

    token_school = payload.get("tenant_id")
    if token_school and token_school != school_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session belongs to a different school. Please sign in again.",
        )
    user_id = str(payload.get("sub") or "")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing sub")
    return Caller(role=role, user_id=user_id, tenant_id=school_id)


def get_caller(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> Caller:
    return _caller_from_token(credentials.credentials)


def require_plan_writer(caller: Caller = Depends(get_caller)) -> Caller:
    """Headmaster and Admin create the syllabus plan. Everyone else is refused."""
    if caller.role not in PLAN_WRITERS:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Admin or Headmaster can change the plan")
    return caller


def require_faculty(caller: Caller = Depends(get_caller)) -> Caller:
    if caller.role != "Faculty":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only a teacher can record teaching or generate today's lesson")
    return caller


def get_session(db: Session = Depends(get_db)) -> Session:
    return db
