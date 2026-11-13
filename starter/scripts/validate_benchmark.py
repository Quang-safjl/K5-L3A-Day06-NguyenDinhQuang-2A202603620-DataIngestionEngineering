import re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.corpus import load_benchmark, load_manifest, load_units
from src.evaluation import gold_list, norm

REQ = ["id", "split", "question", "expected_answer", "gold_source_id", "gold_page", "evidence_quote"]
errors, warns = [], []
qs, man = load_benchmark(), load_manifest()
meta = {s["source_id"]: s for s in man["sources"]}
text = {u.document_id: norm(u.text) for u in load_units()}
ids = [q.get("id") for q in qs]
if len(ids) != len(set(ids)):
    errors.append("id bị trùng")
for q in qs:
    qid = q.get("id", "?")
    for k in REQ:
        if not str(q.get(k, "")).strip():
            errors.append(f"{qid}: thiếu {k}")
    if q.get("split") not in ("dev", "test"):
        errors.append(f"{qid}: split phải là dev|test")
    if all(k in q for k in ("gold_source_id", "evidence_quote")):
        for sid, quote in gold_list(q):
            if sid not in meta:
                errors.append(f"{qid}: '{sid}' không có trong manifest"); continue
            if norm(quote) not in text[sid]:
                errors.append(f"{qid}: evidence_quote KHÔNG nằm trong {sid}")
            if re.search(r"^#{1,6} ", quote, re.M):
                errors.append(f"{qid}: evidence_quote chứa dòng heading")
            if len(quote) > 450:
                warns.append(f"{qid}: evidence dài ({len(quote)}), chunk A (500) dễ cắt đôi")
    flt = q.get("filter")
    if flt:
        for k, v in flt.items():
            if k not in ("category", "topic"):
                errors.append(f"{qid}: filter chỉ dùng category/topic")
            elif q.get("gold_source_id") in meta and meta[q["gold_source_id"]][k] != v:
                errors.append(f"{qid}: nguồn gold có {k}={meta[q['gold_source_id']][k]} nhưng filter đòi {v}")
    if q.get("gold_source_id", "\0") in q.get("question", ""):
        warns.append(f"{qid}: câu hỏi chứa gold_source_id (rò rỉ)")
dev, test = [q for q in qs if q.get("split") == "dev"], [q for q in qs if q.get("split") == "test"]
fl = [q for q in qs if q.get("filter")]
if len(qs) < 20: errors.append(f"Cần >=20 câu (có {len(qs)})")
if len(dev) < 15: errors.append(f"Cần >=15 dev (có {len(dev)})")
if len(test) < 5: errors.append(f"Cần >=5 test (có {len(test)})")
if len(fl) < 3: errors.append(f"Cần >=3 câu filter (có {len(fl)})")
if not any(q["split"] == "test" for q in fl): errors.append("Cần >=1 câu filter thuộc test")
print(f"Tổng {len(qs)} | dev {len(dev)} | test {len(test)} | filter {len(fl)}")
for w in warns: print("[CẢNH BÁO]", w)
for e in errors: print("[LỖI]", e)
print("\nBenchmark HỢP LỆ" if not errors else f"\n{len(errors)} lỗi cần sửa")
sys.exit(1 if errors else 0)