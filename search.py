"""Stage 3: Make the laws searchable by meaning.

Each chunk is turned into an embedding (a list of 384 numbers that captures
its meaning) and stored in a ChromaDB database in the db/ folder. A question
is turned into numbers the same way, and the database finds the chunks whose
numbers are closest, so "can my landlord kick me out" can match eviction
sections even without the same words.

    python search.py build              # (re)build the database from data/chunks.json
    python search.py "your question"    # show the 5 best matching sections
"""

import quiet  # noqa: F401  (must come before the AI libraries)

import json
import sys
from pathlib import Path

import chromadb
import numpy as np
from fastembed import TextEmbedding

ROOT = Path(__file__).parent
CHUNKS_FILE = ROOT / "data" / "chunks.json"
DB_DIR = ROOT / "db"
COLLECTION = "ontario_laws"

# A free embedding model that runs on this computer (no API key needed).
MODEL_NAME = "BAAI/bge-small-en-v1.5"
# This model works best when questions (not law text) start with this phrase.
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

_model = None


def get_model():
    """Load the embedding model once and reuse it."""
    global _model
    if _model is None:
        # FastEmbed runs the same model as sentence-transformers, but without
        # PyTorch (600+ MB), so it also fits on Streamlit Community Cloud.
        _model = TextEmbedding(MODEL_NAME)
    return _model


def embed(texts):
    """Turn a list of texts into embeddings (lists of numbers)."""
    vectors = np.array(list(get_model().embed(texts)))
    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
    return vectors.tolist()


def get_collection():
    """Open (or create) the law collection in the db/ folder."""
    client = chromadb.PersistentClient(path=str(DB_DIR))
    return client.get_or_create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})


def metadata_for(chunk):
    """The extra details stored next to each chunk's numbers."""
    keys = ["law", "citation", "section", "heading", "law_part", "part", "total_parts", "url", "hash"]
    return {k: chunk[k] for k in keys}


def build():
    """Embed every chunk and store it in a fresh database."""
    chunks = json.loads(CHUNKS_FILE.read_text())

    client = chromadb.PersistentClient(path=str(DB_DIR))
    if COLLECTION in [c.name for c in client.list_collections()]:
        client.delete_collection(COLLECTION)
    collection = get_collection()

    batch = 64
    for start in range(0, len(chunks), batch):
        group = chunks[start:start + batch]
        collection.add(
            ids=[c["id"] for c in group],
            documents=[c["text"] for c in group],
            embeddings=embed([c["text"] for c in group]),
            metadatas=[metadata_for(c) for c in group],
        )
        print(f"  embedded {min(start + batch, len(chunks))}/{len(chunks)} chunks", end="\r")
    print(f"\nDone: {collection.count()} chunks stored in {DB_DIR.name}/")


def search(question, k=5):
    """Return the k chunks whose meaning is closest to the question."""
    results = get_collection().query(
        query_embeddings=embed([QUERY_PREFIX + question]),
        n_results=k,
    )
    return [
        {**meta, "text": doc, "score": round(1 - dist, 3)}
        for doc, meta, dist in zip(
            results["documents"][0], results["metadatas"][0], results["distances"][0]
        )
    ]


def show(question, k=5):
    """Print the top results for a question in a readable way."""
    print(f"\nQ: {question}")
    for i, r in enumerate(search(question, k), start=1):
        part = f" (part {r['part']} of {r['total_parts']})" if r["total_parts"] > 1 else ""
        print(f"  {i}. [{r['score']:.3f}] {r['law']}, s. {r['section']} – {r['heading']}{part}")


if __name__ == "__main__":
    if sys.argv[1:] == ["build"]:
        build()
    elif sys.argv[1:]:
        show(" ".join(sys.argv[1:]))
    else:
        print(__doc__)
