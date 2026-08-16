# Qimen Outcome Research Layer

This document defines the JARVIS research boundary for converting Qimen structure into auditable football outcome features without hard-coding score or 1X2 answers.

## Design rule

Qimen symbols do not directly add goals. A rule such as `伏吟 = -1 goal`, `擊刑 = +1 opponent goal`, or `same palace = draw` is prohibited unless it is first registered as a feature hypothesis and then supported by chronological out-of-sample evidence.

The intended path is:

```text
football-only baseline lambda
        ↓
raw Qimen outcome feature snapshot
        ↓
TRAIN-only fitted lambda adjustment
        ↓
adjusted home / away lambda
        ↓
Poisson or Dixon–Coles score grid
        ↓
exact-score probabilities and 1X2
```

The current production path remains `SHADOW_ONLY`. The research wrapper described below does not let Qimen change a probability.

## 1. Venue context is now explicitly registered

`MatchInput.venue_mode` registers whether the nominal schedule home side is:

- `TRUE_HOME`; or
- `NEUTRAL`.

`qimen.venue.resolve_venue_baseline` applies the scoring baseline. A neutral match must provide explicit pre-match neutral-site home/away scoring means and a non-empty source. The implementation deliberately refuses to silently average or reuse the ordinary league home/away split.

`qimen.outcome_prediction.build_outcome_research_prediction` connects this venue contract to the existing football-only JARVIS engine by supplying the registered venue baseline before the Poisson / Dixon–Coles calculation. The existing champion path itself is unchanged.

This design is motivated by empirical football research showing that neutral venues change the ordinary home-advantage context rather than preserving a normal home/away condition.

## 2. Preserve original and visible Qimen stems

`qimen.outcome_features.QimenOutcomeFeatureSnapshot` stores both:

- original day/hour stems from the calendar;
- visible stems after Qimen hiding / xun-head resolution.

This prevents loss of information when an original `甲` resolves to the same visible instrument as the other team.

`same_palace` is a feature, not a draw prediction. When both teams resolve to the same palace, `direction_resolution` becomes `LOW_SAME_PALACE`; it means the current mapping has lower directional discrimination, not that the match must finish level.

## 3. Interpretation index is not an outcome weight

The existing `signal_index` was designed to rank qualitative candidate scenarios. The outcome snapshot records it under the explicit names:

- `home_interpretation_index`;
- `away_interpretation_index`.

These values must not be used as direct goal, xG or 1X2 coefficients.

## 4. Raw structural counters

The first outcome feature snapshot records deterministic counts and flags for structures that can later be tested independently:

- 伏吟 count;
- 反吟 count;
- 擊刑 / 刑格 count;
- 門迫 / 宮迫 count;
- 入墓 count;
- 天網 count;
- same-palace / same-visible-stem flags;
- team palace, door, stars, deity, seasonal state, void and horse states;
- full pattern-name tuple.

No manual effect size is attached to these fields.

Later versions may add registered football axes such as creation, conversion, resistance, transition, volatility and suppression, but raw facts are retained before any statistical encoding is chosen.

## 5. Full exact-score evaluation is available in the research path

Top-1 and top-3 score hits are not sufficient to compare probability models.

`qimen.score_metrics` provides:

- exact-score probability;
- exact-score negative log likelihood.

`qimen.outcome_prediction.reconstruct_score_grid` deterministically rebuilds the complete normalized score grid from the stored lambdas, `max_goals`, score-model family and fitted Dixon–Coles rho. With the default 0–10 range this gives 121 score cells.

`evaluate_exact_score` then scores the actual result against the complete raw score distribution. This is an interim migration path: a later core-schema revision can persist the full grid directly in `PredictionResult` and `LockedPrediction` without changing the mathematical definition.

## 6. Current safety properties

The research path has the following deliberate constraints:

1. Qimen remains `SHADOW_ONLY` and does not change lambda, score probabilities or 1X2.
2. `same_palace` never automatically increases draw probability.
3. 伏吟、反吟、擊刑、天網、迫、入墓 are recorded as features rather than goal increments.
4. neutral-site scoring rates must be explicitly supplied; missing rates fail closed.
5. the existing JARVIS champion path is not replaced by this wrapper.
6. future fitted Qimen coefficients must be trained only on chronological TRAIN data.

## 7. Next integration steps

1. Move venue-baseline provenance from the research wrapper into the core `PrematchModelInput` / provenance schema after compatibility review.
2. Persist the full score grid directly in `PredictionResult` and `LockedPrediction` and add exact-score log loss to aggregate evaluation.
3. Upgrade the football baseline to opponent-adjusted, time-varying attack and defence strengths with neutral-site handling.
4. Define a registered Qimen modelling matrix from the raw snapshot, including categorical encoding and regularization policy.
5. Fit a Qimen lambda-adjustment artifact on `TRAIN` only, using football-only log-lambda as an offset.
6. Compare `FOOTBALL_ONLY` versus `FOOTBALL_PLUS_QIMEN` on identical chronological splits.
7. Keep Qimen in `SHADOW_ONLY` until the existing blind-test promotion gate is satisfied.

## Research references

- Dixon, M. J. & Coles, S. G. (1997), *Modelling Association Football Scores and Inefficiencies in the Football Betting Market*, Journal of the Royal Statistical Society Series C, 46(2), 265–280. DOI: 10.1111/1467-9876.00065.
- Zhou et al. (2022), *The influence of removing home advantage on the Chinese Football Super League*, BMC Sports Science, Medicine and Rehabilitation. DOI: 10.1186/s13102-022-00604-0.

These sources support the football modelling and venue-context rationale. They do not validate any Qimen-to-football predictive mapping; those mappings remain research hypotheses that must be tested prospectively or on untouched chronological data.
