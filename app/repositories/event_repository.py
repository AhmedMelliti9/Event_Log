import base64
import json
import re
from datetime import datetime
from typing import Any, Optional

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import DESCENDING
from pymongo.collection import Collection

from app.database.connection import get_collection
from app.models.event import EventCreate, EventFilters, EventResponse, EventStatsItem

_OBJECT_ID_RE = re.compile(r"^[0-9a-fA-F]{24}$")


class InvalidObjectIdError(ValueError):
    """Raised when a provided event ID is not a valid 24-character hex ObjectId."""


class InvalidCursorError(ValueError):
    """Raised when a pagination cursor cannot be decoded or is malformed."""


def _validate_object_id(event_id: str) -> ObjectId:
    """Validate 24-char hex format before constructing a BSON ObjectId."""
    if not isinstance(event_id, str) or not _OBJECT_ID_RE.match(event_id):
        raise InvalidObjectIdError(f"Invalid event ID format: {event_id}")
    try:
        return ObjectId(event_id)
    except InvalidId as exc:
        raise InvalidObjectIdError(f"Invalid event ID format: {event_id}") from exc


def _encode_cursor(timestamp: datetime, event_id: str) -> str:
    """Encode (timestamp, _id) as an opaque URL-safe base64 cursor."""
    payload = json.dumps({"ts": timestamp.isoformat(), "id": event_id}).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("ascii")


def _decode_cursor(cursor: str) -> tuple[datetime, ObjectId]:
    """Decode an opaque pagination cursor into (timestamp, ObjectId)."""
    try:
        raw = base64.urlsafe_b64decode(cursor.encode("ascii"))
        data = json.loads(raw.decode("utf-8"))
        ts = datetime.fromisoformat(data["ts"])
        oid = _validate_object_id(data["id"])
        return ts, oid
    except Exception as exc:
        raise InvalidCursorError("Invalid pagination cursor") from exc


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

    def _paginate_query(
        self,
        base_query: dict[str, Any],
        limit: int,
        cursor: Optional[str],
    ) -> tuple[list[EventResponse], Optional[str]]:
        """Execute a cursor-paginated query sorted by (timestamp DESC, _id DESC)."""
        mongo_query: dict[str, Any] = dict(base_query)
        if cursor is not None:
            cursor_ts, cursor_oid = _decode_cursor(cursor)
            cursor_filter = {
                "$or": [
                    {"timestamp": {"$lt": cursor_ts}},
                    {"timestamp": cursor_ts, "_id": {"$lt": cursor_oid}},
                ]
            }
            if mongo_query:
                mongo_query = {"$and": [mongo_query, cursor_filter]}
            else:
                mongo_query = cursor_filter

        docs = list(
            self._collection.find(mongo_query)
            .sort([("timestamp", DESCENDING), ("_id", DESCENDING)])
            .limit(limit + 1)
        )

        has_more = len(docs) > limit
        if has_more:
            docs = docs[:limit]

        items = [EventResponse.from_mongo(doc) for doc in docs]
        next_cursor = (
            _encode_cursor(items[-1].timestamp, items[-1].id)
            if has_more and items
            else None
        )
        return items, next_cursor

    def query(
        self,
        filters: Optional[EventFilters] = None,
        limit: int = 50,
        cursor: Optional[str] = None,
    ) -> tuple[list[EventResponse], Optional[str]]:
        """Return filtered, timestamp-descending, cursor-paginated events."""
        base_query: dict[str, Any] = {}
        if filters is not None:
            if filters.service_name is not None:
                base_query["service_name"] = filters.service_name
            if filters.event_type is not None:
                base_query["event_type"] = filters.event_type
            if filters.severity is not None:
                base_query["severity"] = filters.severity.value

            time_range: dict[str, Any] = {}
            if filters.start_time is not None:
                time_range["$gte"] = filters.start_time
            if filters.end_time is not None:
                time_range["$lte"] = filters.end_time
            if time_range:
                base_query["timestamp"] = time_range

        return self._paginate_query(base_query, limit=limit, cursor=cursor)

    def get_by_resource_id(
        self,
        resource_id: str,
        limit: int = 50,
        cursor: Optional[str] = None,
    ) -> tuple[list[EventResponse], Optional[str]]:
        """Return timestamp-descending, cursor-paginated events for a specific resource_id."""
        return self._paginate_query(
            {"resource_id": resource_id}, limit=limit, cursor=cursor
        )

    def get_stats(self) -> list[EventStatsItem]:
        """Return event counts grouped by service_name and event_type via aggregation."""
        pipeline = [
            {
                "$group": {
                    "_id": {
                        "service_name": "$service_name",
                        "event_type": "$event_type",
                    },
                    "count": {"$sum": 1},
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "service_name": "$_id.service_name",
                    "event_type": "$_id.event_type",
                    "count": 1,
                }
            },
            {"$sort": {"service_name": 1, "event_type": 1}},
        ]
        results = self._collection.aggregate(pipeline)
        return [EventStatsItem(**doc) for doc in results]
