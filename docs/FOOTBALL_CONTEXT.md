# JARVIS Football Fixture Context

## Purpose

`jarvis.football.context` adds leakage-auditable schedule facts that may help a football-only research challenger account for recovery time and fixture congestion.

The module does **not** hard-code that short rest improves or worsens scoring. It only derives facts available before kickoff and adapts them to the shared no-intercept residual engine. Coefficients must be learned on `TRAIN`, regularization/shrinkage selected on `VALIDATION`, calibration performed on `CALIBRATION`, and any accuracy claim must come only from frozen `TEST_UNTOUCHED` evaluation.

## Prematch facts

For each target fixture the snapshot records, separately for home and away teams:

- most recent selected prior match time;
- recovery hours since that match;
- number of selected matches in the previous 7 days;
- number of selected matches in the previous 14 days;
- whether recovery is under 96 hours;
- explicit known/unknown indicators for prior-match history.

Rest days are capped at 14 in the numeric design to limit leverage from very long inactive periods. The raw recovery hours remain in the snapshot for audit.

## Leakage boundary

A historical match can contribute only when both conditions hold:

```text
historical.event_at < target.cutoff_at
historical.available_at <= target.cutoff_at
```

Future matches and historical rows whose source payload was not yet available at the target cutoff are ignored. Duplicate `match_id` values are rejected.

## Why 96 hours is only a feature boundary

Published professional-football research commonly defines fixture congestion using short inter-match recovery, including comparisons around three days versus six or more days. Evidence about the direction and magnitude of performance effects is mixed and context-dependent. JARVIS therefore uses 96 hours only as a transparent descriptive feature boundary; it does not assign a manual coefficient or outcome rule.

## Research use

`build_context_residual_observation(...)` converts one context snapshot into the existing generic residual contract with:

```text
feature_family = FOOTBALL_CONTEXT
feature_schema_version = jarvis-football-fixture-context-v0.1.0
```

This keeps schedule-context effects under the same no-hidden-intercept, convergence, provenance and shrinkage guardrails used elsewhere in JARVIS v8.

Production v7.2 is unchanged by this module.
