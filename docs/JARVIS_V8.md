# JARVIS v8 Multi-Signal Research Architecture

JARVIS v8 is an incremental research architecture. It does **not** replace the v7.2 production champion and it does not promote any traditional system into football probabilities by hand.

## Model families

- `M0`: Football-only champion/challengers.
- `M1`: Football + Qimen residual challenger.
- `M2`: Football + Meihua residual challenger.
- `M3`: Football + Qimen + Meihua residual/fusion challenger.
- `M4`: preregistered interaction research only after M3 has shown stable validation gains.

Every challenger must use the same prematch football snapshot and chronological dataset role. `TEST_UNTOUCHED` is never used to choose features or penalties.

## Meihua v0.2 scope

The Meihua implementation deliberately supports only the deterministic year-month-day-hour method. The event-location civil clock is used as the project convention. The lunar year branch, lunar month, lunar day and branch-hour are converted to the upper trigram, lower trigram and moving line with the traditional modulo-eight/modulo-six arithmetic.

The engine records original, mutual and changed trigrams plus body/use and five-element relations. These are **raw research features**. No relation is assigned a football goal bonus, 1X2 weight or fixed score.

All one-of-K Meihua categorical features now use reference coding rather than complete one-hot groups. Moving-line position is categorical rather than a numeric 1-to-6 slope. The reference-coding rule is statistical only: it prevents the signal design matrix from recreating a constant intercept and does not assign any traditional category a privileged football meaning.

## Qimen design integrity

Qimen one-of-K door, deity and seasonal-state fields also use reference coding. Multi-star membership remains multi-hot because a palace may contain more than one star. The Qimen residual fitter rejects any feature matrix whose column span can reproduce an all-ones vector, so a future encoder cannot silently recreate a hidden intercept.

## Shared residual model

The generic residual layer fits

```text
log(mu) = log(football_baseline_lambda) + X beta
```

with L2 regularization and no intercept. The no-intercept constraint is intentional: an all-zero signal model exactly reproduces the football baseline instead of receiving a free global recalibration term.

This contract is enforced twice:

1. one-of-K signal features use reference/effect coding instead of complete one-hot groups;
2. the fitter explicitly rejects a design matrix that contains a constant direction.

Generic residual artifacts record the feature family/schema, training time range, deployment Git commit, training-data SHA-256 and artifact SHA-256. Unconverged artifacts cannot be applied.

## Dynamic football identifiability

The dynamic opponent-adjusted football challenger estimates relative attack and defence-weakness effects. Attack effects and defence effects are each constrained to sum to zero over fitted teams. This keeps the registered venue/competition baseline as the global scoring level instead of letting team effects act as an unregistered league-wide recalibration term.

## Next steps

1. Re-run the full repository test suite with the v0.2 encoders and fitters.
2. Generate Qimen and Meihua snapshots from the same immutable prematch event records.
3. Fit M1 and M2 independently on TRAIN.
4. Select penalties/features on VALIDATION only.
5. Compare M0/M1/M2/M3 with paired chronological evaluation.
6. Add cross-family interactions only after M3 demonstrates stable incremental value.
