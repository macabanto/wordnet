import pymongo
import networkx as nx

MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "lemmas"
SRC_COLLECTION = "lemmas-linked"
DST_COLLECTION = "linked-lemmas-second-degree"

client = pymongo.MongoClient(MONGO_URI)
src = client[DB_NAME][SRC_COLLECTION]
dst = client[DB_NAME][DST_COLLECTION]


def generate_3d_layout(nodes, links, scale=100):
    G = nx.Graph()
    for node in nodes:
        G.add_node(node['id'])

    for link in links:
        source = nodes[link['source']]['id']
        target = nodes[link['target']]['id']
        G.add_edge(source, target)

    pos = nx.spring_layout(G, dim=3, seed=42)
    return {node: tuple(scale * float(coord) for coord in pos[node]) for node in G.nodes}


def update_document_with_coords(doc, coords_map):
    for syn in doc.get("linked_synonyms", []):
        term = syn["term"]
        if term in coords_map:
            x, y, z = coords_map[term]
            syn["x"], syn["y"], syn["z"] = round(x, 3), round(y, 3), round(z, 3)
    return doc


def are_synonyms_connected(term_a, term_b):
    """Check if term_b is a synonym of term_a in any other document."""
    other_doc = src.find_one({"term": term_a})
    if not other_doc:
        return False
    return any(s["term"] == term_b for s in other_doc.get("linked_synonyms", []))


def main():
    total = 0
    for doc in src.find({}):
        center = doc["term"]
        synonyms = doc.get("linked_synonyms", [])

        # Build node list
        nodes = [{"id": center, "index": 0}]
        id_to_index = {center: 0}
        for i, syn in enumerate(synonyms, start=1):
            id_to_index[syn["term"]] = i
            nodes.append({"id": syn["term"], "index": i})

        # Star edges: term → each synonym
        links = [{"source": 0, "target": id_to_index[syn["term"]]} for syn in synonyms]

        # Add cross-links between synonyms
        seen_pairs = set()
        for i, syn_a in enumerate(synonyms):
            for j, syn_b in enumerate(synonyms):
                if i >= j:
                    continue

                a_term = syn_a["term"]
                b_term = syn_b["term"]
                pair_key = tuple(sorted([a_term, b_term]))
                if pair_key in seen_pairs:
                    continue

                if are_synonyms_connected(a_term, b_term):
                    links.append({
                        "source": id_to_index[a_term],
                        "target": id_to_index[b_term]
                    })
                    seen_pairs.add(pair_key)

        # Generate coordinates and update
        coords_map = generate_3d_layout(nodes, links)
        updated_doc = update_document_with_coords(doc, coords_map)

        # Insert into second-degree collection
        dst.replace_one({"_id": doc["_id"]}, updated_doc, upsert=True)

        total += 1
        if total % 100 == 0:
            print(f"Processed {total} documents...")

    print(f"✅ Completed second-degree layout for {total} documents.")


if __name__ == "__main__":
    main()