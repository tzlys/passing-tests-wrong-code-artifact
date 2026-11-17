"""AMENDMENT-02 step 2: Linux serial recheck inside the official SWE-bench instance image.

    python3 linux_recheck.py <stage-b-review-artifact dir> <output dir>

For each task:
1. Start the harness's instance image (base commit plus the installed
   environment) and apply the frozen final patch.
2. Rerun every row that the macOS analysis rechecked (runs/<task>/analysis.json,
   key "recheck"): twice as run and twice source-forced, with caches cleared
   before each run, exactly as on macOS.

Rewrite rule (recorded in the output):
- The leading "/bin/zsh -lc " becomes "bash -c ". A login shell would reset
  PATH and drop the conda environment.
- "/Users/lyseo/sbwork/<task>/repo" becomes "/testbed".
- Every other path is left as it is.
No model is called.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

TASKS = ['psf__requests-3362', 'pallets__flask-4045', 'pallets__flask-4992']
ROOT, OUT = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
OUT.mkdir(parents=True, exist_ok=True)
ACTIVATE = 'source /opt/miniconda3/bin/activate testbed'
RULE = {'shell': '"/bin/zsh -lc " -> "bash -c "', 'repo': '"/Users/lyseo/sbwork/<task>/repo" -> "/testbed"'}


def sh(args, **kw):
    return subprocess.run(args, capture_output=True, text=True, **kw)


def find_image(task):
    names = sh(['docker', 'images', '--format', '{{.Repository}}:{{.Tag}}']).stdout.split()
    keys = [f'sweb.eval.x86_64.{task}:', f'sweb.eval.x86_64.{task.replace("__", "_1776_")}:']
    hits = [n for n in names if any(k in n for k in keys)]
    if not hits:
        raise SystemExit(f'no instance image for {task}; run the harness first (cache_level=instance)')
    return hits[0]


def rewrite(cmd, task):
    c = cmd.replace(f'/Users/lyseo/sbwork/{task}/repo', '/testbed')
    if c.startswith('/bin/zsh -lc '):
        c = 'bash -c ' + c[len('/bin/zsh -lc '):]
    return c


def run_in(name, script, timeout=600):
    try:
        p = sh(['docker', 'exec', '-w', '/testbed', name, 'bash', '-c', script], timeout=timeout)
        return p.returncode, (p.stdout + p.stderr)[-1500:]
    except subprocess.TimeoutExpired:
        return 'timeout', ''


def main():
    report = {'rule': RULE, 'tasks': {}}
    for task in TASKS:
        A = json.loads((ROOT / 'runs' / task / 'analysis.json').read_text())
        img = find_image(task)
        digest = sh(['docker', 'image', 'inspect', '--format', '{{.Id}}', img]).stdout.strip()
        name = f'stageb-recheck-{task.replace("__", "-")}'
        sh(['docker', 'rm', '-f', name])
        sh(['docker', 'run', '-d', '--name', name, img, 'sleep', 'infinity'], check=True)
        sh(['docker', 'cp', str(ROOT / 'runs' / task / 'final.patch'), f'{name}:/tmp/final.patch'], check=True)
        code, tail = run_in(name, 'git apply --whitespace=nowarn /tmp/final.patch')
        diff = sh(['docker', 'exec', '-w', '/testbed', name, 'git', 'diff']).stdout
        patch = (ROOT / 'runs' / task / 'final.patch').read_text()
        src = run_in(name, 'test -d /testbed/src')[0] == 0
        forced = 'export PYTHONPATH=' + ('/testbed/src:/testbed' if src else '/testbed')
        rows = []
        for r in A['recheck']:
            cmd = rewrite(r['command'], task)
            row = {'command': r['command'], 'linux_command': cmd,
                   'macos_as_run': [x['exit'] for x in r['as_run']],
                   'macos_source_forced': [x['exit'] for x in r['source_forced']],
                   'as_run': [], 'source_forced': []}
            for label, env in (('as_run', 'unset PYTHONPATH'), ('source_forced', forced)):
                for _ in range(2):
                    run_in(name, 'find /testbed -name __pycache__ -type d -prune -exec rm -rf {} +; rm -rf /testbed/.pytest_cache')
                    ec, out = run_in(name, f'{ACTIVATE}; export PYTHONDONTWRITEBYTECODE=1; {env}; cd /testbed && {cmd}')
                    row[label].append({'exit': ec, 'tail': out})
            rows.append(row)
        sh(['docker', 'rm', '-f', name])
        report['tasks'][task] = {
            'image': img, 'image_id': digest, 'patch_apply_exit': code, 'patch_apply_tail': tail,
            'tree_matches_final_patch_sha256': hashlib.sha256(diff.encode()).hexdigest() == hashlib.sha256(patch.encode()).hexdigest(),
            'rows': rows}
        print(task, 'patch', code, 'rows', len(rows))
    (OUT / 'linux-recheck.json').write_text(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
