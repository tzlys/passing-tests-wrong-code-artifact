# EXT-01 results (2026-11-19)

**Protocol.** `../EXT-01-PROTOCOL.md`, committed at `dc37bd1` before any data was
downloaded.

**Merge plan.** `../plan.json`, committed at `40041fb` before any shard result
existed.

**Infrastructure corrections.** Listed in `../README.md`. They did not change
the protocol.

**What the runs cover.**
- The first full run is used for entries 1 and 3.
- Shards A, B and C are used for entries 2 and 4–7, and for every
  confirmation rerun.
- All four sources produced a byte-identical `sample.json` and `data/`;
  `ext01_merge.py` checks this.
- No model was called.

## Funnel

| Step | Count |
|---|---|
| Lite entries with `checked: true` and S3 logs | 24 |
| Entries with any logs under the expected S3 layout | 12 (the other 12 list no objects) |
| Entries with at least one included record | 7 |
| Sampled (per-entry caps 12 unresolved / 4 resolved) | 84 unresolved, 27 resolved |
| Valid (both conditions parsed, at least one test passing in M) | 30 unresolved, 15 resolved |
| Excluded: no test passes in M | 54 unresolved, 12 resolved |

Every exclusion in the final data is "no test passes in M": the agent's own
tests did not pass on its own code, or its test files contained no runnable
test. No exclusion is due to infrastructure.

## Main result

| Group | Valid | Divergent, first pass | Confirmed divergent | Rate | Wilson 95% | With an agent-added test (rule) |
|---|---|---|---|---|---|---|
| Unresolved | 30 | 11 | **11** | 0.367 | [0.219, 0.545] | 8 |
| Resolved | 15 | 2 | **2** | 0.133 | [0.037, 0.379] | 2 |

The rerun confirmed every first-pass divergence.

**Prediction check.** The pre-registered prediction was a higher confirmed
divergence rate among unresolved records. The rates point that way (36.7% vs
13.3%), but the 95% intervals overlap, so the difference is not established.

## Confirmed divergent records

Each row is a test that passes on the agent's own code and fails or errors on
the reference fix.

| Entry | Instance | Group | Kind | Note from G log and agent test diff (manual) |
|---|---|---|---|---|
| sweagent 3.5 | django-12856 | unres. | interface | Agent tests call `check_fields`, a method only the agent added |
| opendevin 1.8 | sklearn-10949 | unres. | message | Asserts the agent's warning wording |
| sweagent gpt-4o | flask-4045 | unres. | message | Expects the agent's own error message |
| Kortix | xarray-3364 | unres. | message | Expects the agent's own error message |
| sweagent 3.7 | sympy-22840 | unres. | behavior | Assertion differs |
| sweagent claude-4 | django-15819 | unres. | behavior | `related_name` format differs. Agent-added: Django names the test by its docstring, so the automatic rule missed it |
| sweagent claude-4 | django-11910 | unres. | behavior | Assertion differs |
| sweagent claude-4 | django-13230 | unres. | interface | Agent tests pass a keyword the reference handles differently (TypeError) |
| sweagent claude-4 | sympy-16281 | unres. | **existing test rewritten** | Agent deleted the expected output of `test_pretty_product` and replaced it with its own |
| sweagent claude-4 | sympy-19487 | unres. | **existing test extended** | Agent appended an assertion to `test_sign` |
| sweagent claude-4 | pytest-5413 | unres. | **existing test rewritten** | Agent replaced the assertions of `test_excinfo_str` with its new behavior |
| sweagent claude-4 | django-12856 | res. | message/detail | Check messages differ, although the hidden tests pass |
| sweagent claude-4 | sympy-21055 | res. | behavior | Reference raises on the assumptions the agent's test uses |

**Agent-added count.** By the protocol's automatic rule, 8 unresolved records
contain an agent-added divergent test. Manual inspection puts it at 9, because
of the Django docstring naming above. The paper reports the rule's count and
notes the manual one.

## Reading, within the protocol's limits

- In public patches from seven agent systems, about a third of the unresolved
  patches whose own tests pass carry a test that certifies agent-specific
  behavior that the reference fix does not have. In three of these the agent
  rewrote or extended a pre-existing test.
- Every run used a fresh container on a quiescent final tree, the setting that
  execution controls produce. The divergence therefore persists under those
  controls.
- Divergence also occurs in resolved patches (2 of 15). It shows that the
  agent's tests encode its own reading. By itself it does not show that the
  code is wrong.
- **Selection.** Only entries that keep test files are measurable. Most
  sampled records were excluded because the agent's own tests did not pass on
  its own code. Entries are leaderboard submissions, not a random sample of
  agents.
- **No trajectories.** This study does not show that the agent saw these
  tests pass during its run.

## Files

- `results-merged.json`: per-record classification, with the source of each entry.
- `RESULTS-EXT01-MERGED.md`: the merge script's output.
- `screen.json` and `sample.json`: the funnel and the sample.
- `progress-*.txt` and `repo-commit-*.txt`: logs and commits for the first run and each shard.
- `confirmed-logs.tar.gz`: for every confirmed record, the harness test output for M, G and both reruns, and the agent's test blocks.

## Post-hoc coding of the divergences

See [`DIVERGENCE-CODING.md`](DIVERGENCE-CODING.md). It covers what each confirmed divergent test encodes, a leave-one-submission-out rate and a Fisher test. It was added after the merged results and is not part of the pre-registered protocol.
