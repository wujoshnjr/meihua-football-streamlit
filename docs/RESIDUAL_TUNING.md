# Residual regularization and shrinkage tuning

Status: RESEARCH ONLY.

Signal residual coefficients are learned on TRAIN only. `tune_model_family()` then selects two hyperparameters using only the immutable VALIDATION split:

- L2 penalty controlling coefficient regularization;
- global `shrinkage_alpha` controlling how much of the learned log-lambda residual is applied.

## Shrinkage

For a fitted residual shift `X beta`, prediction uses:

`log(lambda_adjusted) = log(lambda_football) + alpha * X beta`

where `0 <= alpha <= 1`.

- `alpha = 0` exactly reproduces the registered Football baseline.
- `alpha = 1` applies the complete TRAIN-fitted residual.
- intermediate values shrink the signal adjustment toward zero.

The tuning grid is required to include `alpha = 0`. This guarantees that a useless or unstable Qimen/Meihua signal can lose to the Football baseline rather than being forced into every forecast.

## Selection protocol

For each L2 candidate:

1. fit coefficients using TRAIN rows only;
2. score every alpha candidate on VALIDATION rows only;
3. select by lowest validation 1X2 log loss, then Brier score;
4. deterministic ties prefer smaller alpha and stronger L2 regularization.

CALIBRATION and TEST_UNTOUCHED labels are ignored by the tuner. They cannot select L2 or alpha.

## Governance

The selected tuning artifact is not a production promotion. Probability calibration remains a separate CALIBRATION-stage step, and final evidence must still come from TEST_UNTOUCHED plus the project's rolling-block and paired-bootstrap gates.
