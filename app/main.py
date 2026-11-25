from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database.connection import get_client, setup_indexes
from app.routes.events import router as events_router

app = FastAPI(title="Event Log API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
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
