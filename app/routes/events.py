from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.models.event import EventCreate, EventFilters, EventResponse, Severity
from app.services.event_service import EventService

router = APIRouter(prefix="/events", tags=["events"])


def get_event_service() -> EventService:
    """Dependency provider for EventService."""
    return EventService()


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
def ingest_event(
    event: EventCreate,
    service: EventService = Depends(get_event_service),
) -> EventResponse:
    """Ingest a new audit event."""
    return service.ingest_event(event)


@router.get("", response_model=list[EventResponse], status_code=status.HTTP_200_OK)
def list_events(
    service_name: Optional[str] = Query(default=None),
    event_type: Optional[str] = Query(default=None),
    severity: Optional[Severity] = Query(default=None),
    start_time: Optional[datetime] = Query(default=None),
    end_time: Optional[datetime] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    service: EventService = Depends(get_event_service),
) -> list[EventResponse]:
    """List audit events with optional filters and pagination."""
    filters = EventFilters(
        service_name=service_name,
        event_type=event_type,
        severity=severity,
        start_time=start_time,
        end_time=end_time,
    )
    return service.list_events(filters=filters, limit=limit, offset=offset)


@router.get(
    "/resource/{resource_id}",
    response_model=list[EventResponse],
    status_code=status.HTTP_200_OK,
)
def get_events_by_resource(
    resource_id: str,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    service: EventService = Depends(get_event_service),
) -> list[EventResponse]:
    """Retrieve all events for a specific resource_id."""
    return service.get_resource_events(
        resource_id=resource_id, limit=limit, offset=offset
    )


@router.get("/{event_id}", response_model=EventResponse, status_code=status.HTTP_200_OK)
def get_event_by_id(
    event_id: str,
    service: EventService = Depends(get_event_service),
) -> EventResponse:
    """Retrieve a single event by its ID."""
    event = service.get_event(event_id)
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )
    return event
