# JARVIS Football Fixture Context

## Purpose

`jarvis.football.context` adds leakage-auditable schedule facts that may help a football-only research challenger account for recovery time and fixture congestion.

The module does **not** hard-code that short rest improves or worsens scoring. It only derives facts available before kickoff and adapts them to the shared no-intercept residual engine. Coefficients are learned on `TRAIN`, regularization/shrinkage is selected on `VALIDATION`, calibration remains a separate `CALIBRATION` step, and any accuracy claim must come only from frozen `TEST_UNTOUCHED` evaluation.

## Prematch facts

For each target fixture the snapshot records, separately for home and away teams:

- most recent selected prior match time;
- recovery hours since that match;
- number of selected matches in the previous 7 days;
- number of selected matches in the previous 14 days;
- whether recovery is under 96 hours;
- whether prior-match history is known for one side but not the other.

Rest days are capped at 14 in the numeric design to limit leverage from very long inactive periods. The raw recovery hours remain in the snapshot for audit.

The v0.2 numeric design intentionally avoids separate `home_rest_known=1`, `away_rest_known=1`, `both_rest_known=1` columns. On a mature dataset those flags can all become constant one and reconstruct a hidden intercept. Missing-history asymmetry is instead effect-coded as `rest_history_balance`; complete history maps to zero. No football direction is assigned manually.

## Leakage boundary

A historical match can contribute only when both conditions hold:

```text
historical.event_at < target.cutoff_at
historical.available_at <= target.cutoff_at
```

Future matches and historical rows whose source payload was not yet available at the target cutoff are ignored. Duplicate `match_id` values are rejected.

## Why 96 hours is only a feature boundary

Professional-football literature commonly defines congestion around successive matches separated by less than roughly 96 hours. Systematic reviews report mixed effects on physical/technical match performance, while recovery and injury studies show that congested schedules can alter recovery kinetics and injury exposure. The evidence is not strong enough to justify a universal manual goal penalty or bonus.

JARVIS therefore uses 96 hours only as a transparent descriptive feature boundary. TRAIN estimates coefficients from outcomes and VALIDATION decides whether any fitted context shift should survive shrinkage.

## Chronological tuning

`jarvis.football.context_tuning` binds each immutable `MultiSignalDatasetRow` to its same-cutoff `FixtureContextSnapshot` and provides:

- `fit_context_challenger(...)`: fits context coefficients from `TRAIN` rows only;
- `tune_context_challenger(...)`: selects L2 and global shrinkage alpha on `VALIDATION` rows only;
- `apply_context_challenger(...)`: emits a `BaselineLambdaSnapshot` compatible with the existing M0-M3 runner.

Every alpha grid must contain `0`. Therefore the selected context challenger can exactly recover the registered Football lambdas when VALIDATION finds no incremental value. `CALIBRATION` and `TEST_UNTOUCHED` labels are ignored during this selection.

When context-adjusted Football is used in an M0-M3 experiment, the same frozen adjusted baseline must be supplied to all four families. This preserves the intended ablation question: Qimen and Meihua are measured relative to the same Football information set rather than different football baselines.

## Research contract

`build_context_residual_observation(...)` converts one context snapshot into the generic residual contract with:

```text
feature_family = FOOTBALL_CONTEXT
feature_schema_version = jarvis-football-fixture-context-v0.2.0
```

This keeps schedule-context effects under the same no-hidden-intercept, convergence, provenance and shrinkage guardrails used elsewhere in JARVIS v8.

Production v7.2 is unchanged by this module. A context feature existing in code is not evidence that it improves forecasts; only frozen chronological out-of-sample metrics can establish that.
