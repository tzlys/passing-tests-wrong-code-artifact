# SUPPLEMENT-02 results: the model's own tests run against the reference fix

This supplement is post-hoc. The script and its predictions were committed at
`0258021` on 2026-11-18, before the first run, and the run used that commit
(`repo-commit.txt`). It used the official SWE-bench instance images, with the
same digests as AMENDMENT-02, and called no model. Every selected test ran
twice per condition, and the two runs agree for every case.

- **M**: base code plus the model's final patch.
- **G**: base code plus the reference source patch plus only the test files of
  the model's patch.

## Predictions against outcomes

| Task | Model-written test | Prediction (M / G) | Outcome (M / G) | |
|---|---|---|---|---|
| requests-3362 | `test_response_decode_unicode_without_encoding` | pass / fail | pass / **fail** | ✓ |
| | `test_get_encoding_from_headers`, case `application/json` → `utf-8` | pass / fail | pass / **fail** (AssertionError) | ✓ |
| | `test_get_encoding_from_headers`, other 5 cases | pass / pass | pass / pass | ✓ |
| | `test_response_decode_unicode` (docstring only) | pass / pass | pass / pass | ✓ |
| | `test_json_response_decode_unicode` (24 cases) | pass / none | pass / **6 fail** | not predicted |
| flask-4045 | `test_dotted_names` (4 cases) | pass / pass | pass / pass | ✓ |
| | `test_nested_blueprint` | fail / fail (environment) | fail / fail (TypeError in `__init__`, the Werkzeug client mismatch) | ✓ |
| | out-of-repository wrapper (SUPPLEMENT-01 file) | pass / pass | pass / pass | ✓ |
| flask-4992 | `test_config_from_file_mode[None]` | pass / pass | pass / pass | ✓ |
| | `test_config_from_file_mode[t]`, `[b]` | pass / fail | pass / **fail** (TypeError) | ✓ |
| | `test_config_from_file_toml` (model's version) | pass / fail | pass / **fail** (TypeError) | ✓ |
| | `test_config_missing_file[t]`, `[b]` | pass / fail | pass / **fail** (TypeError) | ✓ |

All 11 predicted rows match.

In the unpredicted row, the 6 failing cases are exactly the cases where
`Content-Type` is `application/json` without a charset and the test reads the
body as text, either through `decode_unicode=True` or through cached `r.text`.
These cases depend on the model's UTF-8 default for JSON, which the reference
fix does not adopt.

## Reading

- **requests-3362 and flask-4992.** Every test the model wrote for its
  interpretation passes on its own code and fails on the reference fix. The
  passing evidence in these sessions therefore certified the model's reading,
  not the intended behavior (taxonomy class A4).
- **flask-4045.** The model's tests pass on the reference fix too. Its gap is
  scope: it omits the endpoint-name check. It does not contradict the
  reference, so the tests it wrote are compatible with the intended behavior
  but do not cover the missing part (class A2).

## Limits

Failure messages were kept only in the last 6000 characters of each run's
output. For requests-3362, the reason is recorded only for the
`get_encoding_from_headers` case (AssertionError). The outcome of every case is
recorded in `supplement-02-brief.json`.
