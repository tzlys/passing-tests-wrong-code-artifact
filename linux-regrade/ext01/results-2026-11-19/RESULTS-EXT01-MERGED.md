# EXT-01 merged results

| group | sampled | valid | divergent (first pass) | confirmed divergent | rate | Wilson 95% | with agent-added test |
|---|---|---|---|---|---|---|---|
| unresolved | 84 | 30 | 11 | 11 | 0.367 | [0.219, 0.545] | 8 |
| resolved | 27 | 15 | 2 | 2 | 0.133 | [0.037, 0.379] | 2 |

Invalid reasons: `{"unresolved": {"no_test_passes_in_M": 54}, "resolved": {"no_test_passes_in_M": 12}}`

## Confirmed divergent records

- `20240620_sweagent_claude3.5sonnet/django__django-12856` (unresolved): `test_create_sql_calls_check_fields (model_fields.test_unique_constraint.UniqueConstraintTests)` → ERROR (agent-added); `test_remove_sql_calls_check_fields (model_fields.test_unique_constraint.UniqueConstraintTests)` → ERROR (agent-added); `test_unique_constraint_existing_fields (model_fields.test_unique_constraint.UniqueConstraintTests)` → ERROR (agent-added); `test_unique_constraint_non_existent_field (model_fields.test_unique_constraint.UniqueConstraintTests)` → ERROR (agent-added)
- `20240725_opendevin_codeact_v1.8_claude35sonnet/scikit-learn__scikit-learn-10949` (unresolved): `test_check_array_pandas.py::test_check_array_pandas_dataframe` → FAILED (agent-added)
- `20240728_sweagent_gpt4o/pallets__flask-4045` (unresolved): `tests/test_blueprints.py::test_blueprint_name_with_dot` → FAILED (agent-added)
- `20241203_KortixAI-AgentPress-sonnet-20241022/pydata__xarray-3364` (unresolved): `xarray/tests/test_concat.py::TestConcatDataset::test_concat_errors` → FAILED (agent-added)
- `20250226_sweagent_claude-3-7-sonnet-20250219/sympy__sympy-22840` (unresolved): `test_cse_MatrixSymbol_indexing` → FAILED (agent-added)
- `20250526_sweagent_claude-4-sonnet-20250514/django__django-12856` (resolved): `test_unique_constraint_pointing_to_m2m_field (invalid_models_tests.test_models.ConstraintsTests)` → FAILED (agent-added); `test_unique_constraint_pointing_to_missing_field (invalid_models_tests.test_models.ConstraintsTests)` → FAILED (agent-added); `test_unique_constraint_pointing_to_non_local_field (invalid_models_tests.test_models.ConstraintsTests)` → FAILED (agent-added)
- `20250526_sweagent_claude-4-sonnet-20250514/django__django-15819` (unresolved): `Test that multiple foreign keys to the same target model get related_name` → FAILED
- `20250526_sweagent_claude-4-sonnet-20250514/django__django-11910` (unresolved): `test_rename_field_foreign_key_to_field_with_other_changes (migrations.test_autodetector.AutodetectorTests)` → FAILED (agent-added)
- `20250526_sweagent_claude-4-sonnet-20250514/sympy__sympy-21055` (resolved): `test_arg` → ERROR (agent-added)
- `20250526_sweagent_claude-4-sonnet-20250514/django__django-13230` (unresolved): `test_rss2_feed_comments_precedence (syndication_tests.tests.SyndicationFeedTest)` → ERROR (agent-added); `test_rss2_feed_with_comments_via_extra_kwargs (syndication_tests.tests.SyndicationFeedTest)` → ERROR (agent-added)
- `20250526_sweagent_claude-4-sonnet-20250514/sympy__sympy-16281` (unresolved): `test_pretty_product` → FAILED
- `20250526_sweagent_claude-4-sonnet-20250514/sympy__sympy-19487` (unresolved): `test_sign` → FAILED
- `20250526_sweagent_claude-4-sonnet-20250514/pytest-dev__pytest-5413` (unresolved): `testing/code/test_excinfo.py::test_excinfo_str` → FAILED; `testing/code/test_excinfo.py::test_excinfo_str_multiline` → FAILED (agent-added)
