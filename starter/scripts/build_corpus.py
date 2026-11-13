"""Tạo corpus + manifest từ bản clone godot-docs.
  python scripts/build_corpus.py --docs-dir ../../godot-docs --list-dirs
  python scripts/build_corpus.py --docs-dir ../../godot-docs
Quy tắc chọn: mỗi thư mục trong --dirs, sắp xếp theo đường dẫn, lấy tối đa --per-dir file .rst hợp lệ đầu tiên
(không phải index.rst / file '_*', >= 1500 ký tự sau chuẩn hóa). 1 file = 1 đơn vị (page = source_id)."""
import argparse, csv, json, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.config import CORPUS_DIR, MANIFEST, MIN_UNIT_CHARS, MIN_UNITS, RESULTS, ROOT
from src.ingestion import count_headings, first_heading, rst_to_text

DEFAULT_DIRS = ["tutorials/2d", "tutorials/3d", "tutorials/physics", "tutorials/scripting",
                "tutorials/inputs", "getting_started/step_by_step"]
ATTRIBUTION = "Juan Linietsky, Ariel Manzur and the Godot community"


def git(docs, *args):
    try:
        return subprocess.run(["git", "-C", str(docs), *args], capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return "unknown"


def evaluate_file(path, min_chars):
    if path.name == "index.rst" or path.name.startswith("_"):
        return "excluded", "index/toctree file", ""
    try:
        text = rst_to_text(path.read_text(encoding="utf-8"))
    except Exception as e:
        return "error", f"đọc lỗi: {e}", ""
    if len(text) < min_chars:
        return "excluded", f"quá ngắn ({len(text)} < {min_chars})", text
    return "included", "ok", text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--docs-dir", type=Path, required=True)
    ap.add_argument("--dirs", nargs="+", default=DEFAULT_DIRS)
    ap.add_argument("--per-dir", type=int, default=6)
    ap.add_argument("--min-chars", type=int, default=MIN_UNIT_CHARS)
    ap.add_argument("--list-dirs", action="store_true")
    a = ap.parse_args()
    docs = a.docs_dir.resolve()
    if not docs.is_dir():
        sys.exit(f"Không thấy {docs}")
    if a.list_dirs:
        skip = {"classes", "_static", "_extensions", ".git", "img"}
        for top in sorted(p for p in docs.iterdir() if p.is_dir() and p.name not in skip):
            for sub in sorted(p for p in top.iterdir() if p.is_dir()):
                n = sum(evaluate_file(f, a.min_chars)[0] == "included" for f in sub.glob("*.rst"))
                if n:
                    print(f"{sub.relative_to(docs).as_posix():55s} {n:3d} file hợp lệ")
        return
    commit, branch = git(docs, "rev-parse", "HEAD"), git(docs, "branch", "--show-current")
    commit_date, remote = git(docs, "show", "-s", "--format=%cI"), git(docs, "remote", "get-url", "origin")
    accessed = datetime.now(timezone.utc).isoformat(timespec="seconds")
    sources, log = [], []
    for d in a.dirs:
        base = docs / d
        if not base.is_dir():
            print(f"[CẢNH BÁO] không có thư mục {d}", file=sys.stderr); continue
        taken = 0
        for f in sorted(base.glob("*.rst")):
            rel = f.relative_to(docs)
            status, reason, text = evaluate_file(f, a.min_chars)
            if status == "included" and taken >= a.per_dir:
                status, reason = "excluded", f"vượt --per-dir={a.per_dir}"
            log.append({"path": rel.as_posix(), "status": status, "reason": reason, "chars": len(text)})
            if status != "included":
                continue
            taken += 1
            sid = rel.with_suffix("").as_posix().replace("/", "--")
            sources.append({
                "source_id": sid, "title": first_heading(text) or f.stem, "source_path": rel.as_posix(),
                "source_url": f"https://github.com/godotengine/godot-docs/blob/{commit}/{rel.as_posix()}",
                "source_path_or_url": rel.as_posix(),
                "license_or_permission": f"CC BY 3.0 (godot-docs, trừ classes/); ghi công: {ATTRIBUTION}",
                "accessed_at": accessed, "page_ids": [sid], "char_count": len(text),
                "heading_count": count_headings(text), "category": rel.parts[0],
                "topic": rel.parts[1] if len(rel.parts) > 2 else rel.parts[0], "text": text})
    if len(sources) < MIN_UNITS:
        sys.exit(f"Chỉ có {len(sources)} đơn vị hợp lệ (< {MIN_UNITS}). Thêm --dirs hoặc tăng --per-dir.")
    CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    keep = {s["source_id"] + ".txt" for s in sources}
    for old in CORPUS_DIR.glob("*.txt"):
        if old.name not in keep:
            old.unlink()
    for s in sources:
        (CORPUS_DIR / f"{s['source_id']}.txt").write_text(s.pop("text"), encoding="utf-8", newline="\n")
    manifest = {
        "corpus": "Godot Engine documentation (godot-docs, .rst)",
        "snapshot": {"repo": remote, "branch": branch, "commit": commit, "commit_date": commit_date},
        "license": "CC BY 3.0 (trừ classes/; classes/ không dùng)", "attribution": ATTRIBUTION,
        "selection_rule": f"dirs={a.dirs}; sắp xếp theo đường dẫn; tối đa {a.per_dir}/thư mục; loại index.rst, file '_*', file < {a.min_chars} ký tự",
        "page_counting_rule": f"RST không phân trang: 1 file .rst hợp lệ = 1 đơn vị nguồn độc lập (page = source_id), >= {a.min_chars} ký tự đã chuẩn hóa; không nhân bản.",
        "metadata_fields": {"category": "thư mục cấp 1 (từ đường dẫn)", "topic": "thư mục cấp 2 (từ đường dẫn)",
                            "section": "heading gần nhất (từ nội dung)"},
        "total_units": len(sources), "total_chars": sum(s["char_count"] for s in sources), "sources": sources}
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (ROOT / "data" / "ATTRIBUTION.md").write_text(
        f"# Ghi công dữ liệu\n\nNguồn: godot-docs ({remote}), commit `{commit}`, branch `{branch}`.\n"
        f"Giấy phép: CC BY 3.0, ghi công \"{ATTRIBUTION}\".\n"
        "Thay đổi: .rst được chuyển thành văn bản thuần đã chuẩn hóa; không đổi ý nghĩa.\n", encoding="utf-8")
    RESULTS.mkdir(parents=True, exist_ok=True)
    with (RESULTS / "corpus_log.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["path", "status", "reason", "chars"]); w.writeheader(); w.writerows(log)
    topics = {}
    for s in sources:
        topics[s["topic"]] = topics.get(s["topic"], 0) + 1
    print(f"OK: {len(sources)} đơn vị, {manifest['total_chars']} ký tự, commit {commit[:10]}")
    print("Theo topic:", topics)


if __name__ == "__main__":
    main()