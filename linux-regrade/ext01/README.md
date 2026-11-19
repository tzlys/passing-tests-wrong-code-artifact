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
- **2026-11-19, 03:05.** The second launch stopped during host setup again.
  Ubuntu's main archive served an inconsistent index: `python3-venv` required an
  older `python3` than the image had, and `libonig5` was not installable. No data
  had been downloaded. The host now runs Amazon Linux 2023 with Amazon's own
  repositories (`setup_host_al2023.sh`: docker, git, python3.11), using the same
  SWE-bench v4.1.0 release. Every harness run happens inside the official
  SWE-bench images, so the host OS does not affect test outcomes.
- **2026-11-19, 11:00. Docker Hub pull failures in the first full run.**
  - **What happened.** Entries 1 and 3 ran completely. In entry 2, 7 records got
    no G log because the Docker API timed out while 12 workers pulled at once.
    In entries 4 to 7, every record failed with `No such image`: anonymous
    Docker Hub pulls are limited (100 per 6 hours per IP), and stage 2 deleted
    images after each entry, which forced extra pulls. Because these failures
    ran into the confirmation reruns, the 3 first-pass divergent records were
    never rerun. The reported "0 confirmed" therefore means "not confirmed",
    not "refuted".
  - **Correction** (`ext01_stage2b.sh`, `launch_ext01_shards.sh`). The work is
    split over three hosts, each with its own IP and pull quota:
    - shard A: entries 4 and 5;
    - shard B: entries 6 and 7;
    - shard C: entry 2, plus confirmation reruns of the first-run divergent
      records `1:django__django-12856` and `3:pallets__flask-4045`.

    Each shard pulls every needed image once, in sequence and with retries,
    before running the harness. It never prunes images and uses 6 workers.
  - **Merge rule**, fixed now, before any shard result exists
    (`ext01_merge.py`, `plan.json`). Each entry is taken whole from one source:
    - entries 1 and 3: first pass from the first run, reruns from shard C;
    - entry 2: everything from shard C;
    - entries 4 and 5: everything from shard A;
    - entries 6 and 7: everything from shard B.

    All sources must have byte-identical `sample.json` and `data/`.
  - **Unchanged.** Sampling, conditions and classification rules are as in the
    protocol.
