"""Every route under /api/v1. Swagger at /docs is the contract."""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    academic_year,
    alerts,
    assessments,
    boards,
    calendars,
    coverage,
    lesson_plans,
    syllabus_items,
    syllabus_plan,
    teaching_log,
)

api_router = APIRouter()
api_router.include_router(boards.router)
api_router.include_router(calendars.router)
api_router.include_router(syllabus_items.router)
api_router.include_router(assessments.router)
api_router.include_router(academic_year.router)
api_router.include_router(syllabus_plan.router)
api_router.include_router(teaching_log.router)
api_router.include_router(coverage.router)
api_router.include_router(alerts.router)
api_router.include_router(lesson_plans.router)
