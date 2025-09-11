import pymongo
from bson import ObjectId

# --- Config ---
MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "lemmas"
SOURCE_COLLECTION = "lemmas-linked"
TARGET_COLLECTION = "lemmas-reciprocal"

# --- Connect ---
client = pymongo.MongoClient(MONGO_URI)
db = client[DB_NAME]
src = db[SOURCE_COLLECTION]
dst = db[TARGET_COLLECTION]

# --- Reset target collection ---
dst.drop()

# --- Build lookup dictionary (id -> set of linked ids) ---
print("Building in-memory synonym map...")
id_to_links = {}

for doc in src.find({}, {"_id": 1, "linked_synonyms.id": 1}):
    source_id = doc["_id"]
    linked_ids = {getattr(syn["id"], "$oid", syn["id"]) for syn in doc.get("linked_synonyms", [])}
    id_to_links[str(source_id)] = linked_ids

# --- Filter reciprocal links and copy new docs ---
print("Filtering reciprocal synonyms...")
for doc in src.find():
    term_id = str(doc["_id"])
    reciprocal_synonyms = []

    for syn in doc.get("linked_synonyms", []):
        syn_id = str(getattr(syn["id"], "$oid", syn["id"]))
        # Check if target also links back to source
        if syn_id in id_to_links and term_id in id_to_links[syn_id]:
            reciprocal_synonyms.append({
                "term": syn["term"],
                "id": ObjectId(syn_id)
            })

    new_doc = {
        "_id": doc["_id"],
        "term": doc["term"],
        "part_of_speech": doc.get("part_of_speech"),
        "definition": doc.get("definition"),
        "linked_synonyms": reciprocal_synonyms,
        "unlinked_synonyms": []  # optional
    }
    dst.insert_one(new_doc)

print("Done. Reciprocal collection created as:", TARGET_COLLECTION)