import argparse, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.corpus import load_manifest, load_units

ap = argparse.ArgumentParser()
ap.add_argument("unit", nargs="?"); ap.add_argument("--list", action="store_true"); ap.add_argument("--grep")
a = ap.parse_args()
if a.list:
    for s in load_manifest()["sources"]:
        print(f"{s['source_id']:70s} topic={s['topic']:14s} {s['char_count']:6d}")
elif a.grep:
    rx = re.compile(a.grep, re.I)
    for u in load_units():
        for ln, line in enumerate(u.text.split("\n"), 1):
            if rx.search(line):
                print(f"{u.document_id}:{ln}: {line[:160]}")
elif a.unit:
    u = next((u for u in load_units() if u.document_id == a.unit), None)
    for ln, line in enumerate(u.text.split("\n"), 1):
        print(f"{ln:4d}  {line}")