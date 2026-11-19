# EXT-01: agents' own tests against the reference fix (public SWE-bench Lite patches)

- `EXT-01-PROTOCOL.md`: the pre-registered protocol. It was committed before any data was downloaded.
- `entries.txt`: the 24 submission entries, and `experiments-repo-commit.txt`: the `SWE-bench/experiments` commit they were read from.
- `ext01_screen.py`: downloads public patches, applies the inclusion rules and draws the deterministic sample.
- `ext01_stage1.sh` (screening) and `ext01_stage2.sh` (harness runs, reruns and analysis).
- `ext01_analyze.py`: the analysis. It reads the harness's own parsed test statuses.
- `launch_ext01_from_mac.sh` and `fetch_ext01_to_mac.sh`: start the run on AWS, and later fetch the results and clean up. The Mac does not need to stay awake in between.

No model is called.
