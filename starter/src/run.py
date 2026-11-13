"""Chạy từ starter/:
  python -m src.run info | ingest [--force] | evaluate --split dev|test [--confirm-frozen] | audit | report"""
from __future__ import annotations
import argparse, csv, json, platform, random, statistics, time
from datetime import datetime, timezone
from pathlib import Path

from . import evaluation as ev
from .chunking import chunk_page
from .config import AUDIT, CHROMA_DIR, EXPERIMENT_LOG, INDEXED, RESULTS, STRATEGIES, TOP_K
from .corpus import load_benchmark, load_units
from .embeddings import make_embedder
from .store import ChromaStore

TRACES = RESULTS / "traces"


def now(): return datetime.now(timezone.utc).isoformat(timespec="seconds")


def lib_versions():
    import importlib.metadata as md
    out = {}
    for p in ("chromadb", "sentence-transformers", "torch", "numpy", "transformers"):
        try: out[p] = md.version(p)
        except Exception: out[p] = None
    return out


def cmd_info(_a):
    emb = make_embedder(); store = ChromaStore(CHROMA_DIR, emb.dimensions)
    info = {"run_at": now(), "python": platform.python_version(), "platform": platform.platform(),
            "libs": lib_versions(), "embedder": emb.describe(),
            "vector_store": {"name": "Chroma PersistentClient", "path": str(CHROMA_DIR), "metric": "cosine",
                             "search": "HNSW (approximate)",
                             "space_reported_by_chroma": {STRATEGIES[s]["collection"]: store.space_info(STRATEGIES[s]["collection"]) for s in INDEXED}},
            "cost_usd": 0, "seed": "không áp dụng (pipeline xác định)"}
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "run_info.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(info, ensure_ascii=False, indent=2))
    print("\n>>> 'space_reported_by_chroma' phải chứa 'cosine'.")


