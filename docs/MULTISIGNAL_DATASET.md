# JARVIS multi-signal historical dataset

Status: RESEARCH ONLY.

`jarvis.research.dataset` constructs one deterministic historical row for the same match and cutoff across Football, Qimen and Meihua. The observed 90-minute score is stored only as the post-match label; it does not enter any signal feature calculation.

## Inputs

Each row requires:

- an immutable historical fixture with `match_id`, competition, event-local kickoff, IANA timezone, team IDs and venue mode;
- an explicit `schedule_available_at`, proving the kickoff information needed to cast Qimen/Meihua was known by the model cutoff;
- a `PrematchFeatureSnapshot` built only from football information available by the same cutoff;
- immutable TRAIN / VALIDATION / CALIBRATION / TEST_UNTOUCHED role, evaluation block and experiment ID;
- the registered 90-minute plus added-time home/away score label.

## Generated signal families

From the exact same event record the builder produces:

1. Football snapshot reference and model input.
2. Qimen raw outcome snapshot plus reference-coded numeric features.
3. Meihua raw snapshot plus reference-coded numeric features.

Qimen and Meihua are generated only from the fixture's registered event time/timezone. Their snapshot `available_at` is the schedule availability time, not the end of the match.

## Integrity rules

The builder rejects rows when:

- `schedule_available_at > cutoff`;
- `cutoff >= event_at`;
- football competition or team IDs do not match the fixture;
- venue/dataset-role metadata is invalid;
- the observed score is not a non-negative integer pair.

The resulting `PrematchExperimentRecord` independently rechecks that all three signal snapshots satisfy `available_at <= cutoff < event_at`.

## Provenance

The row stores both the original football snapshot fingerprint and a SHA-256 hash of its serialized payload. Qimen and Meihua snapshots are separately hashed. A final row fingerprint hashes the common experiment-record fingerprint, football model input and both signal families.

This design is intended to make M0/M1/M2/M3 comparisons reproducible and to prevent a later result label, changed schedule, or mismatched football snapshot from silently changing the experiment.
