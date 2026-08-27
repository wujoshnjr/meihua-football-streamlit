# JARVIS Casting Method Benchmark

## Goal

The research goal is to identify the **most accurate casting method for football use**.

JARVIS does **not** need a persistent archive of every complete cast, packet, or interpretation in order to answer that question.

The benchmark should compare methods under the same fixtures, same information cutoff, same scoring rule, and same interpretation contract.

## Persistence boundary

Do not build a permanent "case registry" that stores every full Qimen/Meihua/Yuanling result.

Persistent project data should be limited to:

- method ID and version;
- frozen method definition;
- benchmark dataset definition / fixture IDs;
- scoring rule version;
- aggregate metrics;
- optional compact error counts by category.

Full cast packets, full divination texts, and case-by-case interpretation traces may exist transiently during a benchmark run, but they are not required as a permanent project database.

## What is being compared

A "casting method" must be treated as a frozen contract. Any change creates a new method ID.

Current Meihua candidates include:

1. **MEIHUA_YMDH_XIANTIAN_V1**
   - Current production year/month/day/hour number method.
   - Source-aware classical classification: XIANTIAN_NUMBER_METHOD.

2. **MEIHUA_EVENT_IDENTITY_V1**
   - Deterministic fixture-identity hash mapping.
   - Authority: PROJECT_ADAPTATION.
   - Must never be described as a transmitted classical formula.

Future candidates may be added only after their rules are explicit and deterministic, for example:
- another source-grounded time-number convention;
- a properly implemented Houtian/object method;
- a source-locked alternative day-boundary or leap-month convention.

Qimen variants should be benchmarked separately from Meihua casting-method variants unless the experiment explicitly tests a combined contract.

## Benchmark rules

Each candidate method must receive the same prematch inputs.

The benchmark must not:
- change a method after seeing outcomes;
- select different methods for different matches after the fact;
- alter kickoff time, timezone, home/away mapping, hash slices, body/use rules, or interpretation prompt after outcome access;
- treat post-match information as prematch evidence.

## Accuracy targets

Accuracy must be reported by task, not collapsed into one vague score.

Recommended metrics:

### Result direction
For methods that are allowed to predict 1X2:
- exact 1X2 accuracy;
- balanced accuracy when class imbalance matters;
- draw recall;
- home-win recall;
- away-win recall.

### Structural / phase judgement
For Meihua when used as STRUCTURE_STRESS_TEST:
- phase-direction agreement under a predefined rubric;
- turning-point detection agreement;
- support / counter-signal calibration.

Do not force Meihua into a score metric when the method contract does not output a score.

### Collision performance
For simultaneous fixtures:
- accuracy within temporal-collision cohorts;
- error rate when only temporal input is available;
- incremental value of event-identity differentiation.

## Selection rule

The "best method" is the method with the strongest **out-of-sample** performance under the task it is actually designed to perform.

Do not select the winner from training/tuning cases.

When two methods are statistically indistinguishable, keep both as unresolved rather than declaring a false winner.

## Minimum benchmark output

A benchmark run only needs to return a compact comparison table such as:

| Method | Task | N | Accuracy | Draw recall | Collision N | Collision accuracy |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| MEIHUA_YMDH_XIANTIAN_V1 | structure | ... | ... | n/a | ... | ... |
| MEIHUA_EVENT_IDENTITY_V1 | experiment | ... | ... | n/a | ... | ... |

The full cast results do not need to be persisted.

## Research interpretation

A method can be:
- SOURCE_GROUNDED;
- SOURCE_CROSSCHECKED_RECONSTRUCTION;
- PROJECT_ADAPTATION;
- EXPERIMENTAL.

Accuracy and source authority are separate dimensions.

A project adaptation may empirically outperform a classical method, but that does not make it classical.
A classical method may be source-faithful but empirically weak for football.

JARVIS should report both facts without conflating them.
