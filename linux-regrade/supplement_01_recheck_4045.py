"""SUPPLEMENT-01: rerun the one flask-4045 recheck row that AMENDMENT-02 could not reproduce.

    python3 supplement_01_recheck_4045.py <stage-b-review-artifact dir> <output dir> [--extract-only]

Why: in AMENDMENT-02, the row
    pytest -q /private/tmp/flask-4045-blueprint-verification/test_nested_blueprints.py
exited 0 on macOS and 4 (file not found) on Linux. The model had written that
test file outside the repository during its session, so it was not part of
the frozen final patch. This supplement was added after the AMENDMENT-02 results
were known (2026-11-17). It is reported as a post-hoc supplement and does not
replace the AMENDMENT-02 row.

Steps:
1. Recover the file from the native session record. The model's command
   `cat > <file> <<'PY' ... PY` is in runs/pallets__flask-4045/observable-events.jsonl.
   The heredoc body is taken byte for byte from the completed command item.
2. Apply the AMENDMENT-02 rewrite rule to the file's text as well:
   "/Users/lyseo/sbwork/pallets__flask-4045/repo" -> "/testbed".
   This is the only change. Both hashes are recorded.
3. Start the official instance image, apply the frozen final patch, and write
   the file at the same absolute path, /private/tmp/flask-4045-blueprint-verification/.
4. Rerun the row with the AMENDMENT-02 command rewrite, twice as run and twice
   source-forced, clearing caches before each run.
5. Negative control: the same row without the file must exit 4 again, which
   reproduces the AMENDMENT-02 result.
No model is called.
"""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

TASK = 'pallets__flask-4045'
IMAGE = 'swebench/sweb.eval.x86_64.pallets_1776_flask-4045:latest'
AMENDMENT02_IMAGE_ID = 'sha256:1425b0801ddf4b2607e552e56516cce3d389bab0a3ce06f58e6fa6a7835c703c'
TMPDIR = '/private/tmp/flask-4045-blueprint-verification'
FILE = TMPDIR + '/test_nested_blueprints.py'
MAC_REPO = f'/Users/lyseo/sbwork/{TASK}/repo'
ROW = "/bin/zsh -lc 'python -m pytest -q " + FILE + " -W ignore::DeprecationWarning'"
ACTIVATE = 'source /opt/miniconda3/bin/activate testbed'
ROOT, OUT = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
OUT.mkdir(parents=True, exist_ok=True)


def sha(b):
    return hashlib.sha256(b).hexdigest()


def recover():
    """Return (heredoc body as written on macOS, event index, item id)."""
    hits = []
    for i, line in enumerate((ROOT / 'runs' / TASK / 'observable-events.jsonl').open()):
        d = json.loads(line)
        if d.get('method') != 'item/completed':
            continue
        item = d['params']['item']
        if item.get('type') != 'commandExecution' or f'cat > {FILE} <<' not in item['command']:
            continue
        hits.append((i, item))
    if len(hits) != 1:
        raise SystemExit(f'expected exactly one completed command writing the file, found {len(hits)}')
    i, item = hits[0]
    if item.get('exitCode') != 0:
        raise SystemExit('the writing command did not exit 0')
    cmd = item['command']
    if not (cmd.startswith('/bin/zsh -lc "') and cmd.endswith('"')):
        raise SystemExit('unexpected command quoting')
    # The command is zsh -lc "<script>": undo the double-quote escaping that zsh would undo.
    script = re.sub(r'\\([\\"$`])', r'\1', cmd[len('/bin/zsh -lc "'):-1])
    m = re.search(r"cat > " + re.escape(FILE) + r" <<'PY'\n(.*?\n)PY\Z", script, re.S)
    if not m:
        raise SystemExit('heredoc not found')
    return m.group(1), i, item['id']


def sh(args, **kw):
    return subprocess.run(args, capture_output=True, text=True, **kw)


def run_in(name, script, timeout=600):
    p = sh(['docker', 'exec', '-w', '/testbed', name, 'bash', '-c', script], timeout=timeout)
    return p.returncode, (p.stdout + p.stderr)[-2000:]


