import os
import pymongo
from collections import defaultdict

# === Config ===
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = "lemmas"
COLLECTION_NAME = "entries"

client = pymongo.MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

# === Deduplication based on (term, part_of_speech, definition)
print("🔍 Finding duplicates based on (term, part_of_speech, definition)...")

duplicates_map = defaultdict(list)

for doc in collection.find({}, no_cursor_timeout=True):
    term = doc.get("term", "").strip().lower()
    pos = doc.get("part_of_speech")
    definition = doc.get("definition", "").strip().lower()
    key = (term, pos, definition)
    duplicates_map[key].append(doc["_id"])

removed = 0
kept = 0

for key, doc_ids in duplicates_map.items():
    if len(doc_ids) > 1:
        to_remove = doc_ids[1:]  # keep the first, remove the rest
        result = collection.delete_many({ "_id": { "$in": to_remove } })
        removed += result.deleted_count
        kept += 1
        print(f"[🧹] Removed {result.deleted_count} duplicates for: {key}")
    else:
        kept += 1

print(f"\n✅ Done. {kept} unique lemmas retained, {removed} duplicates removed.")