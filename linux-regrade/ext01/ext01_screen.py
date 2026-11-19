"""EXT-01 step 1: download public patches, apply the inclusion rules, sample, and write harness inputs.

    python ext01_screen.py <ext01 dir> <out dir>

Follows EXT-01-PROTOCOL.md. Reads S3 anonymously. Writes into <out dir>:
  screen.json                 counts at every inclusion step and every exclusion reason
  sample.json                 sampled records (entry, instance, resolved, test/source paths)
  data/<entry>.jsonl          harness dataset rows: test_patch = the agent's test blocks
  preds/<entry>.M.jsonl       model_patch = the agent's source blocks
"""
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import boto3
from botocore import UNSIGNED
from botocore.config import Config

EXT, OUT = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
BUCKET = 'swe-bench-submissions'
CAP_UNRES_ENTRY, CAP_UNRES_TOTAL = 12, 160
CAP_RES_ENTRY, CAP_RES_TOTAL = 4, 60
s3 = boto3.client('s3', config=Config(signature_version=UNSIGNED, max_pool_connections=64))


def is_test_path(p):
    # 'tests/' anywhere is a test suite; 'testing/' only at the repository root (pytest's suite).
    # A bare 'test/' or a nested 'testing/' directory is library code in Lite repositories
    # (django/test/, sympy/testing/), so it counts as source.
    parts = p.split('/')
    base = parts[-1]
    return ('tests' in parts[:-1] or parts[0] == 'testing'
            or base.startswith('test_') or base.endswith('_test.py') or base == 'conftest.py')


def split_patch(patch):
    """Return (test_blocks, source_blocks, test_paths, source_paths), keeping block text exactly."""
    blocks = re.split(r'(?=^diff --git )', patch, flags=re.M)
    tests, srcs, tp, sp = [], [], [], []
    for b in blocks:
        m = re.match(r'diff --git a/(\S+) b/(\S+)', b)
        if not m:
            continue  # preamble text before the first block
        path = m.group(2)
        if not b.endswith('\n'):
            b += '\n'
        if is_test_path(path):
            tests.append(b); tp.append(path)
        else:
            srcs.append(b); sp.append(path)
    return ''.join(tests), ''.join(srcs), tp, sp


def list_instances(entry):
    prefix = f'lite/{entry}/logs/'
    keys = []
    for page in s3.get_paginator('list_objects_v2').paginate(Bucket=BUCKET, Prefix=prefix):
        keys += [o['Key'] for o in page.get('Contents', [])]
    by = defaultdict(set)
    for k in keys:
        rest = k[len(prefix):].split('/')
        if len(rest) == 2 and rest[1] in ('patch.diff', 'report.json'):
            by[rest[0]].add(rest[1])
    return by


def fetch(entry, iid, name):
    dest = OUT / 'raw' / entry / iid / name
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        s3.download_file(BUCKET, f'lite/{entry}/logs/{iid}/{name}', str(dest))
    return dest


def main():
    from datasets import load_dataset
    entries = [l.strip() for l in (EXT / 'entries.txt').read_text().splitlines() if l.strip()]
    ds = {r['instance_id']: dict(r) for r in load_dataset('princeton-nlp/SWE-bench_Lite', split='test')}
    try:
        from huggingface_hub import HfApi
        ds_sha = HfApi().dataset_info('princeton-nlp/SWE-bench_Lite').sha
    except Exception as e:
        ds_sha = f'unavailable: {e}'
    screen = {'entries': len(entries), 'dataset_sha': ds_sha, 'per_entry': {}, 'exclusions': Counter()}
    included = []
    for entry in entries:
        by = list_instances(entry)
        jobs = [(entry, iid, n) for iid, names in by.items() for n in ('patch.diff', 'report.json') if n in names]
        with ThreadPoolExecutor(32) as ex:
            list(ex.map(lambda a: fetch(*a), jobs))
        st = Counter(listed=len(by))
        for iid, names in sorted(by.items()):
            if iid not in ds:
                st['not_in_lite_dataset'] += 1; continue
            if names != {'patch.diff', 'report.json'}:
                st['missing_file'] += 1; continue
            try:
                rep = json.loads((OUT / 'raw' / entry / iid / 'report.json').read_text())
                resolved = rep[iid]['resolved']
                assert isinstance(resolved, bool)
            except Exception:
                st['bad_report'] += 1; continue
            patch = (OUT / 'raw' / entry / iid / 'patch.diff').read_text(errors='replace')
            tests, srcs, tp, sp = split_patch(patch)
            if not any(p.endswith('.py') for p in tp):
                st['no_py_test_block'] += 1; continue
            if not srcs:
                st['no_source_block'] += 1; continue
            st['included_resolved' if resolved else 'included_unresolved'] += 1
            included.append({'entry': entry, 'instance_id': iid, 'resolved': resolved,
                             'test_paths': tp, 'source_paths': sp,
                             'key': hashlib.sha256(f'{entry}/{iid}'.encode()).hexdigest(),
                             'test_patch': tests, 'source_patch': srcs})
        screen['per_entry'][entry] = dict(st)
        for k, v in st.items():
            screen['exclusions'][k] += v
        print(entry, dict(st), flush=True)

    included.sort(key=lambda r: r['key'])
    taken, per = [], Counter()
    tot = Counter()
    for r in included:
        kind = 'res' if r['resolved'] else 'unres'
        cap_e, cap_t = (CAP_RES_ENTRY, CAP_RES_TOTAL) if r['resolved'] else (CAP_UNRES_ENTRY, CAP_UNRES_TOTAL)
        if per[(r['entry'], kind)] < cap_e and tot[kind] < cap_t:
            per[(r['entry'], kind)] += 1; tot[kind] += 1; taken.append(r)
    screen['sampled'] = dict(tot)
    screen['exclusions'] = dict(screen['exclusions'])
    (OUT / 'screen.json').write_text(json.dumps(screen, indent=2))
    (OUT / 'sample.json').write_text(json.dumps(
        [{k: v for k, v in r.items() if k not in ('test_patch', 'source_patch')} for r in taken], indent=2))

    (OUT / 'data').mkdir(exist_ok=True); (OUT / 'preds').mkdir(exist_ok=True)
    by_entry = defaultdict(list)
    for r in taken:
        by_entry[r['entry']].append(r)
    for entry, rows in by_entry.items():
        with open(OUT / 'data' / f'{entry}.jsonl', 'w') as fd, open(OUT / 'preds' / f'{entry}.M.jsonl', 'w') as fp:
            for r in rows:
                row = dict(ds[r['instance_id']])
                row['test_patch'] = r['test_patch']
                row['FAIL_TO_PASS'] = '[]'
                row['PASS_TO_PASS'] = '[]'
                fd.write(json.dumps(row) + '\n')
                fp.write(json.dumps({'instance_id': r['instance_id'], 'model_name_or_path': f'agent__{entry}',
                                     'model_patch': r['source_patch']}) + '\n')
    print(json.dumps({'sampled': dict(tot), 'entries_with_sample': len(by_entry)}, indent=2))


if __name__ == '__main__':
    main()
