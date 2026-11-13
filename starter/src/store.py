from __future__ import annotations
from pathlib import Path
from typing import Any
from .models import Chunk


class ChromaStore:
    """Chroma PersistentClient, cosine, filter metadata. HNSW là tìm kiếm xấp xỉ."""

    def __init__(self, path: Path, dimensions: int) -> None:
        import chromadb
        self.path, self.dimensions = Path(path), dimensions
        self.path.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(self.path))

    def collection(self, name):
        try:
            return self.client.get_or_create_collection(name, configuration={"hnsw": {"space": "cosine"}})
        except TypeError:    # chromadb bản cũ
            return self.client.get_or_create_collection(name, metadata={"hnsw:space": "cosine"})

    def space_info(self, name):
        col = self.collection(name)
        for attr in ("configuration_json", "configuration"):
            if hasattr(col, attr):
                return str(getattr(col, attr))
        return str(getattr(col, "metadata", None))

    def reset(self, name):
        try:
            self.client.delete_collection(name)
        except Exception:
            pass

    def count(self, name): return self.collection(name).count()

    def source_hashes(self, name):
        got = self.collection(name).get(include=["metadatas"])
        return {m["source_id"]: m["content_hash"] for m in got["metadatas"]}

    def delete_sources(self, name, source_ids):
        col, removed = self.collection(name), 0
        for sid in source_ids:
            ids = col.get(where={"source_id": sid})["ids"]
            if ids:
                col.delete(ids=ids); removed += len(ids)
        return removed

    def upsert(self, name, chunks: list[Chunk], vectors):
        if len(chunks) != len(vectors):
            raise ValueError("Số chunk và số vector khác nhau")
        if any(len(v) != self.dimensions for v in vectors):
            raise ValueError("Sai số chiều vector")
        if chunks:
            self.collection(name).upsert(ids=[c.chunk_id for c in chunks], embeddings=vectors,
                                         documents=[c.text for c in chunks], metadatas=[c.metadata for c in chunks])

    def search(self, name, query_vector, top_k=3, filters: dict[str, Any] | None = None):
        where = None
        if filters:
            items = [{k: v} for k, v in filters.items()]
            where = items[0] if len(items) == 1 else {"$and": items}
        res = self.collection(name).query(query_embeddings=[query_vector], n_results=top_k, where=where,
                                          include=["documents", "metadatas", "distances"])
        return [{"chunk_id": i, "text": d, "score": 1.0 - float(dist), "distance": float(dist), "metadata": m}
                for i, d, m, dist in zip(res["ids"][0], res["documents"][0], res["metadatas"][0], res["distances"][0])]