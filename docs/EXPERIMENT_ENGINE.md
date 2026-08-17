# JARVIS v8 chronological experiment engine

Status: RESEARCH ONLY. Production v7.2 is unchanged.

## Purpose

This layer is the arbiter for whether a new football, Qimen, Meihua, or fusion challenger is genuinely better. It is intentionally stricter than an ad-hoc notebook:

- one immutable match record shared by M0/M1/M2/M3;
- one event-local cutoff before kickoff;
- football, Qimen and Meihua snapshots must all have `available_at <= cutoff`;
- roles must remain chronological: TRAIN -> VALIDATION -> CALIBRATION -> TEST_UNTOUCHED;
- the same `match_id` set is required for paired model comparison;
- actual labels are 90-minute plus added-time goals only, as registered by the project protocol;
- no challenger is promoted by this module.

## Model families

- M0_FOOTBALL: football-only control.
- M1_QIMEN: football baseline plus fitted Qimen residual.
- M2_MEIHUA: football baseline plus fitted Meihua residual.
- M3_QIMEN_MEIHUA: football baseline plus both signal families, without hand-written cross-family voting.

Interactions remain out of scope until M3 first demonstrates stable validation value.

## Metrics

Every forecast is scored on the same match with:

- 1X2 log loss;
- Brier score;
- ranked probability score (RPS);
- exact-score negative log likelihood;
- 1X2 top-1 accuracy;
- exact-score top-1/top-3 accuracy;
- classwise recall;
- classwise expected calibration error (ECE).

Paired comparisons report challenger minus baseline deltas; negative deltas are better.

## Market benchmark

`jarvis.research.market.MarketBenchmarkSnapshot` stores a pre-match decimal-odds snapshot, computes its overround, and normalizes reciprocal odds into a simple de-vigged 1X2 benchmark. It is deliberately not a production feature and is not silently fused into M0/M1/M2/M3.

A future market-calibrated challenger must be registered as a separate family and tested on the same untouched matches. This separation matters because market probabilities aggregate information that may overlap with lineups, injuries and team strength.

## Method references

- Dixon, M. J. & Coles, S. G. (1997), *Modelling Association Football Scores and Inefficiencies in the Football Betting Market*, DOI 10.1111/1467-9876.00065.
- Rue, H. & Salvesen, O. (2000), *Prediction and Retrospective Analysis of Soccer Matches in a League*, DOI 10.1111/1467-9884.00243.
- Crowder, M. et al. (2002), *Dynamic Modelling and Prediction of English Football League Matches for Betting*, DOI 10.1111/1467-9884.00308.
- Clegg, L., Song, Z. & Cartlidge, J. (2026), *A market-calibrated accelerated failure time model for in-play football forecasting*, arXiv:2605.16066.

These references support statistical methodology and benchmarking only; they do not validate Qimen or Meihua as predictive signals.
