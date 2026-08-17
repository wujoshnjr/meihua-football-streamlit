# JARVIS v8 Multi-Signal Research Architecture

JARVIS v8 is an incremental research architecture. It does **not** replace the v7.2 production champion and it does not promote any traditional system into football probabilities by hand.

## Model families

- `M0`: Football-only champion/challengers.
- `M1`: Football + Qimen residual challenger.
- `M2`: Football + Meihua residual challenger.
- `M3`: Football + Qimen + Meihua residual/fusion challenger.
- `M4`: preregistered interaction research only after M3 has shown stable validation gains.

Every challenger must use the same prematch football snapshot and chronological dataset role. `TEST_UNTOUCHED` is never used to choose features or penalties.

## Meihua v0.1 scope

The first Meihua implementation deliberately supports only the deterministic year-month-day-hour method. The event-location civil clock is used as the project convention. The lunar year branch, lunar month, lunar day and branch-hour are converted to the upper trigram, lower trigram and moving line with the traditional modulo-eight/modulo-six arithmetic.

The engine records original, mutual and changed trigrams plus body/use and five-element relations. These are **raw research features**. No relation is assigned a football goal bonus, 1X2 weight or fixed score.

## Shared residual model

The generic residual layer fits

```text
log(mu) = log(football_baseline_lambda) + X beta
```

with L2 regularization and no intercept. The no-intercept constraint is intentional: an all-zero signal model exactly reproduces the football baseline instead of receiving a free global recalibration term.

Qimen and Meihua feature families remain schema-versioned and cannot be mixed accidentally within one fit artifact.

## Next steps

1. Finish opponent-adjusted dynamic football attack/defence strength.
2. Generate Qimen and Meihua snapshots from the same immutable prematch event records.
3. Fit M1 and M2 independently on TRAIN.
4. Select penalties/features on VALIDATION only.
5. Compare M0/M1/M2/M3 with paired chronological evaluation.
6. Add cross-family interactions only after M3 demonstrates stable incremental value.
