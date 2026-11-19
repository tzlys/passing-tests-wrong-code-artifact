"""Check every record-level fact that TAXONOMY-CODING.md cites for the natural pilot.

    python3 -I verify_taxonomy.py <extracted stage-b-review-artifact dir>

This is a mechanical second pass over the coding. Each check reads only the
Stage B package and prints PASS or FAIL. It checks that the cited records say
what the coding says they say. It cannot check whether a class is the right
interpretation of those records; that remains a judgment, and the judgment is
documented in TAXONOMY-CODING.md.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
R, F1, F2 = 'psf__requests-3362', 'pallets__flask-4045', 'pallets__flask-4992'
results = []


def events(task):
    return (ROOT / 'runs' / task / 'observable-events.jsonl').read_text().splitlines()


def item(task, i):
    d = json.loads(events(task)[i])
    assert d.get('method') == 'item/completed', f'{task} ev.{i} is not a completed item'
    return d['params']['item']


def text_of(it):
    if it.get('type') == 'userMessage':
        return ''.join(c.get('text', '') for c in it['content'])
    if it.get('type') == 'fileChange':
        return json.dumps(it.get('changes'))
    return it.get('command') or it.get('text') or ''


def check(cls, name, fn):
    try:
        ok, detail = fn()
    except Exception as e:  # a missing record counts as a failure
        ok, detail = False, f'{type(e).__name__}: {e}'
    results.append((cls, name, ok, detail))


def cmd(task, i, *needles, exit_code=None):
    it = item(task, i)
    t = text_of(it)
    ok = it.get('type') == 'commandExecution' and all(n in t for n in needles)
    if exit_code is not None:
        ok = ok and it.get('exitCode') == exit_code
    return ok, f"exit={it.get('exitCode')} {t[:90]!r}"


def msg(task, i, kind, *needles):
    it = item(task, i)
    t = text_of(it)
    return it.get('type') == kind and all(n in t for n in needles), f'{t[:90]!r}'


# O3 check outside the repository (F1)
FILE = '/private/tmp/flask-4045-blueprint-verification/test_nested_blueprints.py'
check('O3', 'F1 ev.126 writes the out-of-repo test file, exit 0',
      lambda: cmd(F1, 126, f'cat > {FILE} <<', exit_code=0))
check('O3', 'F1 ev.130 runs it with pytest, exit 0',
      lambda: cmd(F1, 130, 'pytest', FILE, exit_code=0))
check('O3', 'F1 final patch does not contain the file',
      lambda: ('test_nested_blueprints.py' not in (ROOT / 'runs' / F1 / 'final.patch').read_text(), 'absent'))

# B3 hidden exit status (F1, F2), caught by MemTrace
check('B3', 'F1 ev.91 pytest followed by "; rg" (pytest exit hidden), exit 0',
      lambda: cmd(F1, 91, 'pytest -q tests/test_blueprints.py::test_dotted_names; rg', exit_code=0))
check('B3', 'F1 ev.117 MemTrace reports UNRELIABLE_EXIT_STATUS',
      lambda: msg(F1, 117, 'userMessage', 'UNRELIABLE_EXIT_STATUS'))
check('B3', 'F2 ev.97 pytest redirected, then "; tail" (exit 0)',
      lambda: cmd(F2, 97, 'pytest', '> /tmp/flask-4992-pytest.log', '; tail -65', exit_code=0))
check('B3', 'F2 ev.97 output shows failures despite exit 0',
      lambda: (lambda o: (bool(re.search(r'\b7 failed\b', o)), o[-80:]))(item(F2, 97).get('aggregatedOutput') or ''))
check('B3', 'F2 ev.132 MemTrace reports UNRELIABLE_EXIT_STATUS',
      lambda: msg(F2, 132, 'userMessage', 'UNRELIABLE_EXIT_STATUS'))

# A1 behavior (R)
check('A1', 'R ev.65 agent observes that streaming yields bytes without an encoding',
      lambda: msg(R, 65, 'agentMessage', 'leaves `r.encoding` unset', 'Streaming then yields bytes'))
check('A1', 'R ev.126 final message documents bytes when no encoding is known',
      lambda: msg(R, 126, 'agentMessage', 'no known encoding still yield'))
HIDDEN_R = ("+        r.raw = io.BytesIO(b'the content')\n"
            "+        r.encoding = None\n"
            "+        chunks = r.iter_content(decode_unicode=True)\n"
            "+        assert all(isinstance(chunk, str) for chunk in chunks)\n")
check('A1', 'R hidden test: same input b"the content", encoding None, asserts str',
      lambda: (HIDDEN_R in (ROOT / 'oracle' / R / 'test_patch.diff').read_text(), 'test_patch.diff'))

# A2 scope (F1)
check('A2', 'F1 reference patch also rejects dotted endpoint names',
      lambda: ("'endpoint' may not contain a dot" in (ROOT / 'oracle' / F1 / 'patch.diff').read_text(), 'patch.diff'))
check('A2', 'F1 final patch has no endpoint check',
      lambda: ("'endpoint' may not contain" not in (ROOT / 'runs' / F1 / 'final.patch').read_text(), 'final.patch'))

# A3 interface (F2)
check('A3', 'F2 final patch adds a mode parameter',
      lambda: ('mode' in (ROOT / 'runs' / F2 / 'final.patch').read_text(), 'final.patch'))
check('A3', 'F2 reference adds text: bool',
      lambda: ('text: bool = True' in (ROOT / 'oracle' / F2 / 'patch.diff').read_text(), 'patch.diff'))

# A4 own test encodes its reading
fp = lambda t: (ROOT / 'runs' / t / 'final.patch').read_text()
check('A4', 'R adds test_response_decode_unicode_without_encoding asserting bytes',
      lambda: ("def test_response_decode_unicode_without_encoding" in fp(R)
               and "b''.join(r.iter_content(decode_unicode=True)) == b'the content'" in fp(R), 'final.patch'))
check('A4', 'R narrows the docstring of test_response_decode_unicode',
      lambda: ('-        When called with decode_unicode, Response.iter_content should always' in fp(R)
               and '+        With an encoding set, decode_unicode makes Response.iter_content' in fp(R), 'final.patch'))
check('A4', 'R ev.84 is the file change that adds it',
      lambda: msg(R, 84, 'fileChange', 'test_response_decode_unicode_without_encoding'))
check('A4', 'R ev.112 passing run selects the decode_unicode tests, exit 0',
      lambda: cmd(R, 112, "-k 'decode_unicode", exit_code=0))
check('A4', 'F1 test_dotted_names asserts ValueError for dotted blueprint names',
      lambda: ("+def test_dotted_names(name):" in fp(F1) and "'name' may not contain a dot" in fp(F1), 'final.patch'))
check('A4', 'F2 tests pass mode= to from_file',
      lambda: ('def test_config_from_file_mode' in fp(F2) and 'mode="b"' in fp(F2), 'final.patch'))
check('A4', 'F2 test named test_config_from_file_toml, same name as the hidden test',
      lambda: ('+def test_config_from_file_toml(' in fp(F2)
               and 'test_config_from_file_toml' in (ROOT / 'oracle' / F2 / 'FAIL_TO_PASS.json').read_text(), 'final.patch + oracle'))

# A5 environment blocks part of the suite
adm = lambda t: (ROOT / 'admission' / t / 'tests-base.txt').read_text()
check('A5', 'R base admission shows 108 errors',
      lambda: (lambda m: (bool(m) and m[-1] == '108', m[-1:] if m else None))(re.findall(r'(\d+) error', adm(R))))
check('A5', 'R ev.116 agent reports environment limits',
      lambda: msg(R, 116, 'agentMessage', 'environment limits'))
check('A5', 'F1 base admission: 38 FAILED in test_blueprints.py',
      lambda: (lambda n: (n == 38, n))(len(re.findall(r'^FAILED tests/test_blueprints\.py', adm(F1), re.M))))
check('A5', 'F1 ev.83 blueprint suite fails in session, exit 1',
      lambda: cmd(F1, 83, 'pytest -q tests/test_blueprints.py', exit_code=1))
check('A5', 'F1 ev.102 Werkzeug-client substitute, exit 0',
      lambda: cmd(F1, 102, 'from werkzeug.test import Client', exit_code=0))
check('A5', 'F2 ev.106 failures persist with original config.py (7 failed)',
      lambda: (lambda it: ('git\', \'show\', \'HEAD:src/flask/config.py' in text_of(it)
                           and bool(re.search(r'\b7 failed\b', it.get('aggregatedOutput') or '')), f"exit={it.get('exitCode')}"))(item(F2, 106)))

width = max(len(n) for _, n, _, _ in results)
for cls, name, ok, detail in results:
    print(f"{'PASS' if ok else 'FAIL'}  {cls:3} {name:<{width}}  {detail}")
bad = sum(not ok for *_, ok, _ in results)
print(f'\n{len(results) - bad}/{len(results)} checks pass')
sys.exit(1 if bad else 0)
