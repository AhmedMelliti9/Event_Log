# Event Log API

Append-only audit event log service built with FastAPI and MongoDB (PyMongo).

## Indexing Strategy

### Why is a compound index sometimes better than multiple single-field indexes?

- **Single B-tree lookup vs. index intersection:** When querying on multiple fields together (for example, `service_name` + `event_type` sorted by `timestamp` descending), a compound index `(service_name, event_type, timestamp: -1)` lets MongoDB locate the exact matching slice in a single index traversal instead of intersecting separate single-field indexes.
- **Built-in sort order (avoids in-memory sort):** Because `timestamp: -1` is the trailing key of the compound index, documents matching `(service_name, event_type)` are already ordered by `timestamp` descending in the index. MongoDB can stream results directly without loading them into memory to sort (which would otherwise fail or spill once exceeding the 100 MB sort limit).
- **ESR (Equality, Sort, Range) rule & prefix support:** A compound index `(service_name, event_type, timestamp: -1)` also serves prefix queries on `service_name` alone or `(service_name, event_type)`, reducing the number of separate indexes MongoDB has to maintain on every insert.
