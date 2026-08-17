# JARVIS v8 untouched stability protocol

This protocol answers a narrower question than model fitting or hyperparameter tuning:

> After a model family has been frozen, is its improvement over the baseline stable through time on the already untouched test period?

It must not be used to choose features, L2 penalties, residual shrinkage, calibration temperature, fusion weights, or model families.

## Evaluation unit

Every `PrematchExperimentRecord` already carries an `evaluation_block`. Stability analysis treats that registered block as the atomic time cluster. Matches inside the same block are never split across rolling windows or paired bootstrap clusters.

This is intentional. Football observations close in time can share league regime, team-form, congestion, weather, transfer-window, or other latent conditions. Independently resampling individual matches would understate that dependence.

Blocks must be chronological and contiguous. A block may not disappear from the time sequence and later reappear.

## Rolling-block stability

`rolling_block_stability(...)` walks consecutive windows of registered evaluation blocks. For each window it recomputes the paired same-match deltas for:

- 1X2 log loss
- Brier score
- ranked probability score (RPS)
- exact-score negative log likelihood

For every loss, delta is defined as `challenger - baseline`, so negative is better.

The report includes the fraction of rolling windows in which the challenger is better, the best and worst window deltas, and whether improvement occurs in every window. A positive full-period mean together with weak rolling stability is evidence against claiming a durable gain.

## Paired block bootstrap

`paired_block_bootstrap(...)` resamples whole `evaluation_block` clusters with replacement. The baseline and challenger are always resampled together on the same matches, preserving the paired comparison.

For each loss delta the report includes:

- observed untouched mean delta
- percentile confidence interval
- fraction of bootstrap replicates with delta < 0
- whether the interval excludes zero in favor of the challenger

The default is 2,000 replicates and a deterministic seed for reproducibility.

These intervals are descriptive uncertainty for a frozen `TEST_UNTOUCHED` experiment. Looking at them and then changing the model contaminates the test set. A changed model requires a new future untouched block or a newly registered experiment.

## Why rolling evaluation

Football forecasting literature has long evaluated models through time rather than only as one pooled average. Dixon and Coles-style work reports rolling predictive likelihood, and newer football modelling work continues to use rolling or sequential out-of-sample prediction. JARVIS follows that principle while adding paired block uncertainty estimates around model-vs-baseline loss differences.

## Promotion interpretation

A challenger should not be described as more accurate merely because one aggregate metric is lower. Stronger evidence is:

1. lower paired proper-score losses on `TEST_UNTOUCHED`;
2. improvement across multiple rolling windows rather than one favorable period;
3. paired block-bootstrap intervals that are compatible with a stable improvement;
4. acceptable calibration and no severe class-specific regression;
5. replication on a subsequent untouched chronological block.

Production v7.2 remains unchanged by this protocol.
