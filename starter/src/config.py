import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / "starter" / ".env")

CORPUS_DIR = ROOT / "data" / "corpus"
MANIFEST = ROOT / "data" / "manifest.json"
CHROMA_DIR = ROOT / "data" / "chroma"
BENCHMARK = ROOT / "benchmark" / "questions.jsonl"
RESULTS = ROOT / "results"
AUDIT = RESULTS / "audit"
EXPERIMENT_LOG = ROOT / "artifacts" / "experiment_log.csv"

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL") or "google/embeddinggemma-2"
EMBEDDING_BATCH = int(os.getenv("EMBEDDING_BATCH", "16"))

# C dùng lại index của B (chỉ khác: có filter khi câu hỏi có filter)
STRATEGIES = {
    "A": {"chunker": "fixed", "size": 500, "overlap": 50, "collection": "godot_A", "use_filter": False},
    "B": {"chunker": "heading", "max_size": 1200, "min_section": 150, "collection": "godot_B", "use_filter": False},
    "C": {"chunker": "heading", "max_size": 1200, "min_section": 150, "collection": "godot_B", "use_filter": True},
}
INDEXED = ["A", "B"]
TOP_K = 3
MIN_UNIT_CHARS = 1500
MIN_UNITS = 30