def rerun(name, cmd, forced):
    rows = {'as_run': [], 'source_forced': []}
    for label, env in (('as_run', 'unset PYTHONPATH'), ('source_forced', forced)):
        for _ in range(2):
            run_in(name, 'find /testbed -name __pycache__ -type d -prune -exec rm -rf {} +; rm -rf /testbed/.pytest_cache')
            ec, out = run_in(name, f'{ACTIVATE}; export PYTHONDONTWRITEBYTECODE=1; {env}; cd /testbed && {cmd}')
            rows[label].append({'exit': ec, 'tail': out})
    return rows


def main():
    body, idx, item_id = recover()
    rewritten = body.replace(MAC_REPO, '/testbed')
    assert body.count(MAC_REPO) == 1 and MAC_REPO not in rewritten
    (OUT / 'recovered-test_nested_blueprints.macos.py').write_text(body)
    (OUT / 'recovered-test_nested_blueprints.linux.py').write_text(rewritten)
    rec = {'source': f'runs/{TASK}/observable-events.jsonl line {idx} (0-based), item {item_id}',
           'macos_text_sha256': sha(body.encode()), 'linux_text_sha256': sha(rewritten.encode()),
           'rewrite': f'"{MAC_REPO}" -> "/testbed" (AMENDMENT-02 rule, applied to the file text)'}
    print(json.dumps(rec, indent=2))
    if '--extract-only' in sys.argv:
        return

    A = json.loads((ROOT / 'runs' / TASK / 'analysis.json').read_text())
    mac = [r for r in A['recheck'] if r['command'] == ROW]
    assert len(mac) == 1, 'row not found in analysis.json'
    mac = mac[0]

    sh(['docker', 'pull', IMAGE], check=True)
    image_id = sh(['docker', 'image', 'inspect', '--format', '{{.Id}}', IMAGE]).stdout.strip()
    name = 'stageb-supp01-flask-4045'
    sh(['docker', 'rm', '-f', name])
    sh(['docker', 'run', '-d', '--name', name, IMAGE, 'sleep', 'infinity'], check=True)
    sh(['docker', 'cp', str(ROOT / 'runs' / TASK / 'final.patch'), f'{name}:/tmp/final.patch'], check=True)
    apply_exit, apply_tail = run_in(name, 'git apply --whitespace=nowarn /tmp/final.patch')
    forced = 'export PYTHONPATH=/testbed/src:/testbed'
    cmd = ROW.replace('/bin/zsh -lc ', 'bash -c ', 1)

    control = rerun(name, cmd, forced)                       # file absent: expect exit 4
    run_in(name, f'mkdir -p {TMPDIR}')
    sh(['docker', 'cp', str(OUT / 'recovered-test_nested_blueprints.linux.py'), f'{name}:{FILE}'], check=True)
    in_container = run_in(name, f'sha256sum {FILE}')[1].split()[0]
    with_file = rerun(name, cmd, forced)
    versions = run_in(name, f'{ACTIVATE}; python -c "import flask,werkzeug,sys;print(sys.version.split()[0],flask.__version__,werkzeug.__version__)"')[1].strip()
    sh(['docker', 'rm', '-f', name])

    exits = lambda r: [x['exit'] for x in r]
    report = {
        'supplement': 'SUPPLEMENT-01 (post-hoc, after AMENDMENT-02 results)',
        'recovered_file': rec, 'file_sha256_in_container': in_container,
        'image': IMAGE, 'image_id': image_id,
        'image_id_matches_amendment02': image_id == AMENDMENT02_IMAGE_ID,
        'patch_apply_exit': apply_exit, 'patch_apply_tail': apply_tail,
        'python_flask_werkzeug': versions,
        'command_macos': ROW, 'command_linux': cmd,
        'macos': {'as_run': exits(mac['as_run']), 'source_forced': exits(mac['source_forced'])},
        'linux_without_file': {k: exits(v) for k, v in control.items()},
        'linux_with_file': {k: exits(v) for k, v in with_file.items()},
        'raw': {'without_file': control, 'with_file': with_file},
    }
    report['control_reproduces_amendment02'] = all(e == 4 for v in report['linux_without_file'].values() for e in v)
    report['with_file_same_as_macos'] = report['linux_with_file'] == report['macos']
    (OUT / 'supplement-01.json').write_text(json.dumps(report, indent=2))
    print(json.dumps({k: v for k, v in report.items() if k != 'raw'}, indent=2))


if __name__ == '__main__':
    main()
