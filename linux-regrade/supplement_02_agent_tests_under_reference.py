"""SUPPLEMENT-02: run the tests the model wrote against the reference fix.

    python3 supplement_02_agent_tests_under_reference.py <stage-b-review-artifact dir> <output dir> <recovered wrapper .py>

Question: does each agent-written test encode the agent's own reading (taxonomy
class A4)? If it does, the test should pass on the agent's code and fail on the
reference fix wherever the two readings differ. Until now this was read from the
patches. This supplement executes it. No model is called. It is post-hoc
(planned 2026-11-18, after all grading), and the predictions below were
committed to the public repository before the first run.

Conditions, each in a fresh container of the official instance image:
  M  base + the model's final patch (source and tests), as at the end of the session
  G  base + the reference source patch (oracle patch.diff) + only the test files of
     the model's final patch (`git apply --include='tests/*'`)
Each selected test runs twice per condition, with
  python -m pytest -rA -p no:cacheprovider -W ignore::DeprecationWarning <node ids>
caches cleared before every run and PYTHONDONTWRITEBYTECODE=1.

PREDICTIONS (written before any run; "fail" includes error):
  requests-3362
    test_response_decode_unicode_without_encoding   M pass  G fail   (reference decodes with the apparent encoding)
    test_get_encoding_from_headers                  M pass  G fail only for the case ('application/json' -> 'utf-8')
    test_response_decode_unicode                    M pass  G pass   (only its docstring changed)
    test_json_response_decode_unicode               M pass  G no prediction (depends on charset detection)
  flask-4045
    test_dotted_names (4 cases)                     M pass  G pass   (reference raises the same message for names)
    test_nested_blueprint                           M fail  G fail   (environment: Werkzeug as_tuple mismatch)
    out-of-repo wrapper (SUPPLEMENT-01 file)        M pass  G pass
  flask-4992
    test_config_from_file_mode [None]               M pass  G pass
    test_config_from_file_mode [t], [b]             M pass  G fail   (reference has no mode parameter)
    test_config_from_file_toml (model's version)    M pass  G fail   (same name as the hidden test; uses mode="b")
    test_config_missing_file [t], [b]               M pass  G fail
"""
import hashlib
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT, OUT, WRAPPER = (Path(a).resolve() for a in sys.argv[1:4])
OUT.mkdir(parents=True, exist_ok=True)
WRAPPER_SHA = '260692f23c9f62b28bab7139d2b215aa043fd66e5b39b8717bc09ab7a28f3465'
WRAPPER_PATH = '/private/tmp/flask-4045-blueprint-verification/test_nested_blueprints.py'
ACTIVATE = 'source /opt/miniconda3/bin/activate testbed'
PYTEST = 'python -m pytest -rA -p no:cacheprovider -W ignore::DeprecationWarning'

TASKS = {
    'psf__requests-3362': {
        'image': 'swebench/sweb.eval.x86_64.psf_1776_requests-3362:latest',
        'ids': ['tests/test_requests.py::TestRequests::test_response_decode_unicode_without_encoding',
                'tests/test_utils.py::test_get_encoding_from_headers',
                'tests/test_requests.py::TestRequests::test_response_decode_unicode',
                'tests/test_requests.py::TestRequests::test_json_response_decode_unicode'],
        'wrapper': False},
    'pallets__flask-4045': {
        'image': 'swebench/sweb.eval.x86_64.pallets_1776_flask-4045:latest',
        'ids': ['tests/test_blueprints.py::test_dotted_names',
                'tests/test_blueprints.py::test_nested_blueprint'],
        'wrapper': True},
    'pallets__flask-4992': {
        'image': 'swebench/sweb.eval.x86_64.pallets_1776_flask-4992:latest',
        'ids': ['tests/test_config.py::test_config_from_file_mode',
                'tests/test_config.py::test_config_from_file_toml',
                'tests/test_config.py::test_config_missing_file'],
        'wrapper': False},
}


def sh(args, **kw):
    return subprocess.run(args, capture_output=True, text=True, **kw)


def run_in(name, script, timeout=900):
    p = sh(['docker', 'exec', '-w', '/testbed', name, 'bash', '-c', script], timeout=timeout)
    return p.returncode, p.stdout + p.stderr


def parse(out):
    """Per-node outcomes from pytest -rA short summary."""
    res = {}
    for line in out.splitlines():
        m = re.match(r'^(PASSED|FAILED|ERROR|XFAIL|XPASS) (\S.*?)(?: - .*)?$', line)
        if m and '::' in m.group(2):
            res[m.group(2)] = m.group(1)
        m = re.match(r'^SKIPPED \[\d+\] (\S+?):\d+: (.*)$', line)
        if m:
            res[f'SKIPPED {m.group(1)}: {m.group(2)}'] = 'SKIPPED'
    return res


