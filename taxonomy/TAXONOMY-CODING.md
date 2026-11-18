# How a passing test can support the wrong code: post-hoc taxonomy coding

**Status: post-hoc.** This coding was done on 2026-11-18, after every grading
result was known. It was not part of any sealed protocol. Claude Opus 5.5 proposed the
classes and did the coding. Author review is pending. It assigns observed
behavior to classes. It estimates no rates.

## Classes

The classes follow the four links the paper asks an integrator to check. A
case belongs to a class when the saved records show the behavior directly.
Interpretation alone is not enough.

| Link | Class | Meaning |
|---|---|---|
| L1 What ran | O1 alternate source copy | The test imported another copy of the target source. |
| | O2 unchecked cached bytecode | The test ran cached bytecode that does not match the current source. |
| | O3 check outside the repository | The passing check is a file that is not in the final repository state. |
| L2 When it ran | T1 write during the test | The source changed after the test loaded it and before the test returned. |
| L3 What was recorded | B1 pass bound to another revision | The stored evidence names a revision that the test did not run. |
| | B2 evidence names a test that did not run | The recorded selector differs from the executed test. |
| | B3 hidden exit status | A pipe or command sequence hid the test runner's own exit code. |
| L4 What the pass shows | A1 intent differs: behavior | The code does something the hidden intent rejects. |
| | A2 intent differs: scope | The code covers only part of the intended change. |
| | A3 intent differs: interface | The code exposes the intended behavior under a different interface. |
| | A4 the agent's own test encodes its reading | A test written in the session asserts the agent's interpretation. |
| | A5 the environment blocks the relevant suite | Tests fail in the provided environment before the change, so the agent relies on a narrower check. |

## Constructed cases (paper Sections III and IV)

| Class | Cases | Outcome | Control that stops it |
|---|---|---|---|
| T1 + B1 | MemTrace, 8 injected faults | 8 false completions | observed-write guard; quiescent serial final (8/8 each) |
| B2 | MemTrace, 4 mismatched-selector stable cases | 4/4 blocked by MemTrace | built in |
| O1 | Assay, 3 alternate-copy faults | 3 accepted claims | source-first import (3/3) |
| O2 | Assay, 3 unchecked-cache faults | 3 accepted claims | cache purge with no writes (3/3) |

## Natural pilot (paper Section V; 3 tasks, gpt-6.1-sol, MemTrace learned planning)

Event numbers are 0-based line indices in `runs/<task>/observable-events.jsonl`
of the Stage B package.

| Class | requests-3362 | flask-4045 | flask-4992 | Evidence |
|---|---|---|---|---|
| O1, O2, T1, B1 | not observed | not observed | not observed | Table III: no temporal or origin mismatch; 3 processes overlapped a write without a mismatch |
| O3 | – | **yes** | – | 4045 ev. 126 writes `/private/tmp/.../test_nested_blueprints.py`; ev. 130 runs it (pass). SUPPLEMENT-01 restores the file in the official Linux image, where it passes 4/4; without the file, all 4 runs exit 4 |
| B3 | – | **flagged** | **flagged** | 4045 ev. 91 `pytest …; rg …`; 4992 ev. 97 `pytest … > log; tail -65 log` (exit 0 with 7 failures). MemTrace returned `UNRELIABLE_EXIT_STATUS` (4045 ev. 117, 4992 ev. 132), and the agent reran without the pipe. Caught, not accepted. |
| A1 behavior | **yes** | – | – | Without a known encoding, the agent keeps bytes (ev. 65, 126). The hidden test expects `str` |
| A2 scope | – | **yes** | – | The agent rejects dotted blueprint names. The reference also rejects dotted endpoint names; hidden test `test_route_decorator_custom_endpoint_with_dots` |
| A3 interface | – | – | **yes** | The agent adds `mode="b"`. The reference and the hidden test use `text=False` |
| A4 own test encodes its reading | **yes, contradicts hidden test** | yes | yes | 3362 ev. 84 adds `test_response_decode_unicode_without_encoding`, which asserts bytes when `encoding is None`. The hidden assertion added to `test_response_decode_unicode` asserts `str` for the same input. The same edit narrows that test's docstring from "should always return unicode" to "With an encoding set". The passing run at ev. 112 includes the agent's test |
| A5 environment blocks suite | yes | **yes, narrower substitute** | yes, checked against base | 3362: admission on base code in the same pinned environment shows 108 errors (fixture-dependent HTTP tests), and the agent reports missing test plugins (ev. 116). 4045: admission on base code shows 38 failures in `test_blueprints.py`. All except the hidden fail-to-pass test come from the pinned Werkzeug: its deprecation warnings are raised as errors, and with those ignored, the `as_tuple` client mismatch remains (ev. 83). the agent replaces Flask's test client with Werkzeug's client in a wrapper (ev. 102, 126). 4992: the agent swaps its `from_file` for the original and reruns the 7 failing cookie and session tests; all 7 still fail (ev. 106) |

### Notes on coding decisions

- **A5 is not counted as the agent wrongly dismissing failures.** In
  all three tasks the failures already occur on base code in the pinned
  SWE-bench environment, so attributing them to the environment was correct.
  The class records that the decisive evidence was narrower than the suite.
- **A4 is counted when a test the agent wrote passes and asserts its own
  interpretation.** It contributes to wrong acceptance only where the
  interpretation is wrong, which is all three tasks here.
- **B3 cases were caught by MemTrace.** They show that the guard works on
  natural input. They are not failures.
- **flask-4045 is inconclusive for the primary outcome** because of the
  exposure, but its records are complete. The classes above do not depend on
  the exposed paths.
