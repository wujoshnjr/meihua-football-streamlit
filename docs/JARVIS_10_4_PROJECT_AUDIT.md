# JARVIS 10.4 Project Audit

Audit date: 2026-08-27  
Branch: `agent/jarvis-10-4-project-audit`

## Scope

This audit reviews the repository as a reproducible divination / source-review / AI-handoff system, not as a statistical football predictor. It checks runtime contracts, schemas, Streamlit workflows, time handling, source authority boundaries, football event differentiation, Yuanling reconstruction, test coverage and stale documentation.

## High-priority defects found and corrected

### 1. Yuanling UI packet-version drift

**Problem:** the Yuanling page still displayed `YUANLING_YANSHU_PACKET_V1_2` while the runtime packet and schema were already V1.3.

**Fix:** the UI now imports `YUANLING_PACKET_VERSION` and displays the runtime contract dynamically.

### 2. Ri-Qimen experiment-mode runtime KeyError

**Problem:** the UI read `riqimen_base.calendar.ju_label`, but the backend exposed only `ju`. The normal page-start smoke test could not detect this because it did not execute the experiment result branch.

**Fix:** `ju_label` is now emitted by `build_riqimen_base`, required by the V1.3 schema and regression-tested.

### 3. Yuanling research-status documentation drift

**Problem:** README/Home/UI still stated that the 數主/飛星/直日星 relationship and Ri-Qimen 穿宮 were unresolved after those contracts had already been crosschecked and implemented.

**Fix:** documentation now distinguishes:
- resolved/crosschecked role relationship;
- resolved/crosschecked through-palace mechanics;
- still-gated raw primary autofill;
- remaining number-palace / entry-door / full worked-example gaps.

### 4. Football event-differentiation backend was not wired to the UI

**Problem:** `FOOTBALL_EVENT_IDENTITY_V1`, `MEIHUA_EVENT_IDENTITY_V1` and `QIMEN_PARTICIPANT_LAYER_V1` existed but normal users could not supply their inputs from the main football workflow.

**Fix:** the football page now accepts canonical fixture identity fields and optional coach birth-year Ganzhi, displays differentiation signatures and exposes the project-adaptation authority boundary.

### 5. Yuanling was not part of the football case object

**Problem:** the architecture described Yuanling as a temporal layer, but `DIVINATION_CASE_BUNDLE_V1` only packaged Qimen + Meihua.

**Fix:** `DIVINATION_CASE_BUNDLE_V2` accepts an optional Yuanling V1.3 temporal sibling, verifies its SHA, checks datetime/timezone alignment and incorporates deterministic Yuanling data into the temporal signature.

### 6. New football identity fields were under-specified by JSON Schema

**Problem:** `DIVINATION_PACKET_V2` allowed arbitrary extra properties and therefore did not actually validate the new event / participant contracts.

**Fix:** formal schema definitions now validate event identity, deterministic event Meihua cast, participant authority and ready-state signatures.

### 7. Inconsistent DST handling across pages

**Problem:** Football/Yuanling pages explicitly rejected ambiguous DST wall times until the user selected a fold, while standalone Qimen/Meihua pages used an older helper that silently defaulted to fold=0. Those pages also used five-minute input granularity.

**Fix:** all user-facing casting paths now use the same second-level `jarvis.time` inspection and explicit ambiguous-time policy.

### 8. Coach “Ganzhi year-life palace” wording overstated the implementation

**Problem:** `QIMEN_PARTICIPANT_LAYER_V1` stored a full birth-year Ganzhi, but palace placement actually used the birth-year **stem only**. The branch did not participate in placement.

**Fix:** V1 now explicitly records `placement_basis=BIRTH_YEAR_STEM_ON_HEAVEN_PLATE__BRANCH_RETAINED_FOR_IDENTITY_ONLY` and states that it is not a complete classical year-life algorithm.

## Current architecture after audit

### Temporal layers

- Shijia Qimen board
- Year/month/day/hour Meihua temporal hexagram
- Optional Yuanling Qiyao deterministic temporal reconstruction

These layers may legitimately collide across simultaneous fixtures.

### Event-specific layers

- `FOOTBALL_EVENT_IDENTITY_V1`
- deterministic `MEIHUA_EVENT_IDENTITY_V1`
- optional `QIMEN_PARTICIPANT_LAYER_V1`

These must be pre-match fixed, reproducible and independent of query order and match result.

### Collision gate

If temporal signatures are identical but fixture identities differ, any differing interpretation must identify event/participant evidence. If event identity is missing, cross-fixture differentiation is explicitly unsafe.

## Remaining research / product gaps

### P0 — correctness / research integrity

1. **Yuanling 數宮 complete primary algorithm remains source-tiered.** The collateral Dongting method is reproducible, but should not silently overwrite the Yuanling raw slot.
2. **Yuanling 入門 complete Yanshu mechanics remain unresolved.** Do not substitute the production Shijia chief door.
3. **Ri-Qimen lacks a complete Yuanling end-to-end worked example.** Through-palace mechanics are crosschecked, but authority remains reconstruction rather than full primary golden certification.
4. **Coach participant V1 is year-stem placement only.** A full classical 年命 model requires additional source research before changing the contract.
5. **Football event-Meihua hash mapping is a project adaptation.** Its predictive value must be evaluated only under frozen blind-test rules; it must never be redescribed as a transmitted classical formula.

### P1 — engineering / product

1. Add a persistent blind-test case registry with immutable `input_frozen_at`, source URLs/IDs, method versions and final pre-match interpretation.
2. Add batch collision-group audit so a whole kickoff window can be checked for temporal duplicates before interpretation.
3. Add stronger stateful Streamlit tests for submitted forms, not only page-start smoke tests.
4. Add a migration note for legacy `DIVINATION_CASE_BUNDLE_V1` and old Yuanling packet schemas.
5. Normalize repository/product metadata that still describes the project as an “automatic predictor”.

### P2 — validation / research program

1. Build blind collision cohorts: same kickoff / same temporal signature / different fixtures.
2. Freeze event-identity canonicalization and coach identity before outcome access.
3. Report failures by layer: source data, calendar/cast, identity, mapping, interpretation, final call.
4. Never retune hash slices, coach rules, time offsets or method selection after seeing outcomes.
5. Separate accuracy claims by version; do not pool results across changed method contracts.

## Explicit non-claims

JARVIS does not claim:
- that all historical Qimen / Meihua / Yuanling schools are unified;
- that all Yuanling algorithms are primary-source complete;
- that coach birth-year stem is the unique correct football participant mapping;
- that event-hash Meihua is a classical formula;
- that symbolic layers produce calibrated probabilities;
- that repository completeness implies football predictive accuracy.

The intended boundary remains: **JARVIS casts, retrieves, reconstructs, validates and packages evidence; ChatGPT performs the final interpretation under the frozen case contract.**
