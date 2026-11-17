"""Confirm the harness dataset rows carry the same FAIL_TO_PASS / PASS_TO_PASS as the sealed oracle."""
import json, sys
from pathlib import Path
from datasets import load_dataset

TASKS = ['psf__requests-3362', 'pallets__flask-4045', 'pallets__flask-4992']
root, out = Path(sys.argv[1]), Path(sys.argv[2])
ds = load_dataset('princeton-nlp/SWE-bench_Lite', split='test')
rows = {r['instance_id']: r for r in ds if r['instance_id'] in TASKS}
res = {}
for t in TASKS:
    r = rows[t]
    f2p, p2p = json.loads(r['FAIL_TO_PASS']), json.loads(r['PASS_TO_PASS'])
    o_f2p = json.loads((root / 'oracle' / t / 'FAIL_TO_PASS.json').read_text())
    o_p2p = json.loads((root / 'oracle' / t / 'PASS_TO_PASS.json').read_text())
    res[t] = {'f2p_equal': f2p == o_f2p, 'p2p_equal': p2p == o_p2p,
              'base_commit': r['base_commit'], 'version': r['version']}
try:
    from huggingface_hub import HfApi
    res['_dataset_sha'] = HfApi().dataset_info('princeton-nlp/SWE-bench_Lite').sha
except Exception as e:  # informational only
    res['_dataset_sha'] = f'unavailable: {e}'
out.write_text(json.dumps(res, indent=2))
print(json.dumps(res, indent=2))
