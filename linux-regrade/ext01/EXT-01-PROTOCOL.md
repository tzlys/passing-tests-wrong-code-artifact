# EXT-01 protocol: do agents' own tests certify their misreading? (public SWE-bench Lite patches)

**Status.** Pre-registered on 2026-11-19, before any submission data was downloaded
or any run was made. This file and the scripts in this folder are committed to
the public repository before the first run, and the run records the commit it
used. The study is post-hoc with respect to the paper's sealed Stage B pilot.
It extends SUPPLEMENT-02 from 3 sessions to public agent patches. No model is
called.

**Deadline rule (set by the author).** If usable results are not in hand by
2026-11-20 12:00 America/New_York, EXT-01 is dropped from the AGENT 2027
submission. In that case the paper is submitted as snapshot `db5e4661`.

## Question

When an agent's final patch changes test files, do the tests it wrote pass on its
own code but fail on the reference fix? A test that does certifies the agent's
reading of the issue rather than the intended behavior (taxonomy class A4).

## How this study relates to the paper's three main risks

The paper's position is that it reproduces a known class of problem, verification
evidence that does not match the code, inside real agent evidence pipelines. It
supplies auditable end-to-end receipts and maps where existing controls apply. It
does not claim a new failure mode. EXT-01 is designed against the paper's three
main risks:

1. **The primary faults are constructed.** EXT-01 uses only natural, public agent
   patches: no fault is injected, and no schedule is forced.
2. **Existing controls prevent the primary faults.** Condition M is itself a
   strongest-case execution control. Each run starts in a fresh container, runs
   serially on a quiescent final tree, and imports the checkout's own source.
   This is the setting that the paper's write guard, serial final check and
   import/cache controls aim to produce. Any divergence found here therefore
   persists under those controls, and EXT-01 measures where their applicability
   ends.
3. **The natural pilot did not reproduce the primary binding failure.** EXT-01
   does not test binding, and no result here will be presented as evidence of
   binding failures. It tests only the fourth link: what a faithful pass shows.

## Population and inclusion

1. **Entries.** Every SWE-bench Lite entry in `SWE-bench/experiments` (HEAD at
   download time) whose `metadata.yaml` has `checked: true` and whose `assets.logs`
   is under `s3://swe-bench-submissions/lite/`. That is 24 entries, listed in
   `entries.txt`. No entry is added or removed after download.
2. **Instance records.** For each entry and instance, `logs/<instance_id>/patch.diff`
   and `logs/<instance_id>/report.json`, read anonymously from S3. Records missing
   either file, or with an unreadable `resolved` field, are excluded and counted.
3. **Splitting the patch.** Each `diff --git` block is a *test block* when:
   - its path has a `tests` directory component;
   - its first component is `testing` (pytest's own suite); or
   - its basename starts with `test_`, ends with `_test.py`, or is `conftest.py`.

   A bare `test/` directory or a nested `testing/` directory is library code in
   Lite repositories (`django/test/`, `sympy/testing/`), so it counts as source.
   All other blocks are *source blocks*.
4. **Inclusion.** A record is included when it has at least one test block that
   is a `.py` file and at least one source block.

## Sampling (deterministic)

Included records are ordered by `sha256("<entry>/<instance_id>")`, then taken in
order:
- **unresolved** records: at most 12 per entry, at most 160 in total;
- **resolved** records (control): at most 4 per entry, at most 60 in total.

## Conditions

Each condition runs in the official SWE-bench v4.1.0 harness with the official
`swebench` instance images. The harness's test patch is the agent's **test
blocks**. The harness's model patch differs by condition:

- **M**: the agent's **source blocks**.
- **G**: the reference fix, i.e. the dataset's `patch` field
  (`princeton-nlp/SWE-bench_Lite`, test split).

Test directives, the test command and log parsing are the harness's own:
`get_test_directives`, `MAP_REPO_VERSION_TO_SPECS` and `get_logs_eval`.
Timeout is 900 s per instance.

## Outcomes

- **Valid**: both conditions produce a parsed status map, and at least one test
  passes in M.
- **Divergent**: valid, and at least one test that passes in M fails or errors in
  G, or is absent from G's status map while G reports a failure.
- Each divergent test is labelled **agent-added** when its function name appears
  in a `+ def <name>(` line of the agent's test blocks, and **other** otherwise
  (pre-existing or modified without a changed `def` line).
- **Stability**: every divergent record is rerun once in both conditions.
  Divergence is **confirmed** only if it reproduces.

**Report**: counts at each inclusion step; confirmed divergence rates among valid
unresolved and valid resolved records, with Wilson 95% intervals; per-entry
counts; the agent-added share; and all exclusions with reasons.

## Prediction

The confirmed divergence rate is higher among unresolved than among resolved
records. No numeric prediction is made.

## Limits, stated in advance

- Entries are public leaderboard submissions, not a random sample of agents.
- Only patches that keep test files are visible. Agents that delete their tests
  before submitting cannot be measured.
- Divergence shows that the agent's tests encode behavior the reference fix does
  not have. It does not show that the agent saw those tests pass during its run,
  because trajectories are not analyzed here.
- One run plus one confirmation rerun per divergent record.