def _len_stats(l):
    s = sorted(l)
    return {"min": s[0], "p25": s[len(s) // 4], "median": statistics.median(s), "mean": round(statistics.mean(s), 1),
            "p90": s[int(len(s) * 0.9) - 1], "max": s[-1]}


def cmd_ingest(args):
    units = load_units(); emb = make_embedder(); store = ChromaStore(CHROMA_DIR, emb.dimensions)
    RESULTS.mkdir(parents=True, exist_ok=True)
    sp = RESULTS / "ingest_stats.json"
    stats = json.loads(sp.read_text()) if sp.exists() else {}
    for strat in INDEXED:
        cfg = STRATEGIES[strat]; col = cfg["collection"]; t0 = time.time()
        if args.force: store.reset(col)
        by_src = {u.document_id: chunk_page(cfg, u) for u in units}
        chunk_secs = time.time() - t0
        existing, before = store.source_hashes(col), store.count(col)
        changed = [sid for sid, cs in by_src.items() if existing.get(sid) != cs[0].metadata["content_hash"]]
        obsolete = [sid for sid in existing if sid not in by_src]
        removed = store.delete_sources(col, obsolete + [s for s in changed if s in existing])
        todo = [c for sid in changed for c in by_src[sid]]
        t1 = time.time()
        for i in range(0, len(todo), 64):
            b = todo[i:i + 64]
            store.upsert(col, b, emb.embed_documents([c.text for c in b]))
            print(f"[{strat}] embedded {min(i + 64, len(todo))}/{len(todo)}", flush=True)
        embed_secs = time.time() - t1
        after = store.count(col); all_chunks = [c for cs in by_src.values() for c in cs]
        if after != len(all_chunks):
            raise RuntimeError(f"[{strat}] store có {after} chunk, kỳ vọng {len(all_chunks)}")
        run = {"run_at": now(), "strategy": strat, "collection": col, "sources_total": len(by_src),
               "sources_embedded": len(changed), "sources_unchanged": len(by_src) - len(changed),
               "obsolete_sources_deleted": len(obsolete), "chunks_removed": removed, "chunks_before": before,
               "chunks_after": after, "chunk_seconds": round(chunk_secs, 2), "embed_store_seconds": round(embed_secs, 2),
               "cost_usd": 0, "forced_rebuild": bool(args.force)}
        with (RESULTS / "ingest_log.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(run, ensure_ascii=False) + "\n")
        print(json.dumps(run, ensure_ascii=False))
        toks = [t for t in (emb.count_tokens(c.text) for c in all_chunks) if t is not None]
        s = stats.get(strat, {})
        s.update({"strategy": strat, "params": dict(cfg), "chunks": len(all_chunks),
                  "chars_total": sum(len(c.text) for c in all_chunks),
                  "length_chars": _len_stats([len(c.text) for c in all_chunks]),
                  "tokens_total": sum(toks) if toks else None})
        if len(changed) == len(by_src):
            s["ingest_seconds_full"] = round(chunk_secs + embed_secs, 2); s["ingest_run_at"] = now()
        stats[strat] = s
    stats["C"] = {"strategy": "C", "note": "C dùng lại index của B; chỉ khác filter khi truy xuất.",
                  "chunks": stats["B"]["chunks"], "ingest_seconds_full": 0}
    sp.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")


def cmd_evaluate(args):
    if args.split == "test" and not args.confirm_frozen:
        raise SystemExit("Chạy test cần --confirm-frozen: bạn đã chốt cấu hình + tiêu chí (benchmark/PROTOCOL.md) TRƯỚC khi xem test.")
    qs = [q for q in load_benchmark() if q["split"] == args.split]
    if not qs: raise SystemExit(f"Không có câu hỏi split={args.split}")
    emb = make_embedder(); store = ChromaStore(CHROMA_DIR, emb.dimensions)
    for s in INDEXED:
        if store.count(STRATEGIES[s]["collection"]) == 0:
            raise SystemExit("Collection rỗng. Chạy: python -m src.run ingest")
    TRACES.mkdir(parents=True, exist_ok=True)
    qvec = {q["id"]: emb.embed_query(q["question"]) for q in qs}       # cùng vector query cho A/B/C
    all_traces = []
    for strat, cfg in STRATEGIES.items():
        traces = []
        for q in qs:
            flt = q.get("filter") if cfg["use_filter"] else None
            traces.append(ev.build_trace(strat, q, flt, store.search(cfg["collection"], qvec[q["id"]], TOP_K, flt)))
        with (TRACES / f"trace_{strat}_{args.split}.jsonl").open("w", encoding="utf-8") as f:
            for t in traces: f.write(json.dumps(t, ensure_ascii=False) + "\n")
        all_traces += traces
    summary = ev.summarize(all_traces)
    (RESULTS / f"summary_{args.split}.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (RESULTS / f"summary_{args.split}.md").write_text(ev.summary_markdown(summary), encoding="utf-8")
    print(ev.summary_markdown(summary))
    if EXPERIMENT_LOG.exists():
        rows = list(csv.DictReader(EXPERIMENT_LOG.open(encoding="utf-8")))
        fields = list(rows[0].keys())
        for r in rows:
            s = summary.get(f"{r['strategy']}|{args.split}")
            if s: r[f"{args.split}_hit1"], r[f"{args.split}_hit3"] = f"{s['hit1']}/{s['N']}", f"{s['hit3']}/{s['N']}"
        with EXPERIMENT_LOG.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)


def _write_csv(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)


def cmd_audit(_a):
    units = sorted(load_units(), key=lambda u: u.document_id)
    rows = []
    for u in units[:10]:                       # 10 đơn vị đầu (đã sắp xếp), vị trí = giữa văn bản
        pos = len(u.text) // 2
        for strat in INDEXED:
            cs = chunk_page(STRATEGIES[strat], u)
            c = next((c for c in cs if c.metadata["char_start"] <= pos < c.metadata["char_end"]), None) \
                or min(cs, key=lambda c: abs(c.metadata["char_start"] - pos))
            rows.append({"strategy": strat, "unit_id": u.document_id, "position": pos, "chunk_id": c.chunk_id,
                         "chunk_text": c.text, "score_0_1_2": "", "reason": "", "grader": "author"})
    random.Random(42).shuffle(rows)
    _write_csv(AUDIT / "coherence_labels.csv", ["strategy", "unit_id", "position", "chunk_id", "chunk_text", "score_0_1_2", "reason", "grader"], rows)
    print(f"Tạo coherence_labels.csv ({len(rows)} dòng). C dùng chunk của B => điểm C = điểm B.")
    traces = []
    for strat in STRATEGIES:
        p = TRACES / f"trace_{strat}_test.jsonl"
        if p.exists(): traces += [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    if not traces:
        print("Chưa có trace test. Chạy evaluate --split test trước."); return
    mrows, grows = [], []
    for t in traces:
        for h in t["hits"]:
            m = h["metadata"]
            mrows.append({"question_id": t["question_id"], "strategy": t["strategy"], "rank": h["rank"], "chunk_id": h["chunk_id"],
                          "stored_source": m.get("source"), "stored_page": m.get("page"), "stored_category": m.get("category"),
                          "stored_topic": m.get("topic"), "stored_section": m.get("section"),
                          "filter_required": json.dumps(t["filter_in_question"]), "unit_file": f"data/corpus/{m.get('source_id')}.txt",
                          "source_ok": "", "page_ok": "", "field_ok": "", "note": ""})
        top3 = "\n---\n".join(f"[rank {h['rank']} | {h['chunk_id']}]\n{h['text']}" for h in t["hits"])
        grows.append({"question_id": t["question_id"], "strategy": t["strategy"], "question": t["question"],
                      "expected_answer": t["expected_answer"], "gold_evidence": t["evidence_quote"], "top3_text": top3,
                      "score_0_1_2": "", "reason": "", "grader": "author"})
    _write_csv(AUDIT / "metadata_audit.csv", list(mrows[0].keys()), mrows)
    _write_csv(AUDIT / "grounding_labels.csv", list(grows[0].keys()), grows)
    print(f"Tạo metadata_audit.csv ({len(mrows)} dòng), grounding_labels.csv ({len(grows)} dòng).")


def _read(p): return list(csv.DictReader(p.open(encoding="utf-8-sig"))) if p.exists() else []


def cmd_report(_a):
    out = ["# Bảng số liệu (sinh tự động từ results/)\n", "## Kết quả truy xuất\n",
           "| Strategy | Split | Hit@1 (n/N) | Evidence Hit@3 (n/N) | Chunk count | Ingest (s) | Chi phí |", "|---|---|---|---|---|---|---|"]
    sp = RESULTS / "ingest_stats.json"
    stats = json.loads(sp.read_text()) if sp.exists() else {}
    for split in ("dev", "test"):
        p = RESULTS / f"summary_{split}.json"
        if p.exists():
            for v in json.loads(p.read_text()).values():
                s = stats.get(v["strategy"], {})
                out.append(f"| {v['strategy']} | {v['split']} | {v['hit1']}/{v['N']} | {v['hit3']}/{v['N']} | {s.get('chunks','?')} | {s.get('ingest_seconds_full','?')} | $0 |")
    coh, grd, mda = _read(AUDIT / "coherence_labels.csv"), _read(AUDIT / "grounding_labels.csv"), _read(AUDIT / "metadata_audit.csv")
    out += ["\n## Năm khía cạnh (nhãn thủ công)\n", "| Strategy | Coherence TB /2 (n) | Metadata đủ và đúng (n/N) | Filter tuân thủ (n/N) | Grounding 0/1/2 và TB /2 |", "|---|---|---|---|---|"]
    for strat in STRATEGIES:
        src = "B" if strat == "C" else strat
        v = [float(r["score_0_1_2"]) for r in coh if r["strategy"] == src and r["score_0_1_2"].strip()]
        coh_s = f"{round(sum(v)/len(v),2)}/2 (n={len(v)})" if v else "chưa chấm"
        done = [r for r in mda if r["strategy"] == strat and r["source_ok"].strip() and r["page_ok"].strip() and r["field_ok"].strip()]
        good = [r for r in done if all(r[k].strip().upper() in ("Y", "1", "TRUE", "ĐÚNG") for k in ("source_ok", "page_ok", "field_ok"))]
        meta_s = f"{len(good)}/{len(done)}" if done else "chưa chấm"
        p = TRACES / f"trace_{strat}_test.jsonl"
        tr = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()] if p.exists() else []
        fq = [t for t in tr if t["filter_in_question"]]
        filt_s = f"{sum(bool(t['eval']['filter_compliant']) for t in fq)}/{len(fq)}" if fq else "N/A"
        g = [int(float(r["score_0_1_2"])) for r in grd if r["strategy"] == strat and r["score_0_1_2"].strip()]
        gs = f"{g.count(0)}/{g.count(1)}/{g.count(2)}; TB {round(sum(g)/len(g),2)}/2" if g else "chưa chấm"
        out.append(f"| {strat} | {coh_s} | {meta_s} | {filt_s} | {gs} |")
    out.append("\nGhi chú: C dùng chunk của B nên coherence C = B; filter của A/B là mức tuân thủ tự nhiên (không áp filter).")
    (RESULTS / "report_tables.md").write_text("\n".join(out), encoding="utf-8")
    print("\n".join(out))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("info").set_defaults(fn=cmd_info)
    p = sub.add_parser("ingest"); p.add_argument("--force", action="store_true"); p.set_defaults(fn=cmd_ingest)
    p = sub.add_parser("evaluate"); p.add_argument("--split", choices=["dev", "test"], required=True)
    p.add_argument("--confirm-frozen", action="store_true"); p.set_defaults(fn=cmd_evaluate)
    sub.add_parser("audit").set_defaults(fn=cmd_audit)
    sub.add_parser("report").set_defaults(fn=cmd_report)
    a = ap.parse_args(); a.fn(a)


if __name__ == "__main__":
    main()