import os
import pymongo
from bson.objectid import ObjectId

# === Config ===
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = "lemmas"
SOURCE_COLLECTION = "entries"
TARGET_COLLECTION = "lemmas-linked"
FAILED_COLLECTION = "lemmas-unlinked"

# === Setup clients ===
client = pymongo.MongoClient(MONGO_URI)
db = client[DB_NAME]
src = db[SOURCE_COLLECTION]
dst = db[TARGET_COLLECTION]
failed = db[FAILED_COLLECTION]

# === Resolver ===
def resolve_synonym(part_of_speech, synonym_term, current_synonyms):
    synonym_lower = synonym_term.lower()
    candidates = list(src.find({"term": synonym_lower}))
    if not candidates:
        return None

    if len(candidates) == 1:
        return candidates[0]["_id"]

    pos_matches = [c for c in candidates if c.get("part_of_speech") == part_of_speech]
    if len(pos_matches) == 1:
        return pos_matches[0]["_id"]

    def score(doc):
        return len(set(doc.get("synonyms", [])) & set(current_synonyms))

    best_match = max(pos_matches or candidates, key=score, default=None)
    return best_match["_id"] if best_match else None

# === Get already-linked IDs ===
linked_ids = set(dst.distinct("_id"))
print(f"🔒 {len(linked_ids)} lemmas already linked. Skipping them...")

# === Main processing loop ===
linked_count = 0
skipped_count = 0
error_count = 0

cursor = src.find({"_id": {"$nin": list(linked_ids)}}, no_cursor_timeout=True)

for doc in cursor:
    try:
        term = doc.get("term")
        pos = doc.get("part_of_speech")
        synonyms = doc.get("synonyms", [])

        linked = []
        resolved_count = 0
        unresolved_count = 0

        for syn in synonyms:
            resolved = resolve_synonym(pos, syn, synonyms)
            if resolved:
                linked.append({ "term": syn, "id": resolved })
                resolved_count += 1
            else:
                linked.append({ "term": syn, "id": None })
                unresolved_count += 1

        if unresolved_count == 0:
            print(f'[💡] Linking: "{term}" ({resolved_count}/{len(synonyms)} synonyms linked)')
        else:
            print(f'[⚠️] Linking: "{term}" ({resolved_count}/{len(synonyms)} linked, {unresolved_count} unresolved)')

        # Save to lemmas-linked
        new_doc = {
            "_id": doc["_id"],
            "term": term,
            "part_of_speech": pos,
            "definition": doc.get("definition"),
            "linked_synonyms": linked
        }
        dst.insert_one(new_doc)
        linked_count += 1

        # Save to lemmas-unlinked if any failures
        if unresolved_count > 0:
            if failed.count_documents({"_id": doc["_id"]}) == 0:
                failed.insert_one({
                    "_id": doc["_id"],
                    "term": term,
                    "part_of_speech": pos,
                    "definition": doc.get("definition"),
                    "synonyms": synonyms,
                    "linked_synonyms": linked,
                    "resolved_count": resolved_count,
                    "unresolved_count": unresolved_count
                })

    except Exception as e:
        print(f"[❌] Error processing '{doc.get('term')}' — {e}")
        error_count += 1
        continue

print(f"\n✅ Linking complete.")
print(f"🔗 {linked_count} lemmas newly linked.")
print(f"⏭️ {skipped_count} skipped (already linked).")
print(f"❌ {error_count} errors.")