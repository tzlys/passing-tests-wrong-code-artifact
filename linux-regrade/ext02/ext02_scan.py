"""EXT-02 Stage 1: download the fixed sample, extract agent actions (ext02_extract.py), apply fixed metrics.
Usage: python3 ext02_scan.py OUTDIR"""
import json
import math
import os
import random
import sys
from concurrent.futures import ThreadPoolExecutor

from ext02_common import download, entries, list_objects, sample
from ext02_metrics import analyze_trajectory
import ext02_extract


def wilson(k, n, z=1.96):
    if n == 0:
        return (None, None)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(c - h, 3), round(c + h, 3))


def fetch(args):
    key, cache = args
    path = os.path.join(cache, key.replace("/", "__"))
    if not os.path.exists(path):
        data = download(key)
        with open(path + ".part", "wb") as f:
            f.write(data)
        os.replace(path + ".part", path)
    with open(path, "rb") as f:
        return key, f.read()


def main(outdir):
    cache = os.path.join(outdir, "cache")
    os.makedirs(cache, exist_ok=True)
    rows, excl = [], {"no_trajs": [], "too_large": 0, "unparseable": 0, "no_actions": 0, "no_T": 0}
    for e in entries():
        objs = list_objects(f"lite/{e}/trajs/")
        if not objs:
            excl["no_trajs"].append(e)
            print(e, "no trajs", flush=True)
            continue
        chosen, too_large, _ = sample(e, objs)
        excl["too_large"] += too_large
        keys = [(k, cache) for v in chosen.values() for k, _ in v]
        with ThreadPoolExecutor(8) as ex:
            data = dict(ex.map(fetch, keys))
        for inst, objs_i in chosen.items():
            actions, parsed_any, unparseable = [], False, False
            for k, _ in objs_i:
                try:
                    a = ext02_extract.extract(e, k, data[k])
                except Exception:
                    a, unparseable = None, True
                if a is not None:
                    parsed_any = True
                    actions.extend(a)
            row = {"entry": e, "instance": inst, "files": len(objs_i), "parsed": parsed_any, "n_actions": len(actions)}
            if not parsed_any:
                excl["unparseable" if unparseable else "no_actions"] += 1
            elif not actions:
                excl["no_actions"] += 1
            else:
                r = analyze_trajectory(actions)
                row.update({k: r[k] for k in ("T", "M1", "M2", "M3")})
                row.update({k: r[k][:5] for k in ("M1_lines", "M2_lines", "M3_lines")})
                if not r["T"]:
                    excl["no_T"] += 1
            rows.append(row)
        print(e, len(chosen), "instances", sum(1 for r in rows if r["entry"] == e and r.get("T")), "with T", flush=True)

    with open(os.path.join(outdir, "per-trajectory.jsonl"), "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    withT = [r for r in rows if r.get("T")]
    withA = [r for r in rows if "T" in r]
    summ = {"exclusions": excl, "trajectories_with_actions": len(withA), "trajectories_with_T": len(withT), "metrics": {}}
    for m, base in (("M1", withT), ("M2", withT), ("M3", withA)):
        k = sum(1 for r in base if r[m])
        per = {}
        for e in sorted({r["entry"] for r in base}):
            b = [r for r in base if r["entry"] == e]
            per[e] = [sum(1 for r in b if r[m]), len(b)]
        props = sorted(v[0] / v[1] for v in per.values() if v[1])
        med = props[len(props) // 2] if props else None
        summ["metrics"][m] = {"k": k, "n": len(base), "p": round(k / len(base), 3) if base else None,
                              "wilson95": wilson(k, len(base)), "entries_with_match": sum(1 for v in per.values() if v[0]),
                              "entries": len(per), "median_entry_rate": med, "per_entry": per}
    # precision sample (fixed seed)
    rng = random.Random(20261120)
    prec = {}
    for m in ("M1", "M2", "M3"):
        cands = [(r["entry"], r["instance"], l) for r in rows if r.get(m) for l in r[f"{m}_lines"][:1]]
        rng.shuffle(cands)
        prec[m] = cands[:20]
    with open(os.path.join(outdir, "summary.json"), "w") as f:
        json.dump(summ, f, indent=1)
    with open(os.path.join(outdir, "precision-sample.json"), "w") as f:
        json.dump(prec, f, indent=1)
    print(json.dumps({m: {k: v for k, v in d.items() if k != "per_entry"} for m, d in summ["metrics"].items()}, indent=1))
    print("exclusions", excl)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "ext02-out")
