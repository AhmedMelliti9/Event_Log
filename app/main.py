from fastapi import FastAPI

from app.database.connection import get_client

app = FastAPI(title="Event Log API")


@app.on_event("startup")
def startup():
    """Verify MongoDB connection on startup."""
    client = get_client()
    print(f"Connected to MongoDB: {client.server_info()['version']}")


@app.get("/health")
def health_check():
    return {"status": "ok"}
