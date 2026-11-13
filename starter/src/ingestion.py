from __future__ import annotations
import re, unicodedata
from pathlib import Path
from .models import DocumentPage

ADMONITIONS = {"note", "warning", "tip", "seealso", "important", "attention", "caution", "danger", "hint", "error"}
DROP_BLOCK = {"toctree", "image", "figure", "youtube", "video", "contents", "meta", "include", "rst-class",
              "index", "raw", "only", "csv-table", "list-table", "literalinclude"}
CODE_DIRECTIVES = {"code-block", "code", "sourcecode", "highlight"}
UNDERLINE = re.compile(r'^([!-/:-@\[-`{-~])\1{2,}\s*$')
DIRECTIVE = re.compile(r'^(\s*)\.\. ([\w-]+)::\s*(.*)$')
ROLE_WITH_TARGET = re.compile(r':[\w:+-]+:`([^`<]*?)\s*<[^>]*>`')
ROLE_PLAIN = re.compile(r':[\w:+-]+:`([^`]+)`')
LINK = re.compile(r'`([^`<]+?)\s*<[^>]+>`_{1,2}')


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\u00a0", " ").replace("\t", "    ")
    text = "".join(ch for ch in text if ch == "\n" or unicodedata.category(ch)[0] != "C")
    out, blank = [], False
    for ln in (l.rstrip() for l in text.split("\n")):
        if not ln.strip():
            if out and not blank:
                out.append("")
            blank = True
        else:
            out.append(ln); blank = False
    return "\n".join(out).strip()


def _inline(line: str) -> str:
    line = ROLE_WITH_TARGET.sub(r'\1', line)
    line = ROLE_PLAIN.sub(lambda m: m.group(1).lstrip('~!'), line)
    line = LINK.sub(r'\1', line)
    line = re.sub(r'\*\*([^*]+)\*\*', r'\1', line)
    line = re.sub(r'(?<![\w*])\*([^*\s][^*]*)\*(?![\w*])', r'\1', line)
    line = line.replace('``', '')
    return re.sub(r'\|[\w-]+\|', '', line)


def _indent(s: str) -> int:
    return len(s) - len(s.lstrip(' '))


def rst_to_text(raw: str) -> str:
    lines = normalize_text(raw).split("\n")
    out, styles, i, n, literal_next = [], [], 0, len(lines), False
    while i < n:
        ln = lines[i]; s = ln.strip()
        m = DIRECTIVE.match(ln)
        if m:                                                  # directive (.. note::, .. code-block:: ...)
            ind, name, arg = len(m.group(1)), m.group(2).lower(), m.group(3).strip()
            j, block = i + 1, []
            while j < n and (not lines[j].strip() or _indent(lines[j]) > ind):
                block.append(lines[j]); j += 1
            if name in DROP_BLOCK:
                i = j; continue
            body = [b for b in block if not re.match(r'^\s*:[\w-]+:', b)]
            nonempty = [b for b in body if b.strip()]
            cut = min((_indent(b) for b in nonempty), default=0)
            body = [b[cut:] if b.strip() else "" for b in body]
            if name in CODE_DIRECTIVES:
                out.append(""); out.extend(body); out.append("")
            elif name in ADMONITIONS:
                inner = rst_to_text("\n".join(body)).split("\n") if nonempty else []
                label = f"{name.capitalize()}:"
                out.append("")
                if arg:
                    out.append(f"{label} {_inline(arg)}"); out.extend(inner)
                else:
                    k = next((x for x, t in enumerate(inner) if t.strip()), None)
                    if k is not None:
                        inner[k] = f"{label} {inner[k]}"
                    out.extend(inner)
                out.append("")
            else:
                out.append("")
                if nonempty:
                    out.extend(rst_to_text("\n".join(body)).split("\n"))
                out.append("")
            i = j; continue
        if s.startswith(".. ") or s == "..":                    # comment / anchor
            ind, j = _indent(ln), i + 1
            while j < n and (not lines[j].strip() or _indent(lines[j]) > ind):
                j += 1
            i = j; continue
        if re.match(r'^\s*\+[-=+]+\+\s*$', ln) or re.match(r'^=+(\s+=+)+\s*$', s):   # viền bảng
            i += 1; continue
        if s.startswith("|") and s.endswith("|") and len(s) > 2:
            cells = [c.strip() for c in s.strip("|").split("|") if c.strip()]
            out.append(" | ".join(_inline(c) for c in cells)); i += 1; continue
        if s and not UNDERLINE.match(s) and i + 1 < n and UNDERLINE.match(lines[i + 1].strip()) \
                and len(lines[i + 1].strip()) >= len(s):         # heading
            key = lines[i + 1].strip()[0]
            if i > 0 and UNDERLINE.match(lines[i - 1].strip()):
                key = "over" + key
            if key not in styles:
                styles.append(key)
            out.extend(["", "#" * min(styles.index(key) + 1, 6) + " " + _inline(s), ""])
            i += 2; continue
        if UNDERLINE.match(s) and i + 2 < n and lines[i + 1].strip() and UNDERLINE.match(lines[i + 2].strip()):
            i += 1; continue
        if UNDERLINE.match(s):
            i += 1; continue
        if literal_next:                                         # khối code sau "::"
            if not s:
                out.append(""); i += 1; continue
            if _indent(ln) > 0:
                j, blk = i, []
                while j < n and (not lines[j].strip() or _indent(lines[j]) > 0):
                    blk.append(lines[j]); j += 1
                nonempty = [b for b in blk if b.strip()]
                cut = min((_indent(b) for b in nonempty), default=0)
                out.extend(b[cut:] if b.strip() else "" for b in blk)
                literal_next = False; i = j; continue
            literal_next = False
        if s.endswith("::"):
            literal_next = True
            s2 = s[:-2].rstrip()
            out.append(_inline((s2 + ":") if s2 else "")); i += 1; continue
        out.append(_inline(ln.strip())); i += 1
    return normalize_text("\n".join(out))


def load_rst(path: Path, document_id: str, source: str) -> DocumentPage:
    return DocumentPage(document_id=document_id, source=source, page=document_id,
                        text=rst_to_text(path.read_text(encoding="utf-8")))


def first_heading(text: str) -> str:
    m = re.search(r'^#{1,6} (.+)$', text, re.M)
    return m.group(1).strip() if m else ""


def count_headings(text: str) -> int:
    return len(re.findall(r'^#{1,6} .+$', text, re.M))