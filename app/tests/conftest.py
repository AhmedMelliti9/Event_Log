import os

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from pymongo import MongoClient

from app.database.connection import setup_indexes
from app.main import app
from app.repositories.event_repository import EventRepository
from app.routes.events import get_event_service
from app.services.event_service import EventService

load_dotenv()

TEST_DB_NAME = "event_log_test"


@pytest.fixture
def test_collection():
    """Provide a clean test collection in event_log_test for each test."""
    uri = os.getenv("MONGODB_URI")
    client = MongoClient(uri)
    db = client[TEST_DB_NAME]
    db["events"].drop()
    collection = db["events"]
    setup_indexes(collection)
    yield collection
    db["events"].drop()
    client.close()


@pytest.fixture
def client(test_collection):
    """Provide a FastAPI TestClient wired to the test MongoDB collection."""
    app.dependency_overrides[get_event_service] = lambda: EventService(
        EventRepository(collection=test_collection)
    )
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
