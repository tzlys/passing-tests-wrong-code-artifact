"""EXT-01 analysis.

    python ext01_analyze.py <out dir> phase1   # classify the first runs; write rerun inputs for divergent records
    python ext01_analyze.py <out dir> final    # combine with reruns; write results.json and RESULTS-EXT01.md

Rules are those in EXT-01-PROTOCOL.md. Statuses come from the harness's own
parser (get_logs_eval). Run ids: ext01-<k>-M / ext01-<k>-G for the first run and
ext01-<k>-M-rep / ext01-<k>-G-rep for the confirmation rerun, where k is the
1-based index of the entry in entries order of data/*.jsonl (sorted).
"""
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from types import SimpleNamespace

from swebench.harness.grading import get_logs_eval

OUT, PHASE = Path(sys.argv[1]).resolve(), sys.argv[2]
LOGS = OUT / 'logs' / 'run_evaluation'
FAIL = {'FAILED', 'ERROR'}


def entries():
    return sorted(p.stem for p in (OUT / 'data').glob('*.jsonl'))


def rows(entry, base='data'):
    return [json.loads(l) for l in (OUT / base / f'{entry}.jsonl').read_text().splitlines()]


def status(run_id, model, row):
    fp = LOGS / run_id / model / row['instance_id'] / 'test_output.txt'
    if not fp.exists():
        return None, 'no_log'
    try:
        # get_logs_eval reads only repo and version from the spec; building a full TestSpec would
        # fetch environment requirements over the network, which grading does not need.
        spec = SimpleNamespace(repo=row['repo'], version=row['version'], instance_id=row['instance_id'])
        sm, ok = get_logs_eval(spec, str(fp))
    except Exception as e:  # parser failure counts as invalid, with reason
        return None, f'parse_error:{type(e).__name__}'
    return (sm, 'ok') if ok else (None, 'harness_bad_code')


def fname(test):
    t = re.sub(r'\[.*$', '', test.split(' ')[0] if ' (' in test else test)
    return t.split('::')[-1].split('.')[-1]


def classify(row, entry, k, suffix=''):
    sm_m, rm = status(f'ext01-{k}-M{suffix}', f'agent__{entry}', row)
    sm_g, rg = status(f'ext01-{k}-G{suffix}', 'gold', row)
    if sm_m is None or sm_g is None:
        return {'valid': False, 'reason': f'M:{rm} G:{rg}'}
    m_pass = sorted(t for t, s in sm_m.items() if s == 'PASSED')
    if not m_pass:
        return {'valid': False, 'reason': 'no_test_passes_in_M'}
    g_fails = any(s in FAIL for s in sm_g.values()) or not sm_g
    div = []
    for t in m_pass:
        g = sm_g.get(t)
        if g in FAIL:
            div.append({'test': t, 'G': g})
        elif g is None and g_fails:
            div.append({'test': t, 'G': 'absent'})
    for d in div:
        d['agent_added'] = bool(re.search(r'^\+\s*def\s+' + re.escape(fname(d['test'])) + r'\s*\(',
                                          row['test_patch'], re.M))
    return {'valid': True, 'm_pass': len(m_pass), 'divergent': bool(div), 'divergent_tests': div}


def wilson(x, n, z=1.96):
    if n == 0:
        return None
    p = x / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(c - h, 3), round(c + h, 3)]


