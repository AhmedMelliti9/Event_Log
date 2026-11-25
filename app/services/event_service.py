from typing import Optional

from app.models.event import (
    EventCreate,
    EventFilters,
    EventResponse,
    EventStatsItem,
    PaginatedEventsResponse,
)
from app.repositories.event_repository import EventRepository


class EventService:
    """Business logic layer for audit events."""

    def __init__(self, repository: Optional[EventRepository] = None) -> None:
        self._repository = repository if repository is not None else EventRepository()

    def ingest_event(self, event_data: EventCreate) -> EventResponse:
        """Persist a new audit event."""
        return self._repository.create(event_data)

    def list_events(
        self,
        filters: Optional[EventFilters] = None,
        limit: int = 50,
        cursor: Optional[str] = None,
    ) -> PaginatedEventsResponse:
        """List events matching optional filters with cursor pagination."""
        items, next_cursor = self._repository.query(
            filters=filters, limit=limit, cursor=cursor
        )
        return PaginatedEventsResponse(items=items, next_cursor=next_cursor)

    def get_event(self, event_id: str) -> Optional[EventResponse]:
        """Retrieve a single event by ID, or None if not found."""
        return self._repository.get_by_id(event_id)

    def get_resource_events(
        self,
        resource_id: str,
        limit: int = 50,
        cursor: Optional[str] = None,
    ) -> PaginatedEventsResponse:
        """Retrieve cursor-paginated events for a specific resource_id."""
        items, next_cursor = self._repository.get_by_resource_id(
            resource_id=resource_id, limit=limit, cursor=cursor
        )
        return PaginatedEventsResponse(items=items, next_cursor=next_cursor)

    def get_stats(self) -> list[EventStatsItem]:
        """Return event counts grouped by service_name and event_type."""
        return self._repository.get_stats()
