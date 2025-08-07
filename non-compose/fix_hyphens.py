import os
import pymongo

# === Config ===
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = "lemmas"
COLLECTION_NAME = "entries"

client = pymongo.MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

updated_count = 0

print("🔍 Scanning for hyphenated synonyms...")

for doc in collection.find({}, no_cursor_timeout=True):
    original_synonyms = doc.get("synonyms", [])
    updated_synonyms = []

    changed = False
    for syn in original_synonyms:
        if "-" in syn:
            cleaned = syn.replace("-", " ")
            updated_synonyms.append(cleaned)
            changed = True
        else:
            updated_synonyms.append(syn)

    if changed:
        collection.update_one(
            {"_id": doc["_id"]},
            {"$set": {"synonyms": updated_synonyms}}
        )
        updated_count += 1
        print(f"[🔧] Updated '{doc['term']}' with cleaned synonyms.")

print(f"\n✅ Done. {updated_count} lemmas updated.")