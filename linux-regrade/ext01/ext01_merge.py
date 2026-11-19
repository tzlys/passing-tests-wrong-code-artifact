"""EXT-01: merge the first run with the stage-2b shards and apply the protocol's rules once.

    python ext01_merge.py <out> <first-run ext01-out> <plan.json>

plan.json maps each entry index (1-based, sorted data/*.jsonl) to the directory holding
its first-pass M/G logs ("main") and the directory holding its confirmation-rerun logs ("rep").
An entry is taken whole from one source. An entry with infrastructure failures in the first
run is taken from its complete rerun, never stitched record by record.
All sources must have the identical sample.json and data/ (checked by hash).
Classification is the same as ext01_analyze.py (imported, not copied).
"""
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

OUT, FIRST, PLAN = Path(sys.argv[1]), Path(sys.argv[2]), json.loads(Path(sys.argv[3]).read_text())
sys.argv = [sys.argv[0], str(FIRST), 'final']           # ext01_analyze reads OUT, PHASE at import
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ext01_analyze as A                                 # noqa: E402


def digest(d):
    h = hashlib.sha256((d / 'sample.json').read_bytes())
    for f in sorted((d / 'data').glob('*.jsonl')):
        h.update(f.name.encode()); h.update(f.read_bytes())
    return h.hexdigest()


def classify_from(main, rep, row, entry, k):
    A.LOGS = Path(main) / 'logs' / 'run_evaluation'
    c = A.classify(row, entry, k)
    if c.get('divergent'):
        A.LOGS = Path(rep) / 'logs' / 'run_evaluation'
        r = A.classify(row, entry, k, '-rep')
        first = {d['test'] for d in c['divergent_tests']}
        again = {d['test'] for d in r.get('divergent_tests', [])} if r.get('valid') else set()
        c['confirmed_tests'] = sorted(first & again)
        c['confirmed'] = bool(first & again)
        c['rerun_reason'] = r.get('reason')
    return c


def main():
    srcs = {str(FIRST)} | {v[x] for v in PLAN.values() for x in ('main', 'rep')}
    digests = {s: digest(Path(s)) for s in srcs}
    assert len(set(digests.values())) == 1, f'sample/data differ between sources: {digests}'
    A.OUT = FIRST
    ents = A.entries()
    sample = {(r['entry'], r['instance_id']): r for r in json.loads((FIRST / 'sample.json').read_text())}
    final = {}
    for k, e in enumerate(ents, 1):
        p = PLAN[str(k)]
        for row in A.rows(e):
            c = classify_from(p['main'], p['rep'], row, e, k)
            c['source'] = {'main': Path(p['main']).name, 'rep': Path(p['rep']).name}
            final[f'{e}/{row["instance_id"]}'] = c
    out = {'plan': PLAN, 'sample_data_sha256': next(iter(digests.values())),
           'per_record': final, 'by_group': {}, 'per_entry': {}, 'invalid_reasons': {}}
    grp_of = lambda k: 'resolved' if sample[tuple(k.split('/', 1))]['resolved'] else 'unresolved'
    for g in ('unresolved', 'resolved'):
        keys = [k for k in final if grp_of(k) == g]
        valid = [k for k in keys if final[k]['valid']]
        div1 = [k for k in valid if final[k].get('divergent')]
        conf = [k for k in valid if final[k].get('confirmed')]
        added = [k for k in conf if any(d['agent_added'] for d in final[k]['divergent_tests']
                                        if d['test'] in final[k]['confirmed_tests'])]
        out['by_group'][g] = {'sampled': len(keys), 'valid': len(valid), 'divergent_first_pass': len(div1),
                              'confirmed_divergent': len(conf),
                              'rate': round(len(conf) / len(valid), 3) if valid else None,
                              'wilson95': A.wilson(len(conf), len(valid)),
                              'confirmed_with_agent_added_test': len(added)}
        out['invalid_reasons'][g] = dict(Counter(final[k]['reason'] for k in keys if not final[k]['valid']))
    for k, e in enumerate(ents, 1):
        ks = [x for x in final if x.startswith(e + '/')]
        out['per_entry'][e] = {g: {'valid': sum(final[x]['valid'] for x in ks if grp_of(x) == g),
                                   'confirmed': sum(bool(final[x].get('confirmed')) for x in ks if grp_of(x) == g)}
                               for g in ('unresolved', 'resolved')}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'results-merged.json').write_text(json.dumps(out, indent=2))
    md = ['# EXT-01 merged results', '',
          '| group | sampled | valid | divergent (first pass) | confirmed divergent | rate | Wilson 95% | with agent-added test |',
          '|---|---|---|---|---|---|---|---|']
    for g in ('unresolved', 'resolved'):
        v = out['by_group'][g]
        md.append(f"| {g} | {v['sampled']} | {v['valid']} | {v['divergent_first_pass']} | {v['confirmed_divergent']} | "
                  f"{v['rate']} | {v['wilson95']} | {v['confirmed_with_agent_added_test']} |")
    md += ['', 'Invalid reasons: `' + json.dumps(out['invalid_reasons']) + '`', '', '## Confirmed divergent records', '']
    for k, c in final.items():
        if c.get('confirmed'):
            md.append(f"- `{k}` ({grp_of(k)}): " + '; '.join(
                f"`{d['test']}` → {d['G']}{' (agent-added)' if d['agent_added'] else ''}"
                for d in c['divergent_tests'] if d['test'] in c['confirmed_tests'])[:900])
    (OUT / 'RESULTS-EXT01-MERGED.md').write_text('\n'.join(md) + '\n')
    print('\n'.join(md))


if __name__ == '__main__':
    main()
