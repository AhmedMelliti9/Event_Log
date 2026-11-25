from fastapi import FastAPI

from app.database.connection import get_client, setup_indexes
from app.routes.events import router as events_router

app = FastAPI(title="Event Log API")
app.include_router(events_router)


@app.on_event("startup")
def startup():
    """Verify MongoDB connection and ensure collection indexes exist on startup."""
    client = get_client()
    print(f"Connected to MongoDB: {client.server_info()['version']}")
    setup_indexes()


@app.get("/health")
def health_check():
    return {"status": "ok"}
