from __future__ import annotations
import hashlib, re
from .models import Chunk, DocumentPage

HEADING = re.compile(r'^(#{1,6}) (.+)$')


def _base_meta(page):
    meta = dict(page.metadata)
    meta["content_hash"] = hashlib.sha256(page.text.encode("utf-8")).hexdigest()[:16]
    return meta


def _headings(text):
    out, pos = [], 0
    for block in text.split("\n\n"):
        m = HEADING.match(block)
        if m and "\n" not in block:
            out.append((pos, len(m.group(1)), m.group(2).strip()))
        pos += len(block) + 2
    return out


def _section_at(heads, pos):
    stack = []
    for p, lvl, title in heads:
        if p > pos:
            break
        while stack and stack[-1][0] >= lvl:
            stack.pop()
        stack.append((lvl, title))
    return (stack[-1][1] if stack else ""), " > ".join(t for _, t in stack)


def _mk(strategy, page, idx, text, start, end, section, section_path):
    meta = _base_meta(page)
    meta.update(strategy=strategy, source_id=page.document_id, chunk_index=idx, char_start=start,
                char_end=end, section=section, section_path=section_path, n_chars=len(text))
    return Chunk(f"{strategy}-{page.document_id}-{idx:03d}", page.document_id, page.source, page.page, text, meta)


def fixed_size(page, size=500, overlap=50):
    """A: cửa sổ ký tự cố định."""
    text, n = page.text, len(page.text)
    heads, chunks, i, idx = _headings(text), [], 0, 0
    while i < n:
        end = min(i + size, n)
        sec, path = _section_at(heads, i)
        chunks.append(_mk("A", page, idx, text[i:end], i, end, sec, path))
        idx += 1
        if end == n:
            break
        i = end - overlap
    return chunks


def _split_oversize(text, base, max_size):
    spans, last = [], 0
    for m in re.finditer(r'(?<=[.!?:;])\s+|\n', text):
        spans.append((last, m.start())); last = m.end()
    spans.append((last, len(text)))
    pieces = []
    for s, e in spans:
        while e - s > max_size:
            pieces.append((s, s + max_size)); s += max_size
        if e > s:
            pieces.append((s, e))
    packed, cs, ce = [], None, None
    for s, e in pieces:
        if cs is None:
            cs, ce = s, e
        elif e - cs <= max_size:
            ce = e
        else:
            packed.append((cs, ce)); cs, ce = s, e
    if cs is not None:
        packed.append((cs, ce))
    return [(base + s, base + e, text[s:e]) for s, e in packed]


def by_heading(page, max_size=1200, min_section=150):
    """B/C: theo heading rồi gom đoạn tới max_size; section quá ngắn gộp sang section sau."""
    text = page.text
    blocks, pos = [], 0
    for b in text.split("\n\n"):
        blocks.append((pos, pos + len(b), b)); pos += len(b) + 2
    heads = _headings(text)
    sections, cur = [], {"head": None, "blocks": []}
    for s, e, b in blocks:
        if HEADING.match(b) and "\n" not in b:
            if cur["blocks"]:
                sections.append(cur)
            cur = {"head": b, "blocks": [(s, e, b)]}
        else:
            cur["blocks"].append((s, e, b))
    if cur["blocks"]:
        sections.append(cur)
    merged, carry = [], []
    for k, sec in enumerate(sections):
        body_len = sum(len(b) for _, _, b in sec["blocks"] if not HEADING.match(b))
        if body_len < min_section and k < len(sections) - 1:
            carry.extend(sec["blocks"]); continue
        merged.append({"head": sec["head"], "blocks": carry + sec["blocks"]}); carry = []
    if carry:
        if merged:
            merged[-1]["blocks"].extend(carry)
        else:
            merged.append({"head": None, "blocks": carry})
    chunks, idx = [], 0
    for sec in merged:
        head = sec["head"]
        units = []
        for s, e, b in sec["blocks"]:
            units.extend(_split_oversize(b, s, max_size) if len(b) > max_size else [(s, e, b)])
        cur_units, cur_len = [], 0

        def flush():
            nonlocal idx, cur_units, cur_len
            if not cur_units:
                return
            body = "\n\n".join(u[2] for u in cur_units)
            first_is_head = HEADING.match(cur_units[0][2]) is not None
            ctext = body if (first_is_head or head is None) else head + "\n\n" + body
            sec_title, path = _section_at(heads, cur_units[-1][0])
            chunks.append(_mk("B", page, idx, ctext, cur_units[0][0], cur_units[-1][1], sec_title, path))
            idx += 1; cur_units, cur_len = [], 0

        for u in units:
            add = len(u[2]) + 2
            if cur_units and cur_len + add > max_size:
                flush()
            cur_units.append(u); cur_len += add
        flush()
    return chunks


def chunk_page(cfg, page):
    if cfg["chunker"] == "fixed":
        return fixed_size(page, cfg["size"], cfg["overlap"])
    if cfg["chunker"] == "heading":
        return by_heading(page, cfg["max_size"], cfg.get("min_section", 150))
    raise ValueError(cfg["chunker"])