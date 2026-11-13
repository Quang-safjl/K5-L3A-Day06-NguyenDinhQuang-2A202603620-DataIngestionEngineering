import json
from .config import BENCHMARK, CORPUS_DIR, MANIFEST
from .models import DocumentPage

def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))

def load_units() -> list[DocumentPage]:
    units = []
    for s in sorted(load_manifest()["sources"], key=lambda x: x["source_id"]):
        text = (CORPUS_DIR / f"{s['source_id']}.txt").read_text(encoding="utf-8")
        if len(text) != s["char_count"]:
            raise ValueError(f"{s['source_id']}: số ký tự khác manifest. Chạy lại build_corpus.py")
        meta = {"document_id": s["source_id"], "source": s["source_path"], "page": s["source_id"],
                "category": s["category"], "topic": s["topic"]}
        units.append(DocumentPage(s["source_id"], s["source_path"], s["source_id"], text, meta))
    return units

def load_benchmark() -> list[dict]:
    rows = []
    for ln, line in enumerate(BENCHMARK.read_text(encoding="utf-8").splitlines(), 1):
        if line.strip():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ValueError(f"{BENCHMARK}:{ln} JSON lỗi: {e}") from e
    return rows