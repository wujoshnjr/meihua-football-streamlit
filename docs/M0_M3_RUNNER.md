# JARVIS M0-M3 research runner

Status: RESEARCH ONLY.

The runner keeps the Football baseline independent from the signal families. Each match receives a registered `BaselineLambdaSnapshot`; M1/M2/M3 may only learn residual changes around those same lambdas.

## Families

- M0_FOOTBALL: use the registered Football lambdas unchanged.
- M1_QIMEN: fit/apply Qimen numeric features through the generic residual engine.
- M2_MEIHUA: fit/apply Meihua numeric features through the same generic residual engine.
- M3_QIMEN_MEIHUA: prefix and combine both raw feature families, then fit one residual artifact. No hand-written voting or cross-family interaction is added.

`fit_model_family()` uses only rows whose immutable role is TRAIN. It never fits M0. `predict_model_family()` rejects a residual artifact from the wrong model family.

## Football baseline contract

`BaselineLambdaSnapshot` carries:

- match ID;
- home/away scoring intensities;
- an auditable baseline artifact/source identifier;
- score model (`INDEPENDENT_POISSON` or `DIXON_COLES`);
- optional registered Dixon-Coles rho;
- score-grid truncation.

This contract deliberately does not require one particular Football model. The baseline may come from the current champion or a separately validated dynamic-strength challenger, allowing signal ablations to remain unchanged when the Football core improves.

## Common score generation

All four families use the same score-grid function after their lambdas are fixed. 1X2 probabilities are sums of the normalized score matrix. This prevents M1/M2/M3 from receiving an accidental advantage through a different score model.

## Statistical isolation

Residual fitting delegates to `jarvis.research.residual`, so all signal families share:

- no free intercept;
- hidden-intercept design rejection;
- L2 regularization;
- TRAIN-only observations;
- convergence guards;
- schema checks and provenance hashes.

The runner does not calibrate probabilities and does not promote a model. Calibration remains a separate CALIBRATION-stage operation and model selection remains governed by untouched evaluation.
