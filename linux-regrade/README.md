# Linux regrading of the natural-task pilot (AMENDMENT-02)

These scripts carry out AMENDMENT-02. That amendment was fixed on
2026-11-15, before any benchmark task reached a model. It is inside
`packages/stage-b-review-artifact.tar.gz`. The scripts below were written
after the macOS results, to execute that fixed procedure.

No model is called. Only the frozen final patches and the recorded commands
are used.

1. **Official SWE-bench harness, release v4.1.0.** The harness grades:
   - the three final patches;
   - the reference patches, as a sanity check.
2. **Linux serial recheck.** Every command that the macOS analysis rechecked
   is rerun inside the official instance image: twice as run and twice
   source-forced. The path rewrite rule is recorded in `linux-recheck.json`.
3. **Comparison.** `summary.json` compares the Linux results with the macOS
   records. Disagreements are reported, not resolved.

Host: Ubuntu 22.04 x86_64, at least 4 vCPU, 16 GB RAM and 100 GB disk.

```
git clone https://github.com/tzlys/passing-tests-wrong-code-artifact && cd passing-tests-wrong-code-artifact
bash linux-regrade/setup_host.sh && newgrp docker
bash linux-regrade/run_regrade.sh
```
