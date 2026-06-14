from fastapi import APIRouter, Query

from app.dependencies import CurrentUser, DBSession
from app.schemas.calendar import CreateEventRequest, UpdateEventRequest
from app.services import calendar_service

router = APIRouter(prefix="/calendar", tags=["Calendar"])


@router.get("/events", response_model=list[dict])
async def list_events(
    current_user: CurrentUser,
    db: DBSession,
    days_ahead: int = Query(default=7, ge=1, le=90),
    max_results: int = Query(default=20, ge=1, le=100),
):
    return await calendar_service.list_events(db, current_user.id, days_ahead, max_results)


@router.post("/events", response_model=dict, status_code=201)
async def create_event(body: CreateEventRequest, current_user: CurrentUser, db: DBSession):
    return await calendar_service.create_event(
        db, current_user.id,
        body.title, body.start, body.end,
        body.description, body.attendees or None,
    )


@router.patch("/events/{event_id}", response_model=dict)
async def update_event(event_id: str, body: UpdateEventRequest, current_user: CurrentUser, db: DBSession):
    updates: dict = {}
    if body.title is not None:
        updates["summary"] = body.title
    if body.start is not None:
        updates["start"] = {"dateTime": body.start.isoformat(), "timeZone": "UTC"}
    if body.end is not None:
        updates["end"] = {"dateTime": body.end.isoformat(), "timeZone": "UTC"}
    if body.description is not None:
        updates["description"] = body.description
    return await calendar_service.update_event(db, current_user.id, event_id, updates)


@router.delete("/events/{event_id}", status_code=204)
async def delete_event(event_id: str, current_user: CurrentUser, db: DBSession):
    await calendar_service.delete_event(db, current_user.id, event_id)
