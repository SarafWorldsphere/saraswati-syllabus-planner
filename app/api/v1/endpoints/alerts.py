"""Teacher alerts. The streak is computed when this list is read.

missed_days is not a column. The only stored row is the headmaster's
decision, created the first time a streak reaches three working days.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import Caller, get_session, require_plan_writer
from app.schemas.common import ItemList
from app.schemas.school import AlertOut, AlertPatch
from app.services.alert_service import AlertService
from app.utils.lists import item_list

router = APIRouter(prefix="/teacher-alerts", tags=["teacher alerts"])


@router.get("", response_model=ItemList[AlertOut], summary="Teachers who have stopped marking")
def list_alerts(db: Session = Depends(get_session), caller: Caller = Depends(require_plan_writer)):
    """Empty when the school timetable table is not in this database. A free day is not a miss."""
    return item_list(AlertService(db, caller).list_open())


@router.patch("/{alert_id}", response_model=AlertOut, summary="Acknowledge or close an alert")
def update_alert(
    alert_id: int,
    body: AlertPatch,
    db: Session = Depends(get_session),
    caller: Caller = Depends(require_plan_writer),
):
    """closed_by and closed_at come from the token, not from the body."""
    return AlertService(db, caller).update(alert_id, body.status, body.closed_reason)
