import os

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME")

if not MONGODB_URI:
    raise ValueError("MONGODB_URI environment variable is not set.")

if not MONGODB_DB_NAME:
    raise ValueError("MONGODB_DB_NAME environment variable is not set.")


def get_client() -> MongoClient:
    """Create and return a MongoClient instance."""
    try:
        client = MongoClient(MONGODB_URI)
        # Force a connection check
        client.admin.command("ping")
        return client
    except ConnectionFailure as e:
        raise ConnectionError(
            f"Failed to connect to MongoDB at {MONGODB_URI}: {e}"
        )


def get_database():
    """Return the project database."""
    client = get_client()
    return client[MONGODB_DB_NAME]


def get_collection(collection_name: str = "events"):
    """Return a collection reference from the project database."""
    db = get_database()
    return db[collection_name]


def setup_indexes(collection=None) -> None:
    """Create indexes on the events collection for all supported query patterns."""
    target = collection if collection is not None else get_collection("events")
    target.create_index("service_name")
    target.create_index("event_type")
    target.create_index("severity")
    target.create_index("resource_id")
    target.create_index([("timestamp", -1)])
    target.create_index([("service_name", 1), ("event_type", 1), ("timestamp", -1)])
