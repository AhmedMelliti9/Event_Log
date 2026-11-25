# Event Log API

## General Idea

**Event Log** is an append-only audit logging platform built with **FastAPI**, **MongoDB (PyMongo)**, and a **React** dashboard. Multiple backend services emit audit events (user logins, configuration changes, data access, and errors) with varying payload structures. Events are written once, never updated or deleted, and queried by service, event type, severity, time range, or target resource.

### Architecture & Layers

- **Routes (`app/routes/events.py`)** — HTTP endpoints, query parameter parsing, and response serialization.
- **Services (`app/services/event_service.py`)** — Business logic separating HTTP handling from persistence.
- **Repositories (`app/repositories/event_repository.py`)** — Direct PyMongo data access with an append-only contract (no update/delete methods), cursor-based pagination, and aggregation stats.
- **Models (`app/models/event.py`)** — Pydantic schemas enforcing required metadata while allowing arbitrary JSON objects in `payload`.
- **Database (`app/database/connection.py`)** — Environment-driven MongoDB connection (`MONGODB_URI`, `MONGODB_DB_NAME`) and startup index creation.
- **Dashboard (`dashboard/`)** — React + Vite frontend displaying aggregated event stats and a filterable, cursor-paginated event feed.

### Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/events` | Ingest a new audit event (`201`) |
| `GET` | `/events` | List events with filters and cursor pagination (`200`) |
| `GET` | `/events/stats` | Aggregated event counts grouped by `service_name` and `event_type` (`200`) |
| `GET` | `/events/resource/{resource_id}` | Retrieve cursor-paginated events for a specific resource (`200`) |
| `GET` | `/events/{event_id}` | Retrieve a single event by its ObjectId (`200` / `404`) |

### Running Locally

1. Start local MongoDB (`mongod` on `127.0.0.1:27017`).
2. Configure `.env` with `MONGODB_URI` and `MONGODB_DB_NAME`.
3. Install Python dependencies and start FastAPI:
   ```bash
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```
4. Start the React dashboard:
   ```bash
   cd dashboard
   npm install
   npm run dev
   ```

---

## Indexing Strategy

### Why is a compound index sometimes better than multiple single-field indexes?

- **Single B-tree lookup vs. index intersection:** When querying on multiple fields together (for example, `service_name` + `event_type` sorted by `timestamp` descending), a compound index `(service_name, event_type, timestamp: -1)` lets MongoDB locate the exact matching slice in a single index traversal instead of intersecting separate single-field indexes.
- **Built-in sort order (avoids in-memory sort):** Because `timestamp: -1` is the trailing key of the compound index, documents matching `(service_name, event_type)` are already ordered by `timestamp` descending in the index. MongoDB can stream results directly without loading them into memory to sort (which would otherwise fail or spill once exceeding the 100 MB sort limit).
- **ESR (Equality, Sort, Range) rule & prefix support:** A compound index `(service_name, event_type, timestamp: -1)` also serves prefix queries on `service_name` alone or `(service_name, event_type)`, reducing the number of separate indexes MongoDB has to maintain on every insert.

---

## SQL vs NoSQL Comparison

### Event Log (this project) — Why MongoDB was chosen

1. **What is the primary query pattern?**
   High-volume single-document writes (`insert_one`), time-ordered filtered reads by `service_name`, `event_type`, `severity`, and `timestamp` range, resource history lookups by `resource_id`, and aggregation counts grouped by `(service_name, event_type)`.
2. **Does the data have a fixed or variable schema?**
   **Variable schema.** Top-level metadata (`service_name`, `event_type`, `severity`, `timestamp`, `resource_id`) is consistent, while `payload` varies per event type (e.g., `ip_address` + `user_agent` for logins vs. `amount` + `currency` for billing) without requiring schema migrations.
3. **Are relationships between entities important?**
   **No.** Each event is self-contained and embeds a snapshot of its context at the moment it occurred. No joins across collections are needed.
4. **Is the data immutable or frequently updated?**
   **Immutable (append-only).** Events are written once and never updated or deleted, so there is no need for multi-table foreign-key cascades or complex ACID update transactions.
5. **What would be difficult or awkward in the other database (PostgreSQL)?**
   Representing arbitrary, evolving per-event-type `payload` fields in normalized SQL columns would require frequent `ALTER TABLE` migrations, sparse nullable columns, or an EAV (Entity-Attribute-Value) anti-pattern. While PostgreSQL `JSONB` helps, MongoDB natively stores, indexes, and queries document structures without rigid table definitions.

### Library Catalog (Project 05) — Why PostgreSQL was chosen

1. **What is the primary query pattern?**
   Relational queries across normalized entities: looking up books with their authors, categories, and borrowing/loan status via SQL `JOIN`s, enforcing uniqueness (e.g., ISBN, member email), and updating inventory/loan state.
2. **Does the data have a fixed or variable schema?**
   **Fixed schema.** Books, authors, members, and loans have well-defined, predictable attributes and strict data types enforced at the database level.
3. **Are relationships between entities important?**
   **Yes.** Books relate to authors (many-to-many) and loans relate members to books (one-to-many). Foreign keys and referential integrity ensure a loan cannot reference a non-existent book or member.
4. **Is the data immutable or frequently updated?**
   **Frequently updated.** Book availability counts, loan statuses (`borrowed` → `returned`), and member records change continuously and require ACID transactions so two users cannot borrow the last copy simultaneously.
5. **What would be difficult or awkward in the other database (MongoDB)?**
   Enforcing referential integrity across separate collections (e.g., preventing deletion of an author with active books, or keeping embedded author names synchronized across thousands of book documents when an author's details change) is awkward in MongoDB, and relational `JOIN`s (`$lookup`) are slower and less natural than SQL joins.
