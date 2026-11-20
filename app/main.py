"""Syllabus Planner API.

This process serves routes. The teacher, admin, and headmaster screens are
later work and will call it over HTTP. Swagger at /docs is the contract.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from saraswati_tenant import School, SchoolMiddleware, set_school_lookup

from app.api.v1.router import api_router
from app.core.config import settings

app = FastAPI(
    title="Saraswati Syllabus Planner",
    description=(
        "Platform calendars, the school syllabus plan, the teaching log, "
        "and coverage. A calendar has no board. A topic may continue into the next block. "
        "Headmaster and Admin write the plan. A lesson plan is generated only for the current topic. "
        "class_id is a query or body field, never a header. Class scope is not enforced yet."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


def _development_school(_host: str) -> School:
    # localhost has no row in platform.tenant_domains yet. Every host in
    # development is the sample school, so Swagger can be opened before login.
    return School(
        tenant_id=settings.DEV_TENANT_ID,
        slug="dev-school",
        status="active",
        isolation="rls",
        config={"schoolName": "Development School"},
    )


if settings.APP_ENV == "development":
    set_school_lookup(_development_school)

# Registered before CORS on purpose. add_middleware prepends, so the last one
# added is outermost and runs first. CORS must answer the browser preflight.
app.add_middleware(SchoolMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["health"], summary="Process is up")
def health_check():
    return {"status": "ok", "service": "syllabus-planner"}