def condition(task, spec, cond):
    name = f'stageb-supp02-{task.split("__")[1]}-{cond}'
    sh(['docker', 'rm', '-f', name])
    sh(['docker', 'run', '-d', '--name', name, spec['image'], 'sleep', 'infinity'], check=True)
    sh(['docker', 'cp', str(ROOT / 'runs' / task / 'final.patch'), f'{name}:/tmp/final.patch'], check=True)
    sh(['docker', 'cp', str(ROOT / 'oracle' / task / 'patch.diff'), f'{name}:/tmp/reference.patch'], check=True)
    steps = []
    if cond == 'M':
        steps.append(run_in(name, 'git apply --whitespace=nowarn /tmp/final.patch'))
    else:
        steps.append(run_in(name, 'git apply --whitespace=nowarn /tmp/reference.patch'))
        steps.append(run_in(name, "git apply --whitespace=nowarn --include='tests/*' /tmp/final.patch"))
    ids = list(spec['ids'])
    if spec['wrapper']:
        run_in(name, f'mkdir -p {Path(WRAPPER_PATH).parent}')
        sh(['docker', 'cp', str(WRAPPER), f'{name}:{WRAPPER_PATH}'], check=True)
        ids.append(WRAPPER_PATH)
    diffstat = run_in(name, 'git status --short')[1]
    runs = []
    for _ in range(2):
        run_in(name, 'find /testbed -name __pycache__ -type d -prune -exec rm -rf {} +; rm -rf /testbed/.pytest_cache')
        ec, out = run_in(name, f'{ACTIVATE}; export PYTHONDONTWRITEBYTECODE=1; unset PYTHONPATH; cd /testbed && '
                               f'{PYTEST} ' + ' '.join(f"'{i}'" for i in ids))
        runs.append({'exit': ec, 'outcomes': parse(out), 'tail': out[-6000:]})
    versions = run_in(name, f'{ACTIVATE}; python -c "import sys;print(sys.version.split()[0])"')[1].strip()
    image_id = sh(['docker', 'image', 'inspect', '--format', '{{.Id}}', spec['image']]).stdout.strip()
    sh(['docker', 'rm', '-f', name])
    return {'apply_exits': [s[0] for s in steps], 'apply_tails': [s[1][-800:] for s in steps],
            'git_status': diffstat, 'python': versions, 'image_id': image_id, 'runs': runs}


def function_of(node):
    return re.sub(r'\[.*$', '', node)


def summarize(cond_result):
    agg = defaultdict(lambda: defaultdict(int))
    for r in cond_result['runs']:
        for node, outcome in r['outcomes'].items():
            agg[function_of(node)][outcome] += 1
    return {k: dict(v) for k, v in agg.items()}


def main():
    if hashlib.sha256(WRAPPER.read_bytes()).hexdigest() != WRAPPER_SHA:
        raise SystemExit('recovered wrapper hash mismatch')
    report = {'supplement': 'SUPPLEMENT-02 (post-hoc; predictions in this file were committed before the run)',
              'pytest': PYTEST, 'tasks': {}}
    for task, spec in TASKS.items():
        sh(['docker', 'pull', spec['image']], check=True)
        t = {'image': spec['image'], 'ids': spec['ids'], 'wrapper': spec['wrapper']}
        for cond in ('M', 'G'):
            t[cond] = condition(task, spec, cond)
            t[cond + '_by_function'] = summarize(t[cond])
            t[cond + '_per_case'] = {n: [r['outcomes'].get(n) for r in t[cond]['runs']]
                                     for n in sorted(set().union(*(r['outcomes'] for r in t[cond]['runs'])))}
        report['tasks'][task] = t
        print(task, 'M', json.dumps(t['M_by_function']), '\n', ' ' * len(task), 'G', json.dumps(t['G_by_function']), flush=True)
    (OUT / 'supplement-02.json').write_text(json.dumps(report, indent=2))
    brief = {task: {c: {'apply_exits': t[c]['apply_exits'], 'exits': [r['exit'] for r in t[c]['runs']],
                        'per_case': t[c + '_per_case']} for c in ('M', 'G')}
             for task, t in report['tasks'].items()}
    (OUT / 'supplement-02-brief.json').write_text(json.dumps(brief, indent=2))
    print(json.dumps(brief, indent=2))


if __name__ == '__main__':
    main()
