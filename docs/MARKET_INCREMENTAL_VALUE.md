# Market incremental value protocol

`jarvis-market-incremental-value-v0.1.0` is a research-only test of whether a JARVIS structural forecast adds predictive information beyond a prematch 1X2 market benchmark.

It does **not** feed market probabilities into M0/M1/M2/M3 production or research challengers. The market remains an external benchmark unless a separately reviewed promotion process explicitly changes that boundary.

## Logarithmic opinion pool

For structural probabilities `p_model` and de-vigged market probabilities `p_market`, the pooled probability for outcome `i` is

```
p_pool[i] ∝ p_model[i] ** w * p_market[i] ** (1 - w)
```

where `w` is the structural-model weight. The distribution is renormalized after pooling.

Interpretation:

- `w = 0`: market-only forecast;
- `w = 1`: structural-model-only forecast;
- `0 < w < 1`: the validation data support incremental structural information in addition to the market.

## Selection protocol

`fit_market_incremental_value(...)` accepts only rows explicitly labelled `VALIDATION`.

The candidate grid must include both endpoints:

- `0.0`, so market-only is always a legal fallback;
- `1.0`, so model-only performance is always explicitly measured.

Candidates are ranked by mean 1X2 log loss, then Brier score, then RPS. Exact ties prefer lower structural weight. This is intentionally conservative: the model must earn non-zero weight rather than receiving it by construction.

A fit is tied to exactly one `model_family` and `model_version`. Mixing versions in one fit is rejected.

## Leakage guardrails

Every market snapshot must satisfy:

```
market.captured_at <= cutoff_at < event_at
```

Snapshots captured after the registered cutoff are rejected. `CALIBRATION` and `TEST_UNTOUCHED` rows cannot be used to select the pooling weight.

The fitted artifact stores the validation window, candidate metrics, validation-data SHA-256, and artifact SHA-256.

## How to interpret results

A selected weight greater than zero is **not** by itself proof of final predictive improvement. It means only that validation favored retaining some structural-model contribution relative to the market benchmark.

The weight must be frozen before `TEST_UNTOUCHED`. Final claims require same-match untouched evaluation and stability diagnostics. If the selected weight is zero, the correct conclusion is that the tested structural model did not demonstrate incremental information beyond the market on validation.

This protocol follows the stronger forecasting question: not whether a model beats a naive baseline, but whether it adds information beyond a strong market aggregation benchmark.
