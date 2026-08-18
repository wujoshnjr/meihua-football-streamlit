# Production artifacts

`artifacts/live_meihua.json` is intentionally **absent** until an M2 Meihua challenger completes the registered chronological workflow.

The live application always computes the deterministic Meihua snapshot and its feature fingerprint. Meihua may change Football lambdas / 1X2 probabilities only when this directory contains a valid `jarvis-live-meihua-artifact-v1.0.0` deployment artifact.

A deployable artifact must bind all of the following:

1. `model_family = M2_MEIHUA`;
2. a converged `MEIHUA` residual fit trained on at least 200 `TRAIN` matches;
3. the exact Football baseline model version and score-model configuration;
4. the `VALIDATION`-selected shrinkage alpha and tuning artifact SHA-256;
5. an M2-specific `CALIBRATION` temperature artifact SHA-256;
6. an `ELIGIBLE_FOR_HUMAN_REVIEW` promotion report SHA-256 produced from the preregistered `TEST_UNTOUCHED` review;
7. explicit `approved_for_live = true`, reviewer identity, approval timestamp and source Git commit;
8. a canonical deployment artifact SHA-256.

The loader rejects tampered hashes, late/manual coefficient fragments, wrong model families, mismatched feature schemas, non-converged fits, wrong Football baselines and artifacts that have not received explicit live approval.

This gate is deliberate: traditional Meihua state is formally present in the production pipeline, but the repository does not invent hand-written mappings such as `生體 = +x% home win`. Numeric influence must come from frozen historical out-of-sample evidence.
