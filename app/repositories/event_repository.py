import re
from typing import Any, Optional

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import DESCENDING
from pymongo.collection import Collection

from app.database.connection import get_collection
from app.models.event import EventCreate, EventFilters, EventResponse

_OBJECT_ID_RE = re.compile(r"^[0-9a-fA-F]{24}$")


class InvalidObjectIdError(ValueError):
    """Raised when a provided event ID is not a valid 24-character hex ObjectId."""


def _validate_object_id(event_id: str) -> ObjectId:
    """Validate 24-char hex format before constructing a BSON ObjectId."""
    if not isinstance(event_id, str) or not _OBJECT_ID_RE.match(event_id):
        raise InvalidObjectIdError(f"Invalid event ID format: {event_id}")
    try:
        return ObjectId(event_id)
    except InvalidId as exc:
        raise InvalidObjectIdError(f"Invalid event ID format: {event_id}") from exc


class EventRepository:
    """Append-only repository for audit events in MongoDB."""

    def __init__(self, collection: Optional[Collection] = None) -> None:
        self._collection = collection if collection is not None else get_collection("events")

    def create(self, event_data: EventCreate) -> EventResponse:
        """Insert a new event document and return the created event."""
        document: dict[str, Any] = event_data.model_dump()
        document["severity"] = event_data.severity.value
        result = self._collection.insert_one(document)
        document["_id"] = result.inserted_id
        return EventResponse.from_mongo(document)

    def get_by_id(self, event_id: str) -> Optional[EventResponse]:
        """Return a single event by its ObjectId string, or None if not found."""
        oid = _validate_object_id(event_id)
        document = self._collection.find_one({"_id": oid})
        if document is None:
            return None
        return EventResponse.from_mongo(document)

    def query(
        self,
        filters: Optional[EventFilters] = None,
        limit: int = 50,
        skip: int = 0,
    ) -> list[EventResponse]:
        """Return filtered, timestamp-descending, paginated events."""
        mongo_query: dict[str, Any] = {}
        if filters is not None:
            if filters.service_name is not None:
                mongo_query["service_name"] = filters.service_name
            if filters.event_type is not None:
                mongo_query["event_type"] = filters.event_type
            if filters.severity is not None:
                mongo_query["severity"] = filters.severity.value

            time_range: dict[str, Any] = {}
            if filters.start_time is not None:
                time_range["$gte"] = filters.start_time
            if filters.end_time is not None:
                time_range["$lte"] = filters.end_time
            if time_range:
                mongo_query["timestamp"] = time_range

        cursor = (
            self._collection.find(mongo_query)
            .sort("timestamp", DESCENDING)
            .skip(skip)
            .limit(limit)
        )
        return [EventResponse.from_mongo(doc) for doc in cursor]

    def get_by_resource_id(
        self,
        resource_id: str,
        limit: int = 50,
        skip: int = 0,
    ) -> list[EventResponse]:
        """Return timestamp-descending, paginated events for a specific resource_id."""
        cursor = (
            self._collection.find({"resource_id": resource_id})
            .sort("timestamp", DESCENDING)
            .skip(skip)
            .limit(limit)
        )
        return [EventResponse.from_mongo(doc) for doc in cursor]