def main():
    sample = {(r['entry'], r['instance_id']): r for r in json.loads((OUT / 'sample.json').read_text())}
    ents = entries()
    if PHASE == 'phase1':
        res, rerun = {}, defaultdict(list)
        for k, e in enumerate(ents, 1):
            for row in rows(e):
                c = classify(row, e, k)
                res[f'{e}/{row["instance_id"]}'] = c
                if c.get('divergent'):
                    rerun[e].append(row)
        (OUT / 'phase1.json').write_text(json.dumps(res, indent=2))
        (OUT / 'rerun' / 'data').mkdir(parents=True, exist_ok=True)
        (OUT / 'rerun' / 'preds').mkdir(parents=True, exist_ok=True)
        for e, rs in rerun.items():
            ids = {r['instance_id'] for r in rs}
            (OUT / 'rerun' / 'data' / f'{e}.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in rs))
            preds = [l for l in (OUT / 'preds' / f'{e}.M.jsonl').read_text().splitlines()
                     if json.loads(l)['instance_id'] in ids]
            (OUT / 'rerun' / 'preds' / f'{e}.M.jsonl').write_text('\n'.join(preds) + '\n')
        print(json.dumps(Counter('invalid' if not c['valid'] else ('divergent' if c['divergent'] else 'not_divergent')
                                 for c in res.values()), indent=2))
        return

    p1 = json.loads((OUT / 'phase1.json').read_text())
    final = {}
    for k, e in enumerate(ents, 1):
        for row in rows(e):
            key = f'{e}/{row["instance_id"]}'
            c = dict(p1[key])
            if c.get('divergent'):
                rep = classify(row, e, k, '-rep')
                first = {d['test'] for d in c['divergent_tests']}
                again = {d['test'] for d in rep.get('divergent_tests', [])} if rep.get('valid') else set()
                c['confirmed_tests'] = sorted(first & again)
                c['confirmed'] = bool(first & again)
                c['rerun_reason'] = rep.get('reason')
            final[key] = c
    out = {'per_record': final, 'by_group': {}, 'per_entry': {}, 'invalid_reasons': {}}
    for grp in ('unresolved', 'resolved'):
        keys = [k for k in final if sample[tuple(k.split('/', 1))]['resolved'] == (grp == 'resolved')]
        valid = [k for k in keys if final[k]['valid']]
        conf = [k for k in valid if final[k].get('confirmed')]
        added = [k for k in conf if any(d['agent_added'] for d in final[k]['divergent_tests']
                                        if d['test'] in final[k]['confirmed_tests'])]
        out['by_group'][grp] = {'sampled': len(keys), 'valid': len(valid),
                                'divergent_first_run': sum(final[k].get('divergent', False) for k in valid),
                                'confirmed_divergent': len(conf), 'rate': round(len(conf) / len(valid), 3) if valid else None,
                                'wilson95': wilson(len(conf), len(valid)), 'confirmed_with_agent_added_test': len(added)}
        out['invalid_reasons'][grp] = dict(Counter(final[k]['reason'] for k in keys if not final[k]['valid']))
    for e in ents:
        ks = [k for k in final if k.startswith(e + '/')]
        out['per_entry'][e] = {g: {'valid': sum(final[k]['valid'] for k in ks if sample[tuple(k.split('/', 1))]['resolved'] == (g == 'resolved')),
                                   'confirmed': sum(bool(final[k].get('confirmed')) for k in ks if sample[tuple(k.split('/', 1))]['resolved'] == (g == 'resolved'))}
                               for g in ('unresolved', 'resolved')}
    (OUT / 'results.json').write_text(json.dumps(out, indent=2))
    u, r = out['by_group']['unresolved'], out['by_group']['resolved']
    md = ['# EXT-01 results', '', '| group | sampled | valid | confirmed divergent | rate | Wilson 95% | with agent-added test |',
          '|---|---|---|---|---|---|---|']
    for g, v in (('unresolved', u), ('resolved', r)):
        md.append(f"| {g} | {v['sampled']} | {v['valid']} | {v['confirmed_divergent']} | {v['rate']} | {v['wilson95']} | {v['confirmed_with_agent_added_test']} |")
    md += ['', 'Invalid reasons: `' + json.dumps(out['invalid_reasons']) + '`']
    (OUT / 'RESULTS-EXT01.md').write_text('\n'.join(md) + '\n')
    print('\n'.join(md))


if __name__ == '__main__':
    main()
