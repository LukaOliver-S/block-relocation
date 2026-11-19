"""Convert BRP JSON instance files into the .txt format read by brp.

Usage: python scripts/json2dat.py <folder with brp_*.json> <output folder>

One file per instance, e.g. brp_W3_H4_N8_id1.txt:
    W H N
    <height> <item> <item> ...      one line per stack, bottom -> top
Run brp with -maxHeight file to use the H from the header.
"""
import json
import pathlib
import sys

src = pathlib.Path(sys.argv[1])
dst = pathlib.Path(sys.argv[2])
dst.mkdir(parents=True, exist_ok=True)

count = 0
for f in sorted(src.glob("brp_*.json")):
    d = json.load(open(f, encoding="utf-8"))
    W, H, N = d["metadata"]["W"], d["metadata"]["H"], d["metadata"]["N"]
    for inst in d["instancias"]:
        assert len(inst["stacks"]) == W
        lines = [f"{W} {H} {N}"]
        for p in inst["stacks"]:
            lines.append(" ".join([str(len(p))] + [str(c) for c in p]))
        (dst / f"{f.stem}_id{inst['id']}.txt").write_text(
            "\n".join(lines) + "\n")
        count += 1
print(f"{count} instances written to {dst}")
