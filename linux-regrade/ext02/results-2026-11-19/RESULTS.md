# EXT-02 results (2026-11-19)

The protocol is in [`../EXT-02-PROTOCOL.md`](../EXT-02-PROTOCOL.md). Two commits came
before the data:

- the pre-registration, `6f1e329`, made before any trajectory download;
- the extractors, `2d0d1a2`, made after Stage 0, which saw only masked structure,
  and before Stage 1.

The author ran Stage 1 on the Mac. It used anonymous HTTPS reads, and no model was
called.

## Funnel

| Step | Count |
|---|---|
| Entries | 24 |
| Entries with `trajs/` objects | 16 |
| Entries whose format exposes agent shell commands | 8: SWE-agent ×6, OpenDevin CodeAct v1.8, OpenHands CodeAct 2.1 |
| Sampled instances (≤ 40 per entry) | 601 |
| Instances with at least one extracted shell action | 305 |
| ... of which ran a test runner (T) | 75 |
| Objects over 20 MB, skipped | 12 |

The 75 trajectories that ran a test runner are concentrated. Thirty-seven of them
come from one entry, `20250526_sweagent_claude-4-sonnet-20250514`. Most other agents
check their work with ad-hoc reproduction scripts rather than test runners.

## Metrics (pre-registered definitions)

| Metric | Link | k / n | Rate | Wilson 95% CI | Entries with a match |
|---|---|---|---|---|---|
| M1: test exit status hidden by a later command | 3 | 7 / 75 | 9.3% | 4.6–18.0% | 2 of 8 |
| M2: test run in the background | 2 | 0 / 75 | 0% | 0–4.9% | 0 of 8 |
| M3: non-editable install of the repository | 1 | 1 / 305 | 0.3% | 0.1–1.8% | 1 of 8 |

- The median per-entry rate is 0 for all three metrics.
- Six of the seven M1 matches come from the SWE-agent Claude 4 entry, and one from
  SWE-agent Claude 3.7.

## Prediction

| Metric | Prediction | Outcome |
|---|---|---|
| M1 | above 10% | **Not met** (9.3%) |
| M2 | below 5% | Met (0%) |
| M3 | below 5% | Met (0.3%) |

## Precision check

Every match was checked, because each metric had at most 20. There was one coder,
the AI assistant, working under the author's delegation.

- **M1 (7 matches).**
  - All 7 fit the definition: a test-runner segment followed by `| grep`,
    `| head` or `| tail`.
  - Six are real test runs, through Django `runtests.py` or pytest.
  - One is `python -m pytest --help | grep …`. It invokes the runner but does not
    run tests.
  - Substantive precision is therefore 6/7 = 0.86, which is at least the 0.8
    threshold.
- **M2.** No matches.
- **M3 (1 match).** `python setup.py install` in SWE-agent Claude 3 Opus,
  sphinx-8801. It is correct.

## Reading

- **Link 3, exit status hidden.** The precondition recurs in public agents, as it
  did in our pilot (F1, F2). It is concentrated in one agent. MemTrace already
  rejects such evidence, as it did in the pilot.
- **Link 2, background test runs.** None were found. The SWE-agent, OpenDevin and
  OpenHands harnesses in this sample run commands sequentially, so explicit
  backgrounding is the only route to an overlap there. This result does not speak
  to harnesses that run commands concurrently, such as the Codex sessions in which
  our pilot observed three overlaps.
- **Link 1, non-editable install.** Rare: one in 305.
- **Overall.** This scan does not show that the preconditions of links 1–3 are
  common in these public agents. It shows that the link-3 precondition occurs
  naturally, mostly in one agent, and that the link-1 and link-2 preconditions are
  rare or absent in sequential harnesses.

## Decision on the paper

To be decided by the author. The assistant's recommendation is not to add this to
the 5-page paper. Reporting all three metrics honestly takes about four lines, and
the M2 null invites a misreading about concurrent harnesses that needs further
space to explain. The study stays here as a pre-registered, public result for the
extended version.
