# EXT-01: what the 13 confirmed divergences encode (post-hoc coding)

This coding is post-hoc and was not part of the pre-registered protocol. One coder
(the AI assistant, under the author's delegation) read each confirmed divergent test
in `confirmed-logs.tar.gz`: the agent's test-block diff, plus the failure in the
G (reference-fix) run. There was no second coder. Treat the counts as descriptive.

Classes:

- **behavior**: the test asserts an output or behavior that the reference fix does
  not produce.
- **interface**: the test calls a parameter, method or call pattern that only the
  agent's source defines. Under the reference fix it errors.
- **message**: the test asserts the exact text of an error or warning message that
  the agent wrote.

| Resolved | Entry | Instance | Failure under reference fix | Class |
|---|---|---|---|---|
| no | sweagent claude3.5sonnet | django-12856 | AttributeError: no `check_fields` | interface |
| no | opendevin codeact v1.8 | scikit-learn-10949 | assert on warning text ("were converted" vs "were all converted") | message |
| no | sweagent gpt4o | flask-4045 | `pytest.raises(match=...)` on the agent's message text | message |
| no | KortixAI AgentPress | xarray-3364 | TypeError: unexpected kwarg `variables_join` | interface |
| no | sweagent claude-3-7 | sympy-22840 | `len(replacements) == 2` fails | behavior |
| no | sweagent claude-4 | django-15819 | expected `related_name='target1_set'`, reference generates another name | behavior |
| no | sweagent claude-4 | django-11910 | `'field' != 'renamed_field'` | behavior |
| no | sweagent claude-4 | django-13230 | TypeError: `add_item()` got multiple values for `comments` | interface |
| no | sweagent claude-4 | sympy-16281 | pretty-printed Product differs (existing test edited) | behavior |
| no | sweagent claude-4 | sympy-19487 | `test_sign` assertion (existing test extended) | behavior |
| no | sweagent claude-4 | pytest-5413 | `str(excinfo)` assertions (existing test edited) | behavior |
| yes | sweagent claude-4 | django-12856 | expected E012/E013/E016 errors; reference reports none in that call | behavior, beyond hidden tests |
| yes | sweagent claude-4 | sympy-21055 | contradictory assumptions raise ValueError under the reference fix | behavior, beyond hidden tests |

**Summary**

- **Unresolved (11):** 6 behavior, 3 interface, 2 message. Hidden tests fail on all 11
  of these patches, so in each one a passing agent test supports code that is wrong.
- **Resolved (2):** both assert behavior beyond what the hidden tests check. A test
  that fails on the reference fix is therefore a signal of a mismatch, not proof that
  the code is wrong.

**Robustness**

These are computed from `results-merged.json` and `sample.json`.

- Six of the 11 unresolved divergences come from `20250526_sweagent_claude-4-sonnet-20250514`.
  Excluding that submission leaves 5 of 22 (23%, Wilson 95% CI 10–43%).
- One-sided Fisher exact test of unresolved (11/30) against resolved (2/15): p = 0.098.
  The difference between the groups is not significant.
- All 66 non-analyzable sampled patches (54 unresolved, 12 resolved) fall outside the
  pre-registered definition, because no test of the patch's own passes on the agent's
  source. None was excluded for infrastructure reasons.
