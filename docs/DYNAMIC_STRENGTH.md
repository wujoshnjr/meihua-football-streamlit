# Dynamic Opponent-Adjusted Football Strength

This research module estimates current team attack and defence-weakness effects from historical score observations while respecting a prematch cutoff.

For a match between home team `i` and away team `j`:

```text
lambda_home = registered_home_baseline * exp(attack_i + defence_weakness_j)
lambda_away = registered_away_baseline * exp(attack_j + defence_weakness_i)
```

Each historical match is weighted by exponential time decay. Attack and defence parameters are fitted jointly with L2 regularization, so opponent quality affects the estimated team effects instead of being ignored by a simple recent-match average.

The scoring baselines are explicit per observation. This is deliberate: neutral-site observations must not silently inherit a true-home advantage. A dataset builder is responsible for registering the correct prematch venue baseline before fitting.

The first version is a research challenger only. It does not replace the existing JARVIS champion until chronological paired evaluation shows an improvement.

## Guardrails

- only `event_at < cutoff_at` and `available_at <= cutoff_at` rows are used;
- duplicate match IDs are rejected;
- unseen teams shrink exactly to the registered scoring baseline;
- unconverged fits cannot be used for prediction;
- lambda bounds are numerical safety rails, not football claims.
