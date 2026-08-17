# Dynamic Opponent-Adjusted Football Strength

This research module estimates current team attack and defence-weakness effects from historical score observations while respecting a prematch cutoff.

For a match between home team `i` and away team `j`:

```text
lambda_home = registered_home_baseline * exp(attack_i + defence_weakness_j)
lambda_away = registered_away_baseline * exp(attack_j + defence_weakness_i)
```

Each historical match is weighted by exponential time decay. Attack and defence parameters are fitted jointly with L2 regularization, so opponent quality affects the estimated team effects instead of being ignored by a simple recent-match average.

## Identifiability and baseline preservation

Version `jarvis-opponent-adjusted-strength-v0.2.0` uses explicit sum-to-zero contrasts:

```text
sum_i attack_i = 0
sum_i defence_weakness_i = 0
```

The L2 penalty is applied to the reconstructed team effects through the contrast penalty matrix, not merely to an arbitrary reference team's free parameters. This keeps attack and defence as relative team strengths and prevents the layer from absorbing an unregistered global scoring intercept.

The scoring baselines remain explicit per observation. This is deliberate: neutral-site observations must not silently inherit a true-home advantage, and team effects must not silently replace the registered venue/competition scoring level.

The first version family remains a research challenger only. It does not replace the existing JARVIS champion until chronological paired evaluation shows an improvement.

## Guardrails

- only `event_at < cutoff_at` and `available_at <= cutoff_at` rows are used;
- duplicate match IDs are rejected;
- attack and defence effects each sum to zero over fitted teams;
- unseen teams shrink exactly to the registered scoring baseline;
- unconverged fits cannot be used for prediction;
- lambda bounds are numerical safety rails, not football claims.
