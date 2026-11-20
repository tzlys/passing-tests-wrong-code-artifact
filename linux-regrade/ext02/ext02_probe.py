"""EXT-02 Stage 0: format probe. Lists trajs/ per entry; downloads ONE object per entry and prints only its structure.
Computes no metric. Usage: python3 ext02_probe.py OUTDIR"""
import json
import os
import re
import sys
from collections import Counter

from ext02_common import download, entries, list_objects, sample

MASK = re.compile(r"[A-Za-z0-9]+")


def shape(v, path, out, depth=0):
    if depth > 7 or len(out) > 400:
        return
    if isinstance(v, dict):
        out.append(f"{path} : dict[{len(v)}] keys={sorted(v)[:40]}")
        for k in sorted(v)[:40]:
            shape(v[k], f"{path}.{k}", out, depth + 1)
    elif isinstance(v, list):
        out.append(f"{path} : list[{len(v)}]")
        if v:
            shape(v[0], f"{path}[0]", out, depth + 1)
            if len(v) > 1 and type(v[1]) != type(v[0]):
                shape(v[1], f"{path}[1]", out, depth + 1)
    elif isinstance(v, str):
        first = v.strip().split(None, 1)[0][:20] if v.strip() else ""
        out.append(f"{path} : str[{len(v)}] first_word={MASK.sub('x', first) if len(first) > 12 else first!r}")
    else:
        out.append(f"{path} : {type(v).__name__}")


def structure(raw):
    text = raw.decode("utf-8", "replace")
    try:
        obj = json.loads(text)
        out = []
        shape(obj, "$", out)
        return "JSON\n" + "\n".join(out)
    except Exception:
        pass
    lines = text.splitlines()
    try:
        objs = [json.loads(l) for l in lines[:50] if l.strip()]
        out = []
        for i, o in enumerate(objs[:3]):
            shape(o, f"$line{i}", out)
        return f"JSONL ({len(lines)} lines)\n" + "\n".join(out)
    except Exception:
        pass
    out = []
    for l in lines[:60]:
        parts = l.split(None, 1)
        head = parts[0][:24] if parts else ""
        tail = MASK.sub("x", parts[1])[:100] if len(parts) > 1 else ""
        out.append(f"{head} {tail}")
    return f"TEXT ({len(lines)} lines)\n" + "\n".join(out)


def main(outdir):
    os.makedirs(outdir, exist_ok=True)
    summary = {}
    for e in entries():
        prefix = f"lite/{e}/trajs/"
        try:
            objs = list_objects(prefix)
        except Exception as ex:
            summary[e] = {"error": repr(ex)}
            print(e, "LIST ERROR", ex, flush=True)
            continue
        exts = Counter(os.path.basename(k).split(".", 1)[1] if "." in os.path.basename(k) else "" for k, _ in objs)
        chosen, too_large, n_inst = sample(e, objs)
        rec = {"objects": len(objs), "instances": n_inst, "ext": dict(exts.most_common(8)),
               "too_large_in_sample": too_large,
               "bytes_total": sum(s for _, s in objs)}
        first = next((v[0] for v in chosen.values() if v), None)
        if first:
            rec["probe_key"] = first[0]
            raw = download(first[0])
            with open(os.path.join(outdir, f"structure-{e}.txt"), "w") as f:
                f.write(first[0] + "\n" + structure(raw))
        summary[e] = rec
        print(e, rec.get("objects"), "objects", rec.get("instances"), "instances", rec.get("ext"), flush=True)
    with open(os.path.join(outdir, "probe-summary.json"), "w") as f:
        json.dump(summary, f, indent=1)
    print("wrote", outdir)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "ext02-probe")
