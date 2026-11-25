from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class Severity(str, Enum):
    """Allowed severity levels for audit events."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class EventCreate(BaseModel):
    """Schema for ingesting a new audit event."""

    service_name: str = Field(..., min_length=1, description="Name of the emitting service")
    event_type: str = Field(..., min_length=1, description="Type of the event")
    severity: Severity = Field(..., description="Event severity level")
    timestamp: datetime = Field(..., description="ISO 8601 timestamp when the event occurred")
    resource_id: str = Field(..., min_length=1, description="Identifier of the related resource")
    payload: dict[str, Any] = Field(
        ...,
        description="Arbitrary JSON object containing event-specific context",
    )


class EventResponse(BaseModel):
    """Schema returned by the API for an audit event."""

    id: str = Field(..., description="String representation of MongoDB ObjectId")
    service_name: str
    event_type: str
    severity: Severity
    timestamp: datetime
    resource_id: str
    payload: dict[str, Any]

    @classmethod
    def from_mongo(cls, document: dict[str, Any]) -> "EventResponse":
        """Convert a MongoDB document (with ObjectId `_id`) into an EventResponse."""
        return cls(
            id=str(document["_id"]),
            service_name=document["service_name"],
            event_type=document["event_type"],
            severity=document["severity"],
            timestamp=document["timestamp"],
            resource_id=document["resource_id"],
            payload=document["payload"],
        )


class EventFilters(BaseModel):
    """Query parameters for filtering audit events."""

    service_name: Optional[str] = Field(default=None, description="Filter by service name")
    event_type: Optional[str] = Field(default=None, description="Filter by event type")
    severity: Optional[Severity] = Field(default=None, description="Filter by severity level")
    start_time: Optional[datetime] = Field(
        default=None, description="Include events at or after this timestamp"
    )
    end_time: Optional[datetime] = Field(
        default=None, description="Include events at or before this timestamp"
    )


class PaginatedEventsResponse(BaseModel):
    """Cursor-paginated list of audit events."""

    items: list[EventResponse]
    next_cursor: Optional[str] = Field(
        default=None, description="Opaque cursor for fetching the next page"
    )


class EventStatsItem(BaseModel):
    """Aggregated event count grouped by service_name and event_type."""

    service_name: str
    event_type: str
    count: int
