"""Walk through one primary case: a passing test supports code it never ran.

    python3 -B show_case.py

Case: more-itertools `ChunkedTests.test_even`, overlapping-fault scenario,
original MemTrace policy (paper Section III-A). It reads only the saved
records under case/; standard library only, about one second. Each step
prints the record it relies on and the file it came from. The script exits
non-zero if any step does not hold.
"""
import hashlib
import json
import re
import sqlite3
import sys
from pathlib import Path

CASE = Path(__file__).resolve().parent / 'case' / 'more-chunked-pass-then-break-original'
OK = True


def check(cond, text):
    global OK
    OK &= bool(cond)
    print(f"  [{'ok' if cond else 'FAIL'}] {text}")


def line(n):
    return json.loads((CASE / 'native-events.jsonl').read_text().splitlines()[n - 1])


def main():
    exposure = json.loads((CASE / 'exposure.json').read_text())
    revs = {p.stem.replace('revision_', ''): json.loads(p.read_text())
            for p in (CASE / 'runtime' / 'workspace-revisions').glob('*.json')}
    edited = next(r for r, d in revs.items() if d['changed_paths'] == ['more_itertools/more.py'])
    initial = next(r for r, d in revs.items() if not d['changed_paths'])

    print('Step 1. The test process loads the original source and pauses.')
    print('        files: case/.../exposure.json, native-events.jsonl line 13')
    check(exposure['loaded'] and exposure['selected_items'] == ['tests/test_more.py::ChunkedTests::test_even'],
          'the collection plugin saw the target module loaded for the selected test')
    check(exposure['source_sha256'].startswith('1bdc5f323ea1'),
          f"source hash at load time: {exposure['source_sha256'][:12]} (original)")
    l13 = line(13)
    check(l13['params'].get('itemId') == 'fixture-test' and l13['params'].get('delta') == 'IMPORTED\n',
          'native event 13: test command prints IMPORTED (module loaded, process still running)')

    print('\nStep 2. Another command writes the faulty source; then the old process passes.')
    print('        files: native-events.jsonl lines 17 and 26, runtime/workspace-revisions/')
    e17 = line(17)['params']['item']
    check(e17['id'] == 'fixture-edit' and e17['exitCode'] == 0 and e17.get('aggregatedOutput') == 'MUTATION_DONE\n',
          'native event 17: the fault write completes')
    patch = (CASE / 'runtime' / 'workspace-revisions' / f'revision_{edited}.patch').read_text()
    check('AUDIT_INJECTED_REGRESSION' in patch,
          f'MemTrace records the write as revision {edited[:12]} (patch raises AUDIT_INJECTED_REGRESSION)')
    e26 = line(26)['params']['item']
    check(e26['id'] == 'fixture-test' and e26['exitCode'] == 0 and '1 passed' in e26.get('aggregatedOutput', ''),
          'native event 26: the test that loaded the original source exits 0 with "1 passed"')
    check(line(32)['method'] == 'turn/completed', 'native event 32: the turn completes')

    print('\nStep 3. MemTrace stores that pass as evidence for the EDITED revision.')
    print('        file: runtime/v2-state.sqlite3, table v2_semantic_evidence')
    db = sqlite3.connect(f"file:{CASE / 'runtime' / 'v2-state.sqlite3'}?mode=ro&immutable=1", uri=True)
    row = db.execute("select revision_id, valid_from_revision, valid_to_revision, content_json "
                     "from v2_semantic_evidence where evidence_type='TEST_RESULT'").fetchone()
    content = json.loads(row[3])
    check(content['success'] and content['exit_code'] == 0 and content['criterion_ids'] == ['C1'],
          'stored TEST_RESULT: success, exit 0, attached to required criterion C1')
    check(row[0] == f'revision_{edited}' and row[1] == f'revision_{edited}',
          f'bound to revision {edited[:12]} (the faulty one), not {initial[:12]} (the one the test ran)')
    check(row[2] is None, 'validity interval is open (no end revision)')

    print('\nStep 4. The reducer declares completion, but the final source fails the same test.')
    print('        files: result.json, oracle.xml, final-source/more.py')
    res = json.loads((CASE / 'result.json').read_text())
    ret = res['returned']
    check(ret['completion_verdict'] == 'COMPLETED' and ret['milestone_statuses'] == {'M001': 'COMPLETED_VERIFIED'},
          'reducer result: COMPLETED, milestone M001 COMPLETED_VERIFIED')
    oracle = (CASE / 'oracle.xml').read_text()
    check(re.search(r'failures="1"', oracle) and 'AUDIT_INJECTED_REGRESSION' in oracle,
          'fresh rerun of tests/test_more.py::ChunkedTests::test_even on the final source: 1 failure')
    final = hashlib.sha256((CASE / 'final-source' / 'more.py').read_bytes()).hexdigest()
    check(final.startswith('41a129a87dc6'), f'final source hash: {final[:12]} (faulty)')
    check(res['model_calls'] == 0 and res['live_native_transport'],
          'native Codex transport was live; tool requests were scripted (no model inference)')

    print(f"\nstatus: {'pass' if OK else 'FAIL'}")
    sys.exit(0 if OK else 1)


if __name__ == '__main__':
    main()
