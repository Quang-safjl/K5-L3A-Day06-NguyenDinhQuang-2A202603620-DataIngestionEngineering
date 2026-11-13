from __future__ import annotations
import re
from collections import defaultdict


def norm(s): return re.sub(r"\s+", " ", s).strip()


def gold_list(q):
    gold = [(q["gold_source_id"], q["evidence_quote"])]
    for a in q.get("alt_evidence", []) or []:
        gold.append((a["gold_source_id"], a["evidence_quote"]))
    return gold


def filter_ok(hit, flt):
    return all(hit["metadata"].get(k) == v for k, v in (flt or {}).items())


def evaluate_query(question, hits):
    """Hit = chunk thuộc nguồn gold VÀ chứa đủ evidence_quote (sau khi gộp khoảng trắng)."""
    gold = gold_list(question)
    gold_sources = {g[0] for g in gold}
    flags = []
    for h in hits:
        t, src = norm(h["text"]), h["metadata"].get("source_id")
        flags.append({"rank": len(flags) + 1, "chunk_id": h["chunk_id"], "source_hit": src in gold_sources,
                      "evidence_hit": any(src == sid and norm(q) in t for sid, q in gold)})
    return {
        "hit1": bool(flags and flags[0]["evidence_hit"]),
        "hit3": any(f["evidence_hit"] for f in flags[:3]),
        "first_hit_rank": next((f["rank"] for f in flags if f["evidence_hit"]), None),
        "source_hit1": bool(flags and flags[0]["source_hit"]),
        "source_hit3": any(f["source_hit"] for f in flags[:3]),
        "per_rank": flags,
        "evidence_split_suspect": any(f["source_hit"] for f in flags) and not any(f["evidence_hit"] for f in flags),
        "filter_compliant": (all(filter_ok(h, question.get("filter")) for h in hits) if question.get("filter") else None),
    }


def build_trace(strategy, question, applied_filter, hits):
    return {"strategy": strategy, "question_id": question["id"], "split": question["split"],
            "question": question["question"], "filter_in_question": question.get("filter"),
            "filter_applied": applied_filter, "gold_source_id": question["gold_source_id"],
            "gold_page": question["gold_page"], "evidence_quote": question["evidence_quote"],
            "alt_evidence": question.get("alt_evidence"), "expected_answer": question.get("expected_answer"),
            "hits": [{"rank": i + 1, "chunk_id": h["chunk_id"], "score": h["score"], "text": h["text"],
                      "metadata": h["metadata"]} for i, h in enumerate(hits)],
            "eval": evaluate_query(question, hits)}


def summarize(traces):
    groups = defaultdict(list)
    for t in traces:
        groups[(t["strategy"], t["split"])].append(t)
        if t["filter_in_question"]:
            groups[(t["strategy"], t["split"] + "/filter-only")].append(t)
    out = {}
    for (strat, split), ts in sorted(groups.items()):
        out[f"{strat}|{split}"] = {
            "strategy": strat, "split": split, "N": len(ts),
            "hit1": sum(t["eval"]["hit1"] for t in ts), "hit3": sum(t["eval"]["hit3"] for t in ts),
            "source_hit1": sum(t["eval"]["source_hit1"] for t in ts),
            "source_hit3": sum(t["eval"]["source_hit3"] for t in ts),
            "evidence_split_suspects": [t["question_id"] for t in ts if t["eval"]["evidence_split_suspect"]],
            "failed_hit3": [t["question_id"] for t in ts if not t["eval"]["hit3"]]}
    return out


def summary_markdown(summary):
    rows = ["| Strategy | Split | Hit@1 (n/N) | Evidence Hit@3 (n/N) | Source@3 (n/N) | Câu trượt Hit@3 |",
            "|---|---|---|---|---|---|"]
    for v in summary.values():
        rows.append(f"| {v['strategy']} | {v['split']} | {v['hit1']}/{v['N']} | {v['hit3']}/{v['N']} | "
                    f"{v['source_hit3']}/{v['N']} | {', '.join(v['failed_hit3']) or '-'} |")
    return "\n".join(rows)