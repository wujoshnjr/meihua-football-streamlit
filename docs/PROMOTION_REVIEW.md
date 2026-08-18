# JARVIS v8 Generic Promotion Review

`jarvis.research.promotion` turns the existing untouched evaluation stack into a generic governance gate for any frozen M0–M3 challenger. It does **not** activate a model.

## Why this exists

The repository already had a Qimen-specific activation gate, but v8 now has several possible challengers: Dynamic Football, context-adjusted Football, M1 Qimen, M2 Meihua and M3 fusion. A generic gate is needed so every challenger is judged under the same pre-registered rules instead of inventing a new threshold after seeing `TEST_UNTOUCHED`.

## Pre-registration boundary

A `PromotionPolicy` stores:

- baseline and challenger model family;
- minimum untouched matches, time blocks and competitions;
- minimum relative Log Loss improvement;
- maximum classwise ECE degradation;
- required fraction of rolling windows with better Log Loss;
- rolling-window width;
- paired block-bootstrap sample count, confidence level and seed;
- `registered_at` and a SHA-256 policy fingerprint.

`registered_at` must be no later than the first `TEST_UNTOUCHED` cutoff. If the policy is created or changed after the untouched period starts, `review_model_promotion(...)` rejects the review. This prevents seeing final outcomes and then weakening the gate.

## Default policy values

The v0.1 policy defaults deliberately inherit the repository's existing conservative Qimen governance scale where applicable:

- at least 5,000 untouched matches;
- at least 5 registered evaluation blocks;
- at least 2 competitions;
- at least 0.5% relative 1X2 Log Loss improvement;
- 95% paired block-bootstrap interval for Log Loss must be entirely below zero;
- Brier, RPS and exact-score NLL observed deltas must point in the same improving direction;
- maximum classwise ECE degradation of 0.005;
- at least 80% of registered rolling windows must improve Log Loss.

These values are not claims that 5,000 is universally optimal. They are a frozen governance policy. A future policy may use different thresholds, but it must receive a new policy fingerprint and be registered before its untouched test begins.

## Output

The review returns only one of:

- `ELIGIBLE_FOR_HUMAN_REVIEW`
- `KEEP_CHALLENGER`

It also returns all individual checks, aggregates, bootstrap intervals, rolling stability, the policy artifact source and a report SHA-256.

`automatic_promotion` is always `False`.

## Required workflow

```text
TRAIN
  ↓ learn coefficients
VALIDATION
  ↓ select hyperparameters
CALIBRATION
  ↓ fit probability calibration only
freeze model artifacts + PromotionPolicy
  ↓
TEST_UNTOUCHED
  ↓
paired block bootstrap + rolling stability
  ↓
review_model_promotion(...)
  ↓
human review only
```

The promotion report is never a new tuning signal. If it fails, the challenger remains frozen/shadow; the failed untouched test must not be recycled as a new validation set.
