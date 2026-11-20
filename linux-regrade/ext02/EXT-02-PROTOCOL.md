# EXT-02: how often do public agent trajectories create the preconditions of links 1–3?

Status: **pre-registered**. This file and the scripts next to it were committed
before any trajectory was downloaded. If no clean result exists by
**2026-11-20 12:00 America/New_York**, the study is abandoned, and the paper is
submitted at the fallback version (`paper-v11`, SHA-256 prefix `d55bd7fe`).

## Question and claim boundary

The paper's first three links (what ran, when it ran, what was recorded) are
populated only by constructed cases. This study asks how often real agents issue
commands that create the *preconditions* of those links:

- **Link 3, recorded:** a test command whose exit status is hidden by a later
  command.
- **Link 2, when:** a test run in the background, so the agent can edit while it
  runs.
- **Link 1, what ran:** a non-editable install of the repository, so tests may
  import an installed copy instead of the checkout.

A match shows that a precondition occurred. It **never** shows that a failure
occurred. We do not claim that any match caused a wrong pass, a wrong record or a
wrong acceptance.

## Population and sample

1. **Entries.** The 24 SWE-bench Lite entries in `../ext01/entries.txt`, which
   is the same population as EXT-01.
2. **Trajectory files.** All objects under
   `s3://swe-bench-submissions/lite/<entry>/trajs/`, read anonymously over HTTPS.
   An entry with no objects there is counted and excluded.
3. **Sampling.** Within each entry, group objects by instance id. The instance id
   is the first path component after `trajs/`, or the file stem when files sit
   directly in `trajs/`.
   - Order instances by `sha256("<entry>/<instance_id>")`.
   - Take the first 40.
   - For each instance, take every object whose size is at most 20 MB. Larger
     objects are counted and skipped.

## Stages

- **Stage 0, format probe (`ext02_probe.py`).**
  - List each entry's `trajs/` prefix and record object counts, extensions and
    sizes.
  - Download one object per entry: the first object of the first instance in
    sample order.
  - Print only its *structure*: JSON key paths and value types, or the first 40
    lines with every run of letters and digits replaced by `x`.
  - Stage 0 computes no metric.
- **Extractor step.**
  - From the structure only, write one action extractor per format in
    `ext02_extract.py`.
  - An extractor returns the agent-issued shell commands and code actions of a
    trajectory, in order. It excludes observations, prompts and model reasoning.
  - Formats that expose no agent actions return `None`, and the trajectory is
    counted as *no actions*.
  - The extractor file is committed before Stage 1 runs.
- **Stage 1, scan (`ext02_scan.py`).** Download the sample, extract the actions,
  apply the fixed metrics below, and write `ext02-out/`.

## Fixed metric definitions

The definitions live in `ext02_metrics.py`, which is committed now and is not
edited after Stage 0. An action string is split into lines. Each line is split
into segments at the shell operators `||`, `&&`, `|`, `;` and `&`, and the
operators are kept.

**Test segment (T).** A segment whose first word is a test runner, after
optional leading `cd X &&`, environment assignments, `timeout N`, `nohup` or
`python`/`python3` with `-m`. The test runners are:

- `pytest`, `py.test`, `python -m pytest`;
- `python -m unittest`;
- `tox` and `nosetests`;
- Django's `runtests.py` (any path) and `manage.py test`;
- sympy's `bin/test`.

**M1, exit status hidden (link 3).** A T segment is followed in the same action by
any of the following, while the line does not set `pipefail`:

- a single pipe `|`;
- `;` and another command;
- `|| true`, `|| :` or `|| echo`;
- a later non-empty line.

**M2, background test (link 2).** A T segment is followed by a single `&`, or is
preceded by `nohup`.

**M3, non-editable install (link 1).** Any of:

- `pip install` (or `python -m pip install`) whose arguments include `.`, `./` or
  a path ending in the repository directory, with no `-e` or `--editable`;
- `python setup.py install`.

**Unit of analysis.** The trajectory. The denominator for M1 and M2 is the set of
trajectories with at least one T segment. The denominator for M3 is the set of
trajectories with any extracted action.

## Reporting

- For each metric:
  - the pooled proportion with a Wilson 95% CI;
  - per-entry proportions;
  - the median across entries, because pooled rates can be dominated by one
    agent;
  - the number of entries with at least one match.
- **Exclusions are counted and reported:**
  - no `trajs/` objects;
  - unparseable files;
  - files that are too large;
  - trajectories with no actions;
  - trajectories with no T segment.
- **Precision check.**
  - For each metric, up to 20 matches are drawn with `random.Random(20261120)`.
  - One coder judges each match against its command line: is it a real instance
    of the definition?
  - The coder is the AI assistant, under the author's delegation.
  - The reported precision is the share judged correct.
  - If precision for a metric is below 0.8, that metric is reported only as
    "unreliable", without a rate.
- **Prediction** (written before any data): M1 will be common, above 10% of
  trajectories with T. M2 and M3 will be rare, below 5%.

## How it enters the paper

At most one short paragraph or sentence in Section VI. It is phrased as
"preconditions occur", never as "failures occur", and it states the
precision check and the sample.

## Stage 0 outcome and the extractor (added after Stage 0, before Stage 1)

Stage 0 found `trajs/` objects for 16 of the 24 entries. The extractors are in `ext02_extract.py`:

- **SWE-agent (6 entries):** `.traj` files, `trajectory[].action`. Editor commands are dropped.
- **OpenDevin CodeAct v1.8 (1 entry):** `run` actions.
- **OpenHands CodeAct 2.1 (1 entry):** `execute_bash` tool calls.

Moatless (4 entries), AppMap Navie (2), CodeFuse-CGM and SWE-Fixer issue no agent shell commands, so they are counted as *no actions*. In every format, heredoc bodies are removed because they are file content. The metric definitions in `ext02_metrics.py` are unchanged.
