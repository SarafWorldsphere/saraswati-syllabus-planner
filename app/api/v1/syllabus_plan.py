from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
from datetime import date

# Adjust these imports based on your project's structure
from app.db.session import get_db
from app.api.deps import get_current_admin # Or whatever your auth dependency is named
from app.models.syllabus_plan import SyllabusPlan
from app.models.chapter import Chapter # Assuming a Chapter model exists

router = APIRouter()

# --- Pydantic Schemas ---
class GenerateResponse(BaseModel):
    created: int
    skipped: int

class PlanUpdate(BaseModel):
    chapter_id: Optional[int] = None
    planned_periods: Optional[int] = None
    plan_seq: Optional[int] = None
    is_active: Optional[bool] = None
    version_no: int # CRITICAL: Required for edits

class UnmatchedItem(BaseModel):
    plan_id: int
    block_name: str
    topic_name: str
    plan_seq: int
    suggested_chapter_id: Optional[int] = None
    suggested_chapter_name: Optional[str] = None

class UnmatchedResponse(BaseModel):
    items: List[UnmatchedItem]
    total: int

# --- Endpoints ---

@router.post("/generate", response_model=GenerateResponse)
def generate_plan(
    class_id: Optional[int] = None, 
    subject_id: Optional[int] = None, 
    db: Session = Depends(get_db),
    admin = Depends(get_current_admin)
):
    """
    Creates one syllabus_plan row per board topic. 
    Safe to call twice: existing rows are skipped.
    """
    # TODO: Implement logic to read board topics and insert into SyllabusPlan
    # For now, returning a mock response
    return {"created": 142, "skipped": 18}

@router.get("/unmatched", response_model=UnmatchedResponse)
def get_unmatched_topics(
    class_id: int,
    subject_id: int,
    db: Session = Depends(get_db),
    admin = Depends(get_current_admin)
):
    """
    Returns plan rows with no chapter_id yet.
    """
    # In a real query, you would join SyllabusPlan, SyllabusItemBlock, and Chapter to get the suggested match
    # For now, returning a mock response
    mock_items = [
        {
            "plan_id": 55, 
            "block_name": "July 2026", 
            "topic_name": "A Square and A Cube",
            "plan_seq": 1, 
            "suggested_chapter_id": 12, 
            "suggested_chapter_name": "Squares and Cubes"
        }
    ]
    return {"items": mock_items, "total": len(mock_items)}

@router.patch("/{plan_id}")
def update_plan(
    plan_id: int, 
    payload: PlanUpdate, 
    db: Session = Depends(get_db),
    admin = Depends(get_current_admin)
):
    """
    Handles both Matching (chapter_id) and Editing (periods, seq, toggle off).
    """
    # 1. Fetch the plan
    plan = db.query(SyllabusPlan).filter(SyllabusPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    # 2. Check Version (Optimistic Locking)
    if plan.version_no != payload.version_no:
        raise HTTPException(status_code=409, detail="Conflict: Plan has been updated by someone else. Please refresh.")

    # 3. Update fields
    if payload.chapter_id is not None: plan.chapter_id = payload.chapter_id
    if payload.planned_periods is not None: plan.planned_periods = payload.planned_periods
    if payload.plan_seq is not None: plan.plan_seq = payload.plan_seq
    if payload.is_active is not None: plan.is_active = payload.is_active
    
    # 4. Increment version and save
    plan.version_no += 1
    db.commit()
    
    return {"status": "success", "message": "Plan updated successfully"}

@router.get("/chapters")
def get_school_chapters(
    class_id: int,
    subject_id: int,
    db: Session = Depends(get_db),
    admin = Depends(get_current_admin)
):
    """
    Returns the school's own chapters for the matching dropdown.
    """
    chapters = db.query(Chapter).filter(Chapter.class_id == class_id, Chapter.subject_id == subject_id).all()
    return {"items": chapters, "total": len(chapters)}