# When Passing Tests Support the Wrong Code: review artifact

This is the reviewer artifact for the AGENT 2027 submission *When Passing
Tests Support the Wrong Code: A Controlled Audit of Agent Evidence*. It
supports the paper's claims in three layers, from quickest to most complete:

1. **One case, four steps (start here, about 5 minutes).** The saved records of
   one primary case show the failure from start to finish. Reading them needs
   no setup. `show_case.py` checks every step in about one second.
2. **Natural-task pilot (Section V, Table III).** `stage-b-review-artifact.tar.gz`
   is a release asset. Its `review_stage_b.py` recomputes Table III from the raw
   receipts and verifies every seal.
3. **Full original packages (Sections III–IV, Tables I–II).** These are shared
   through a private review link, listed under [Full packages](#full-packages).

No step needs an account, credentials, network access, a model call or a GPU.

---

## One case, four steps

**The case.** Upstream more-itertools test `ChunkedTests.test_even`, run
against `chunked` at pin `4aeb4338`. The scenario is the overlapping fault;
the policy is the original MemTrace policy (paper Section III-A). Every file
below is a byte-identical copy of the saved record; see
[`PROVENANCE.json`](case/more-chunked-pass-then-break-original/PROVENANCE.json).

```
python3 -B show_case.py      # standard library only; prints each step and "status: pass"
```

### Step 1. The test loads the original source and pauses

- **Load record.** [`exposure.json`](case/more-chunked-pass-then-break-original/exposure.json)
  is written by a log-only collection plugin. It records that the selected
  test's target module was loaded, and the source hash at that moment:

  ```
  "selected_items": ["tests/test_more.py::ChunkedTests::test_even"],
  "loaded": true,
  "source_sha256": "1bdc5f323ea1…"          ← original source
  ```

- **Native event.** Line 13 of
  [`native-events.jsonl`](case/more-chunked-pass-then-break-original/native-events.jsonl)
  is the test command printing `IMPORTED`. The process is still alive and
  waits for the writer.

### Step 2. Another command writes the fault, then the old process passes

- **Line 17:** command `fixture-edit` completes with exit 0 and prints
  `MUTATION_DONE`. MemTrace records the write as revision `f5b1a258…`. Its
  [patch](case/more-chunked-pass-then-break-original/runtime/workspace-revisions/)
  replaces the body of `chunked` with:

  ```diff
  +    raise RuntimeError("AUDIT_INJECTED_REGRESSION")
  ```

- **Line 26:** the *same* test process, which loaded the original source,
  exits 0 with `1 passed`.
- **Line 32:** the turn completes.

### Step 3. MemTrace stores that pass as evidence for the edited revision

In [`runtime/v2-state.sqlite3`](case/more-chunked-pass-then-break-original/runtime/),
table `v2_semantic_evidence` contains:

| field | value |
|---|---|
| `evidence_type` | `TEST_RESULT` (success, exit 0, criterion `C1`) |
| `revision_id` / `valid_from_revision` | `revision_f5b1a258…`, the **faulty** revision |
| `valid_to_revision` | `NULL` (open validity) |

The test actually ran revision `160df338…`, the original, which has no
changed paths.

### Step 4. The reducer declares completion; the final source fails the same test

- **Reducer result.** [`result.json`](case/more-chunked-pass-then-break-original/result.json)
  reports `completion_verdict: COMPLETED`, with milestone `M001` at
  `COMPLETED_VERIFIED`.
- **Fresh rerun.** [`oracle.xml`](case/more-chunked-pass-then-break-original/oracle.xml)
  reruns `tests/test_more.py::ChunkedTests::test_even` on the final source and
  gets `failures="1"` with `RuntimeError: AUDIT_INJECTED_REGRESSION`.
- **Final source.** [`final-source/more.py`](case/more-chunked-pass-then-break-original/final-source/more.py)
  has hash `41a129a87dc6…`.

The native Codex transport was live. Tool requests came from a scripted local
provider, with no model inference (`model_calls: 0`), as described in
Section III-A.

The other seven primary cases have the same structure. The full primary
package reconstructs all eight, plus the 24 stable controls, the guard and
serial controls, and the selector/seed sensitivity runs.

---

## Natural-task pilot (Section V)

Download `stage-b-review-artifact.tar.gz` from the latest release, then run:

```
tar xzf stage-b-review-artifact.tar.gz && cd stage-b-review-artifact
python3 -I -B review_stage_b.py     # about one second; prints Table III and "status: pass"
```

The script:
- verifies the 45 hashes in the five seals;
- recomputes every Table III value from the native events, executed-source
  logs, source-hash poll and grading logs, using the sealed classifiers;
- compares each value with the analysis written at run time;
- lists every command that named a path outside the task repository, for the
  manual exposure audit.

Read `README.md`, `RESULTS-PILOT.md` and `EXPOSURE-AUDIT-ALL.md` inside the
package for the protocol, corrections and verdicts. The model sessions
themselves cannot be replayed.

## Full packages

The three original review packages, bundled with one wrapper, are
`integrated-review-artifact.tar.gz` (SHA-256 `d21cc933…a6596`):
- the primary MemTrace study;
- the supplemental Assay study;
- the known-fix ablation.

Run them with:

```
python3.11 -B review_all.py --output /absolute/new/review-results
```

This bundle is shared through a private review link rather than this public
repository. It contains saved copies of third-party web pages and one pinned
third-party source tree (autoMRE) that carries no license file, so we do not
redistribute it publicly.

Private review link: **(added before submission)**

## Limits

These hold as stated in the paper:
- The primary faults are injected, under forced schedules.
- Assay's full expansion gate was not met.
- The natural pilot has two analyzable tasks of three and gives no
  occurrence rate.
- Native replay needs macOS ARM, the pinned Codex binary and Python 3.12.14.
  Offline review needs Python 3.11 (primary package) or any Python 3.9+
  (`show_case.py`, Stage B).

## Licenses

- Scripts and documentation in this repository: MIT.
- Saved records: CC BY 4.0.
- `final-source/more.py` comes from more-itertools (MIT), with its notice in
  [`third_party/more-itertools-LICENSE`](third_party/more-itertools-LICENSE).
- Stage B contains code from requests (Apache-2.0) and Flask (BSD-3-Clause).
  These come inside the model's final repository snapshots, and inside the
  SWE-bench task patches (SWE-bench: MIT).
