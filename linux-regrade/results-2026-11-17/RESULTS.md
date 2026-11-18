# AMENDMENT-02 Linux regrading: results (2026-11-17)

This run executed the procedure fixed in AMENDMENT-02 with no model involved. It used repository commit `968ef2a` (`repo-commit.txt`).

| | |
|---|---|
| Host | AWS EC2 m5.xlarge, Ubuntu 22.04 x86_64, us-east-2. Ran about 4 minutes, then terminated. |
| Harness | SWE-bench v4.1.0 (tag, commit `726c5461`) |
| Dataset | `princeton-nlp/SWE-bench_Lite`, test split, revision `6ec7bb89` |
| Images | Official `swebench/sweb.eval.x86_64.*` instance images; digests in `images.txt` |

## Dataset check (`dataset-check.json`)

For all three tasks, the FAIL_TO_PASS and PASS_TO_PASS lists equal the sealed oracle used on macOS. The base commits match as well.

## Official harness

The model patches resolve 0 of 3 tasks; the reference patches resolve 3 of 3. The harness reported no errors and no empty patches.

| Task | Model F2P pass/fail | Model P2P pass/fail | Gold F2P | Gold P2P | Agrees with macOS |
|---|---|---|---|---|---|
| psf__requests-3362 | 0 / 1 | 75 / 0 | 1 / 0 | 75 / 0 | yes |
| pallets__flask-4045 | 1 / 1 | 50 / 0 | 2 / 0 | 50 / 0 | yes |
| pallets__flask-4992 | 0 / 1 | 18 / 0 | 1 / 0 | 18 / 0 | yes |

The F2P test that fails on Linux is the same one that failed on macOS:

- `test_response_decode_unicode` (requests-3362)
- `test_route_decorator_custom_endpoint_with_dots` (flask-4045)
- `test_config_from_file_toml` (flask-4992)

## Linux serial recheck (`linux-recheck.json`)

The recheck covers 16 command rows, each run twice as run and twice with source forced, inside the official image. 15 rows give the same exit codes as macOS. In all 16 rows, the as-run exit codes equal the source-forced ones.

The one difference is in flask-4045. The command `pytest /private/tmp/flask-4045-blueprint-verification/test_nested_blueprints.py` exited 0 on macOS and 4 on Linux. Exit 4 is pytest's "file not found": the test file was written outside the repository on the Mac and does not exist in the container. `AMENDMENT-02-EXECUTION.md` predicted this before the run.

## Note on `linux_tree_matches_final_patch = false`

All three final patches applied with `git apply` exit 0. `git apply` without `--3way` refuses any hunk whose context does not match. The only warnings were file-mode mismatches: in the image the files are mode `100755`, while the patch expects `100644`.

The check compares the bytes of the post-apply `git diff` with the bytes of the patch file. Mode lines and diff-header formatting (the macOS patch was produced with `git diff --binary`) can make those bytes differ even when the content is identical. The post-apply diff text was not retained, so this explanation is likely but not verified. The paper makes no claim that depends on this field.

## Reports

`reports/` holds the per-instance harness `report.json` files, copied out of the harness's deep `logs/run_evaluation/...` tree. `stageb.stageb-model.json` and `gold.stageb-gold.json` are the harness run summaries.

The gold run's `submitted_instances: 300` is expected: the harness loads the gold predictions for the whole Lite split and evaluates only the three selected instance ids.

## SUPPLEMENT-01 (2026-11-18, post-hoc): the out-of-repository row

This supplement was added after the results above were known, so it is reported
separately from AMENDMENT-02 and does not change the result recorded above.

**Setup.**
- The test file the model wrote to `/private/tmp` was recovered byte for byte
  from the session record: `observable-events.jsonl` line 126 (0-based) in the
  flask-4045 run. SHA-256 of the macOS text: `2982462d…`.
- The AMENDMENT-02 path rule was applied to the file text: the macOS
  repository path was replaced with `/testbed`. SHA-256 of the Linux text:
  `260692f2…`; the hash of the file inside the container matches.
- Image and patch were the same as in AMENDMENT-02. The image digest matches,
  and `git apply` exited 0.
- Code version: repository commit `fcf3392`.

**Result.**

| Run | as run | source-forced |
|---|---|---|
| macOS session recheck | 0, 0 | 0, 0 |
| Linux, file absent (negative control) | 4, 4 | 4, 4 |
| Linux, file restored | 0, 0 | 0, 0 |

The negative control reproduces the AMENDMENT-02 difference: pytest reports
"file or directory not found". With the file restored, all four runs pass
(`1 passed`), the same as on macOS. All 16 recheck rows therefore agree with
macOS: 15 directly, and 1 after this post-hoc restore.

Files: [`../supplement-01-2026-11-18/`](../supplement-01-2026-11-18/).

