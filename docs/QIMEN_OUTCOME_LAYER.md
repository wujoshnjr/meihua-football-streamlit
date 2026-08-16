# Qimen Outcome Research Layer

This document defines the next JARVIS research boundary for converting Qimen structure into auditable football outcome features without hard-coding score or 1X2 answers.

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

The current production path remains `SHADOW_ONLY`. This foundation does not change any probability.

## 1. Venue context is a model input

A nominal schedule home team is not automatically treated as having a true home venue advantage. `qimen.venue.resolve_venue_baseline` separates:

- `TRUE_HOME`: use a registered home/away scoring split;
- `NEUTRAL`: require an explicit neutral-site scoring estimate.

The neutral path deliberately refuses to silently average or reuse league home/away means. A neutral estimate must come from a pre-match training window and have its own provenance.

This is motivated by empirical football research showing that neutral venues change the usual home-advantage context rather than preserving the ordinary home/away condition.

## 2. Preserve original and visible Qimen stems

`qimen.outcome_features.QimenOutcomeFeatureSnapshot` stores both:

- original day/hour stems from the calendar;
- visible stems after Qimen hiding / xun-head resolution.

This prevents loss of information in cases where an original `甲` resolves to the same visible instrument as the other team.

`same_palace` is therefore a feature, not a draw prediction. When both teams resolve to the same palace, `direction_resolution` becomes `LOW_SAME_PALACE`; it means the current Qimen mapping has lower directional discrimination, not that the match must finish level.

## 3. Interpretation index is not an outcome weight

The existing `signal_index` was designed to rank qualitative candidate scenarios. The outcome snapshot records it under the explicit names:

- `home_interpretation_index`
- `away_interpretation_index`

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

Later versions may add registered football axes such as creation, conversion, resistance, transition, volatility and suppression, but the first implementation intentionally preserves raw facts before choosing a statistical encoding.

## 5. Exact-score evaluation

Top-1 and top-3 score hits are not sufficient to compare probability models. `qimen.score_metrics` adds:

- exact-score probability;
- exact-score negative log likelihood.

The prediction path should next retain the full score grid, not only the five highest-probability scorelines. This makes it possible to compare whether a model assigned materially different probability to the score that actually occurred.

## 6. Next integration steps

1. Add venue mode and venue-baseline provenance to `MatchInput`, `PrematchModelInput` and feature snapshots.
2. Retain the full score grid in `PredictionResult` and `LockedPrediction`.
3. Add exact-score log loss to aggregate evaluation.
4. Upgrade the football baseline to opponent-adjusted, time-varying attack and defence strengths with neutral-site handling.
5. Fit a regularized Qimen lambda-adjustment artifact on `TRAIN` only, using the football-only lambda as an offset.
6. Compare `FOOTBALL_ONLY` versus `FOOTBALL_PLUS_QIMEN` on the same chronological splits.
7. Keep Qimen in `SHADOW_ONLY` until the existing blind-test promotion gate is satisfied.

## Research references

- Dixon, M. J. & Coles, S. G. (1997), *Modelling Association Football Scores and Inefficiencies in the Football Betting Market*, Journal of the Royal Statistical Society Series C, 46(2), 265–280. DOI: 10.1111/1467-9876.00065.
- Zhou et al. (2022), *The influence of removing home advantage on the Chinese Football Super League*, BMC Sports Science, Medicine and Rehabilitation, 14:206. DOI: 10.1186/s13102-022-00604-0.

These sources support the football modelling and venue-context rationale. They do not validate any Qimen-to-football predictive mapping; those mappings remain research hypotheses that must be tested prospectively or on untouched chronological data.
