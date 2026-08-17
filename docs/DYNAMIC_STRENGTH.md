# Dynamic Opponent-Adjusted Football Strength

This research module estimates current team attack and defence-weakness effects from historical observations while respecting a prematch cutoff.

For a match between home team `i` and away team `j`:

```text
lambda_home = registered_home_baseline * exp(attack_i + defence_weakness_j)
lambda_away = registered_away_baseline * exp(attack_j + defence_weakness_i)
```

Each historical match is weighted by exponential time decay. Attack and defence parameters are fitted jointly with L2 regularization, so opponent quality affects the estimated team effects instead of being ignored by a simple recent-match average.

## Identifiability and baseline preservation

Version `jarvis-opponent-adjusted-strength-v0.3.0` uses explicit sum-to-zero contrasts:

```text
sum_i attack_i = 0
sum_i defence_weakness_i = 0
```

The L2 penalty is applied to the reconstructed team effects through the contrast penalty matrix, not merely to an arbitrary reference team's free parameters. This keeps attack and defence as relative team strengths and prevents the layer from absorbing an unregistered global scoring intercept.

The scoring baselines remain explicit per observation. This is deliberate: neutral-site observations must not silently inherit a true-home advantage, and team effects must not silently replace the registered venue/competition scoring level.

## Research-only xG target blend

StatsBomb Open Data ingestion already preserves normal-time `home_xg` and `away_xg`. Version `v0.3.0` allows the dynamic-strength fit to use those process metrics instead of discarding them:

```text
target = (1 - xg_weight) * goals + xg_weight * xG
```

Important constraints:

- `xg_weight=0` is the default and reproduces the original goals-only estimator;
- `xg_weight>0` requires complete xG coverage for every selected training row;
- the blended target is fitted with the same log-mean score equations; with a non-integer target this is treated as a quasi-likelihood mean fit, not as a claim that xG is a Poisson count;
- enabling xG does not promote this challenger into production and does not imply improved forecast accuracy until chronological out-of-sample metrics demonstrate it.

The motivation is to test whether partially shrinking noisy realized finishing toward shot-quality production improves future estimates of team attack/defence. The repository treats that as a hypothesis to validate rather than an assumed improvement.

## VALIDATION-only hyperparameter tuning

`jarvis-dynamic-strength-tuning-v0.1.0` removes manual selection of the three highest-impact dynamic-strength hyperparameters:

- exponential `half_life_days`;
- `l2_penalty`;
- `xg_weight`.

`tune_dynamic_strength(...)` uses rolling-origin validation. For every registered `VALIDATION` fixture it refits the strength model at that fixture's own prematch cutoff, predicts the fixture, and scores 1X2 log loss plus Brier score. Later validation matches therefore cannot leak into earlier validation fits.

The xG grid **must contain `0.0`**. Goals-only is always a legal fallback; xG earns a non-zero weight only when held-out validation forecasts improve. Candidate selection minimizes mean 1X2 log loss, then Brier score. Exact ties are resolved conservatively toward lower xG weight, stronger L2 regularization, and longer half-life.

`CALIBRATION` and `TEST_UNTOUCHED` fixtures are rejected by this tuner. After selection, the chosen hyperparameters must be frozen before calibration and untouched testing. A better validation score is not itself evidence of final predictive improvement.

## Guardrails

- only `event_at < cutoff_at` and `available_at <= cutoff_at` historical rows are used;
- duplicate match IDs are rejected;
- attack and defence effects each sum to zero over fitted teams;
- unseen teams shrink exactly to the registered scoring baseline;
- partial home/away xG pairs are rejected;
- positive xG weight requires full selected-row xG coverage;
- tuning fixtures must be explicitly labelled `VALIDATION` and locked before kickoff;
- xG tuning grids must preserve a goals-only fallback;
- unconverged fits cannot be used for prediction;
- lambda bounds are numerical safety rails, not football claims.

The module remains a research challenger only. It does not replace the existing JARVIS champion until chronological paired evaluation shows an improvement on untouched data.
