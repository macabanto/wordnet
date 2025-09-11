import pymongo
import networkx as nx
import numpy as np

MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "lemmas"
COLLECTION = "lemmas-linked"

client = pymongo.MongoClient(MONGO_URI)
collection = client[DB_NAME][COLLECTION]

def generate_3d_layout(nodes, links, scale=100):
    G = nx.Graph()
    for node in nodes:
        G.add_node(node['id'])

    for link in links:
        source = nodes[link['source']]['id']
        target = nodes[link['target']]['id']
        G.add_edge(source, target)

    pos = nx.spring_layout(G, dim=3, seed=42)  # 3D layout
    return {node: tuple(scale * float(coord) for coord in pos[node]) for node in G.nodes}

def update_document_with_coords(doc, coords_map):
    for syn in doc.get("linked_synonyms", []):
        term = syn["term"]
        if term in coords_map:
            x, y, z = coords_map[term]
            syn["x"], syn["y"], syn["z"] = round(x, 3), round(y, 3), round(z, 3)
    return doc

def main():
    total = 0
    for doc in collection.find({}):
        center = doc["term"]
        synonyms = doc.get("linked_synonyms", [])
        
        # Build node and link lists (like JS)
        nodes = [{"id": center, "index": 0}]
        id_to_index = {center: 0}
        for i, syn in enumerate(synonyms, start=1):
            id_to_index[syn["term"]] = i
            nodes.append({"id": syn["term"], "index": i})

        links = []
        # Root connected to all
        for syn in synonyms:
            links.append({"source": 0, "target": id_to_index[syn["term"]]})
        
        # Optional: add cross-links between synonyms based on similarity logic
        # You could build edges between synonyms if you have that logic elsewhere

        # Generate 3D layout
        coords_map = generate_3d_layout(nodes, links)

        # Inject coordinates into linked_synonyms
        updated_doc = update_document_with_coords(doc, coords_map)

        # Save back to Mongo
        collection.update_one({"_id": doc["_id"]}, {"$set": {
            "linked_synonyms": updated_doc["linked_synonyms"]
        }})
        total += 1

    print(f"✅ Finished assigning coordinates to {total} documents.")

if __name__ == "__main__":
    main()