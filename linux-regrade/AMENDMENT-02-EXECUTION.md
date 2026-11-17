# AMENDMENT-02 execution note

- Written: 2026-11-16, about 23:20 America/New_York.
- This is after all three macOS pilot tasks were run and graded. No Linux
  step had been run yet.

What was fixed in advance (AMENDMENT-02, 2026-11-15, before any task reached
a model):
- official-harness grading of every final patch;
- a Linux serial recheck of the recorded passing test-like commands;
- reporting rules:
  - the Linux `resolved` value is the reference;
  - a cross-platform disagreement is reported per task;
  - the primary outcome and the gate stay determined on macOS.

What is decided only now:
- **Scripts.** `run_regrade.sh`, `linux_recheck.py`, `compare.py`,
  `check_dataset.py` and `make_predictions.py`. They are committed to this
  public repository before any Linux run, so the git history timestamps them.
- **Harness.** SWE-bench `v4.1.0`, the release whose specs macOS admission
  used.
- **Dataset.** `princeton-nlp/SWE-bench_Lite`, test split. Its
  FAIL_TO_PASS and PASS_TO_PASS lists are checked against the sealed oracle.
- **Reference patches.** They are also graded, as a harness sanity check.
- **Recheck rewrite rule.**
  - The leading `/bin/zsh -lc` becomes `bash -c`.
  - The macOS repository path becomes `/testbed`.
  - Every other path is unchanged.
  - Commands that need a file outside the repository, or a tool missing
    from the image (zsh, rg), are expected to differ. They are reported
    as such.

Not done:
- no model call;
- no change to any macOS record;
- no new task.
