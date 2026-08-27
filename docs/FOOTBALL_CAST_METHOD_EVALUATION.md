# Football Cast-Method Evaluation Protocol

## Goal

JARVIS is not intended to become a permanent database of football divination cases.

The football research goal is narrower:

> compare reproducible casting / charting methods and identify which method produces the most accurate and stable football predictions.

Individual cast outputs are transient evaluation material. They are not persisted by the project.

## No-persistence rule

The evaluation workflow must not automatically write individual match casts, packets, interpretations or outcomes into a repository database or case registry.

Allowed:
- temporary in-memory evaluation rows;
- user-supplied files for a one-off batch;
- aggregate method metrics displayed in the current session;
- optional user-initiated export of aggregate results.

Not part of the product:
- a permanent per-match cast registry;
- automatic storage of every prediction;
- long-term retention of individual Case Bundles for benchmarking.

Existing downloadable Packet / Case Bundle artifacts remain user-controlled handoff files, not server-side persistence.

## What is being compared

A candidate method must be explicitly defined before comparison. Examples may include different legitimate casting conventions, event-differentiation constructions, or method variants already implemented by JARVIS.

Every candidate must declare:
- method ID and version;
- exact required inputs;
- casting / charting rule;
- time convention and timezone handling;
- source authority: classical source, crosschecked reconstruction, or project adaptation;
- prediction role: result engine, structural stress test, or supporting context.

A method may not be relabeled as classical when it is a project adaptation.

## Fair-comparison rule

For one evaluation batch:

1. Use the same fixture set for every candidate method.
2. Use the same prematch information boundary.
3. Do not change a method after inspecting a match outcome within that batch.
4. Do not exclude difficult matches only because a method missed them.
5. Keep simultaneous-kickoff collisions visible.
6. Separate casting/chart errors from interpretation/final-call errors.

Historical completed matches may be used for method research, but the candidate method definition must be frozen before its output is compared with the known result. No post-result symbol picking or rule retuning is allowed.

## Accuracy metrics

The primary metric depends on the method role.

### Result-engine methods

Primary:
- 1X2 accuracy: home win / draw / away win.

Secondary, only when the method is designed to output score candidates:
- exact-score hit rate;
- top-N score-candidate hit rate;
- goal-difference absolute error;
- total-goals absolute error.

Do not force score metrics onto methods whose contract does not produce scores.

### Structural / stress-test methods

Meihua-style structural methods must not be judged as a second independent score predictor when their contract is structural.

Evaluate them against their declared outputs, for example:
- whether the predicted pressure/control direction matched the observed match structure;
- whether a declared turning-point condition occurred;
- whether the method correctly supplied support or counter-evidence to the result engine.

These structural labels require an explicit evaluation rubric before use; they must not be invented after seeing the match.

## Method ranking

Do not rank methods from one match or a very small sample.

For each candidate report, at minimum:
- evaluated match count;
- 1X2 accuracy when applicable;
- draw accuracy separately;
- same-kickoff collision subset performance;
- performance by competition / context when sample size is sufficient;
- number of abstentions or invalid casts;
- method version.

Prefer stability across batches over one unusually strong batch.

## Failure analysis

When a prediction fails, classify the failure before changing a method:

- EVENT_DATA: wrong kickoff, timezone, team identity, or other prematch input.
- CAST: chart / hexagram construction error.
- METHOD_MAPPING: the chosen football mapping was wrong.
- INTERPRETATION: deterministic facts were correct but read incorrectly.
- FINAL_CALL: synthesis chose the wrong winner / score candidate.
- COLLISION: simultaneous fixtures were not validly differentiated.

Do not use a missed result as permission to rewrite the cast after the fact.

## Recommended JARVIS workflow

```text
fixture batch
    ↓
same normalized prematch inputs
    ↓
candidate method A ─┐
candidate method B ─┼─ transient outputs in current evaluation
candidate method C ─┘
    ↓
compare with outcomes
    ↓
aggregate metrics + failure counts
    ↓
discard individual transient cast rows
```

The project should preserve method definitions, validators and reproducible algorithms. It does not need to preserve every football cast result.

## Current research priority

The next football-research improvements should focus on:

1. enumerating candidate casting methods that are sufficiently defined to test;
2. making each candidate deterministic and source/authority labeled;
3. building an ephemeral batch evaluator;
4. comparing methods on the same match cohorts;
5. retaining only aggregate method-performance summaries when persistence is desired.

The objective is method selection, not case archiving.
