"""Write the SWE-bench predictions file from the frozen final patches (no model)."""
import json, sys
from pathlib import Path

TASKS = ['psf__requests-3362', 'pallets__flask-4045', 'pallets__flask-4992']
root, out = Path(sys.argv[1]), Path(sys.argv[2])
with open(out, 'w') as f:
    for t in TASKS:
        f.write(json.dumps({'instance_id': t, 'model_name_or_path': 'stageb',
                            'model_patch': (root / 'runs' / t / 'final.patch').read_text()}) + '\n')
print(f'wrote {out}')
