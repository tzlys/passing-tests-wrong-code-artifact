# EXT-01: agents' own tests against the reference fix (public SWE-bench Lite patches)

- `EXT-01-PROTOCOL.md`: the pre-registered protocol. It was committed before any data was downloaded.
- `entries.txt`: the 24 submission entries, and `experiments-repo-commit.txt`: the `SWE-bench/experiments` commit they were read from.
- `ext01_screen.py`: downloads public patches, applies the inclusion rules and draws the deterministic sample.
- `ext01_stage1.sh` (screening) and `ext01_stage2.sh` (harness runs, reruns and analysis).
- `ext01_analyze.py`: the analysis. It reads the harness's own parsed test statuses.
- `launch_ext01_from_mac.sh` and `fetch_ext01_to_mac.sh`: start the run on AWS, and later fetch the results and clean up. The Mac does not need to stay awake in between.

No model is called.

## Infrastructure corrections (no change to the protocol)

- **2026-11-19, 02:40.** The first launch stopped during host setup because the
  regional EC2 Ubuntu mirror returned 503, so `python3-venv` could not be
  installed. No data had been downloaded and no harness run had started.
  `setup_host.sh` now retries apt and falls back to `archive.ubuntu.com`.
