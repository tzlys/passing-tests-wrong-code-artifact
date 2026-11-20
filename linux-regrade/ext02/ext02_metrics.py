"""EXT-02 fixed metric definitions. Committed before any trajectory download; not edited after Stage 0."""
import re

OPS = re.compile(r"(\|\||&&|\||;|&)")
TEST_RUNNER = re.compile(
    r"""^(?:
        (?:\S*/)?py\.?test\b
      | (?:\S*/)?python[0-9.]*\s+(?:-\S+\s+)*-m\s+(?:pytest|unittest)\b
      | (?:\S*/)?tox\b
      | (?:\S*/)?nosetests\b
      | (?:\S*/)?python[0-9.]*\s+(?:-\S+\s+)*(?:\S*/)?runtests\.py\b
      | (?:\S*/)?runtests\.py\b
      | (?:\S*/)?python[0-9.]*\s+(?:-\S+\s+)*(?:\S*/)?manage\.py\s+test\b
      | (?:\S*/)?bin/test\b
      | (?:\S*/)?python[0-9.]*\s+(?:-\S+\s+)*(?:\S*/)?bin/test\b
    )""",
    re.X,
)
PREFIX = re.compile(r"^(?:(?:[A-Za-z_][A-Za-z0-9_]*=\S*\s+)|(?:timeout\s+\S+\s+)|(?:nohup\s+)|(?:env\s+))*")
INSTALL_NONEDIT = re.compile(
    r"""(?:^|\s)(?:python[0-9.]*\s+-m\s+)?pip[0-9.]*\s+install\b(?P<args>[^\n;&|]*)""", re.X)
SETUP_INSTALL = re.compile(r"(?:^|\s)python[0-9.]*\s+setup\.py\s+install\b")


REDIR = re.compile(r"\d*>&\d*|&>>?|>&")


def _segments(line):
    """Split one line into [(segment_text, following_operator)] keeping operators.
    Redirections such as 2>&1, &> and >& are not operators."""
    line = REDIR.sub(" REDIR ", line)
    parts = OPS.split(line)
    out = []
    i = 0
    while i < len(parts):
        seg = parts[i]
        op = parts[i + 1] if i + 1 < len(parts) else ""
        out.append((seg.strip(), op))
        i += 2
    return out


def is_test_segment(seg):
    s = seg.strip()
    if s.startswith("(") or s.startswith("{"):
        s = s.lstrip("({ ")
    s = PREFIX.sub("", s)
    return bool(TEST_RUNNER.match(s)), seg.strip().startswith("nohup")


def analyze_action(action):
    """Return dict of booleans for one action string."""
    lines = [l for l in action.splitlines()]
    nonempty_idx = [i for i, l in enumerate(lines) if l.strip() and not l.strip().startswith("#")]
    res = {"T": False, "M1": False, "M2": False, "M3": False, "M1_lines": [], "M2_lines": [], "M3_lines": []}
    for li, line in enumerate(lines):
        if not line.strip() or line.strip().startswith("#"):
            continue
        pipefail = "pipefail" in line
        segs = _segments(line)
        for k, (seg, op) in enumerate(segs):
            # "cd X && pytest": the cd segment is its own segment, so T is checked per segment
            t, nohup = is_test_segment(seg)
            if not t:
                continue
            res["T"] = True
            rest = segs[k + 1:]
            masked = False
            if op == "|" and not pipefail:
                masked = True
            elif op == ";" and any(s for s, _ in rest):
                masked = True
            elif op == "||" and rest and re.match(r"^(true|:|echo\b)", rest[0][0] or ""):
                masked = True
            elif op in ("", "&") and any(i > li for i in nonempty_idx):
                masked = True
            if masked:
                res["M1"] = True
                res["M1_lines"].append(line.strip()[:300])
            if op == "&" or nohup:
                res["M2"] = True
                res["M2_lines"].append(line.strip()[:300])
        for m in INSTALL_NONEDIT.finditer(line):
            args = m.group("args")
            toks = args.split()
            if any(t in ("-e", "--editable") or t.startswith("--editable=") for t in toks):
                continue
            if any(t in (".", "./") or (t.startswith("/") and "site-packages" not in t and not t.endswith(".whl")) for t in toks):
                res["M3"] = True
                res["M3_lines"].append(line.strip()[:300])
        if SETUP_INSTALL.search(line):
            res["M3"] = True
            res["M3_lines"].append(line.strip()[:300])
    return res


def analyze_trajectory(actions):
    agg = {"T": False, "M1": False, "M2": False, "M3": False, "M1_lines": [], "M2_lines": [], "M3_lines": []}
    for a in actions:
        if not isinstance(a, str):
            continue
        r = analyze_action(a)
        for k in ("T", "M1", "M2", "M3"):
            agg[k] = agg[k] or r[k]
        for k in ("M1_lines", "M2_lines", "M3_lines"):
            agg[k].extend(r[k])
    return agg


if __name__ == "__main__":
    # self-test on synthetic commands (no trajectory data)
    cases = {
        "pytest tests/test_x.py | tail -20": (True, True, False, False),
        "pytest tests/test_x.py": (True, False, False, False),
        "cd /repo && python -m pytest -q tests && echo ok": (True, False, False, False),
        "python -m pytest tests; echo done": (True, True, False, False),
        "set -o pipefail; pytest | tail": (True, False, False, False),
        "pytest tests || true": (True, True, False, False),
        "pytest tests &": (True, False, True, False),
        "nohup pytest tests > log 2>&1 &": (True, False, True, False),
        "pytest tests 2>&1 | tail -30": (True, True, False, False),
        "pytest tests &> out.txt; cat out.txt": (True, True, False, False),
        "pytest a.py\nls": (True, True, False, False),
        "./tests/runtests.py queries 2>&1 | tail -5": (True, True, False, False),
        "python tests/runtests.py queries": (True, False, False, False),
        "bin/test sympy/core": (True, False, False, False),
        "pip install .": (False, False, False, True),
        "pip install -e .": (False, False, False, False),
        "python setup.py install": (False, False, False, True),
        "python setup.py develop": (False, False, False, False),
        "grep -r pytest .": (False, False, False, False),
        "echo pytest": (False, False, False, False),
        "PYTHONPATH=. timeout 60 pytest -x | head": (True, True, False, False),
    }
    ok = 0
    for cmd, exp in cases.items():
        r = analyze_action(cmd)
        got = (r["T"], r["M1"], r["M2"], r["M3"])
        flag = "OK " if got == exp else "BAD"
        ok += got == exp
        print(flag, repr(cmd), got, "expected", exp)
    print(f"{ok}/{len(cases)} self-tests pass")
