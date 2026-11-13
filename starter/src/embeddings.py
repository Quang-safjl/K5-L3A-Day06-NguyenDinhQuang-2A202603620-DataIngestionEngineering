from __future__ import annotations
import os
from .config import EMBEDDING_BATCH, EMBEDDING_MODEL


class MyEmbedder:
    """EmbeddingGemma 2 local qua sentence-transformers. Không fallback sang model khác khi lỗi."""

    def __init__(self, model_name: str = EMBEDDING_MODEL) -> None:
        from sentence_transformers import SentenceTransformer
        self.model_name = model_name
        try:
            self.model = SentenceTransformer(model_name)
        except Exception as e:
            raise RuntimeError(f"Không tải được model '{model_name}': {e}\n"
                               "Nếu model đã tải về máy, đặt EMBEDDING_MODEL=<thư mục model> trong starter/.env") from e
        self.dimensions = int(self.model.get_sentence_embedding_dimension())
        prompts = dict(getattr(self.model, "prompts", {}) or {})
        self.q_prefix = os.getenv("QUERY_PREFIX") or None      # chỉ đặt nếu model.prompts thiếu query/document
        self.d_prefix = os.getenv("DOC_PREFIX") or None
        self.manual = self.q_prefix is not None and self.d_prefix is not None
        if not self.manual and not ("query" in prompts and "document" in prompts):
            raise RuntimeError(f"model.prompts={list(prompts)} thiếu query/document: đặt QUERY_PREFIX và "
                               "DOC_PREFIX trong starter/.env theo model card (không đoán)")
        self.prompts = prompts

    def _encode(self, texts, kind):
        if self.manual:
            pre = self.q_prefix if kind == "query" else self.d_prefix
            vecs = self.model.encode([pre + t for t in texts], batch_size=EMBEDDING_BATCH,
                                     normalize_embeddings=True, show_progress_bar=False)
        else:
            fn = self.model.encode_query if kind == "query" else self.model.encode_document
            vecs = fn(texts, batch_size=EMBEDDING_BATCH, normalize_embeddings=True, show_progress_bar=False)
        return [[float(x) for x in v] for v in vecs]

    def embed_documents(self, texts): return self._encode(texts, "document")
    def embed_query(self, question): return self._encode([question], "query")[0]

    def count_tokens(self, text):
        try:
            return len(self.model.tokenizer.encode(text, add_special_tokens=False))
        except Exception:
            return None

    def describe(self):
        import importlib.metadata as md
        return {"model": self.model_name, "dimensions": self.dimensions, "normalize": "L2",
                "query_prompt": self.q_prefix if self.manual else self.prompts.get("query"),
                "document_prompt": self.d_prefix if self.manual else self.prompts.get("document"),
                "sentence_transformers": md.version("sentence-transformers")}


def make_embedder():
    return MyEmbedder()