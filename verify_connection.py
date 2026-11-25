"""
Verification script for Task 1.
Connects to MongoDB, inserts a test document, then deletes it.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.database.connection import get_collection


def verify_connection():
    collection = get_collection("events")

    # Insert a test document
    test_doc = {"test": True, "message": "Task 1 verification"}
    result = collection.insert_one(test_doc)
    print(f"Inserted test document with _id: {result.inserted_id}")

    # Read it back
    found = collection.find_one({"_id": result.inserted_id})
    print(f"Retrieved test document: {found}")

    # Delete it
    collection.delete_one({"_id": result.inserted_id})
    print("Deleted test document.")

    # Confirm deletion
    gone = collection.find_one({"_id": result.inserted_id})
    assert gone is None, "Test document was not deleted!"
    print("Verification complete — MongoDB connection works.")


if __name__ == "__main__":
    verify_connection()
