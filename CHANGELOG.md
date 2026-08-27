# Changelog

## 10.4.0-alpha.2 — COLLISION COHORT + QA HARDENING

### Batch collision audit
- Add `FOOTBALL_COLLISION_GROUP_AUDIT_V1` for up to 50 `DIVINATION_CASE_BUNDLE_V2` artifacts.
- Group cases by deterministic temporal signature before interpretation.
- Distinguish safe cross-fixture collisions only when prematch event identities are present.
- Mark missing event identity as `REVIEW_UNSAFE_COLLISION`; tampered/unsupported bundles fail before comparison.
- Add downloadable collision-audit JSON and formal JSON Schema.

### Stateful UI regression
- Add submitted-state Streamlit tests for the Yuanling Ri-Qimen experiment branch.
- Add submitted-state Streamlit test for full football Case Bundle construction.
- Keep page-start smoke tests, but no longer rely on them as the only UI coverage.

### Migration safety
- Add `docs/MIGRATION_10_4.md`.
- Explicitly prohibit relabeling legacy artifacts or reconstructing prematch identity from post-match knowledge.
- Keep legacy Packet V1 / Bundle V1 schemas for compatibility only.

**No method/accuracy claim:** alpha.2 changes QA, cohort auditing and artifact lifecycle only; it does not alter source-locked divination rules or claim predictive improvement.

## 10.4.0-alpha.1 — MULTI-LAYER FOOTBALL CASE + PROJECT AUDIT

### Football event differentiation
- Wire `FOOTBALL_EVENT_IDENTITY_V1` into the primary football UI.
- Freeze canonical fixture identity from competition, season, official English home/away names and scheduled kickoff UTC.
- Expose deterministic `MEIHUA_EVENT_IDENTITY_V1` as a project adaptation, not a transmitted classical formula.
- Expose optional `QIMEN_PARTICIPANT_LAYER_V1`; V1 placement uses the coach birth-year **stem only**, while the branch is retained for identity audit.
- Display temporal / event / participant signatures and block unsupported cross-fixture differentiation when event identity is missing.

### Case Bundle V2
- Upgrade football handoff to `DIVINATION_CASE_BUNDLE_V2`.
- Add optional `YUANLING_YANSHU_PACKET_V1_3` as `TEMPORAL_NUMERIC_CONTEXT`.
- Verify Yuanling SHA and datetime/timezone alignment.
- Include deterministic Yuanling reconstruction in the temporal signature when present.
- Keep Qimen=RESULT_ENGINE_INPUT, Meihua=STRUCTURE_STRESS_TEST, Yuanling=TEMPORAL_NUMERIC_CONTEXT; no three-system voting.

### Yuanling corrections
- Align UI text with the crosschecked 數主 / 飛星 / 直日星 role reconstruction.
- Align UI text with resolved Ri-Qimen through-palace mechanics: Qimen nine stars fly numeric 1→…→9 with center included; doors remain on the eight-palace ring.
- Fix experiment-mode `ju_label` runtime contract and require it in the V1.3 schema.
- Remove stale V1.2 UI labels.

### Time correctness
- Unify standalone Qimen / Meihua pages with the second-level, DST-aware event-time contract.
- Ambiguous DST wall times now require explicit fold selection instead of silently defaulting to fold=0.

### Schema / audit
- Formally validate event-identity and participant-layer objects in `DIVINATION_PACKET_V2`.
- Add `schemas/divination_case_bundle_v2.schema.json`.
- Add project-wide audit at `docs/JARVIS_10_4_PROJECT_AUDIT.md`.
- Preserve unresolved source gaps rather than promoting collateral reconstruction to primary facts.

**No accuracy claim:** this release improves reproducibility, collision handling, source honesty and engineering consistency. It does not claim improved football predictive accuracy.

## 10.3.0-alpha.1 — YUANLING SOURCE RECONSTRUCTION

JARVIS 10.3 begins a source-first 《奇門遁甲元靈經》 layer. The alpha deliberately prioritizes reconstructable classical facts and explicit uncertainty over producing numeric football answers.

### Method separation
- Add independent `yuanling.yanshu_qiyao` and `yuanling.riqimen` modules.
- Do **not** claim that 演數七要 must use 日奇門 as its base chart merely because the sections are adjacent.
- Add `RIQIMEN_QIYAO_EXPERIMENT` only as an explicitly project-level bridge that preserves both source objects separately.

### Yanshu Qiyao
- Fix the primary seven-factor contract at 數宮 / 數主 / 飛星 / 入門 / 直日星 / 日干 / 時支.
- Preserve source wording `遁至本時之星即為數主` while leaving the complete star-flight algorithm unresolved until source reconstruction is stronger.
- Add number-chief landing-state review using the primary black-star example; Luoshu element assignments remain clearly labeled project normalization.
- Keep unresolved factors as `UNRESOLVED_BY_SOURCE_AUDIT` rather than inferring them from the Shijia rotating-plate engine.

### Numeric-star registry
- Add an independent 一白/二黑/三碧/四綠/五黃/六白/七赤/八白/九紫 registry with 太乙/攝提/軒轅/招搖/天符/青龍/咸池/太陰/天乙 and Beidou-style aliases where source-supported.
- Explicitly prohibit silent reuse of Shijia 天蓬/天芮/天沖/... as Yanshu numeric stars.

### Ri-Qimen
- Materialize and exact-test the full 60-day `某宮起休` table from the Yuanling Ri-Qimen section.
- Build a source-grounded base with event-local calendar, solar term, three-yuan, dun, Ju, earth plate and day xun.
- Keep `值符之上星加本日干穿宮數去` as unresolved; current status is `PARTIAL_SOURCE_GROUNDED__HEAVEN_PLATE_PENDING`.

### Collateral reconstruction
- Add a separate `COLLATERAL_QIMEN_TEXT_RECONSTRUCTION` authority tier.
- Reconstruct day-nine-star candidate charts from 《金函玉鏡》 with exact Yang/Yin 甲子 anchors.
- Reconstruct a candidate current-time/數宮 from 《奇門寶鑑》洞庭老人法, including 酉/戌/亥 repeating 子/丑/寅.
- Expose candidate number palace, daily-nine-star chart, star at number palace and center daily star without populating Yuanling primary slots.
- Preserve cross-text variants rather than silently emending the Yuanling transcription: `入門` vs `八門`; black-star example `乾宮` vs `坤宮`.

### Packet / UI / validation
- Add deterministic `YUANLING_YANSHU_PACKET_V1` and JSON Schema.
- Add `/yuanling` Streamlit research page with DST-aware time entry, primary-factor audit, collateral candidate display and optional Ri-Qimen experiment view.
- Add dedicated `tools/validate_yuanling.py`, pytest coverage and CI step.
- Register Yuanling primary/crosscheck/collateral sources in `knowledge/sources.json`.

### Hard boundaries
- `raw_numeric_candidates=[]` until algorithm source-lock.
- `score_synthesis=DEFERRED_UNTIL_BLIND_TEST_PROTOCOL`.
- No `數宮3 → 3球`, no automatic total-goals/score/probability, no post-match fitting, no silent Shijia substitution and no promotion of collateral candidates to Yuanling primary facts.

**Alpha completeness statement:** this release establishes a reproducible Yuanling research architecture and several source/collateral mechanical layers. It does not yet claim the exact relationship among 數主 / 飛星 / 直日星 or the Ri-Qimen `穿宮數去` heaven-plate mechanics are fully source-locked.

## 10.2.0 — JARVIS DEEP DIVINATION REVIEW

JARVIS 10.2 completes Issue #62's deep-review acceptance while preserving the product boundary: **JARVIS casts, retrieves, audits, and packages; ChatGPT performs final interpretation.** No predictive-accuracy improvement is claimed.

### Football case workflow
- Add `MATCH_EVENT_V1` deterministic same-event identity.
- Add `DIVINATION_CASE_BUNDLE_V1` with packet SHA verification and strict home/away/event-datetime/IANA-timezone alignment.
- Add the `⚽ 足球 Case` workspace to create Qimen + Meihua from one event input or re-import existing packets.
- Formalize Qimen=`RESULT_ENGINE_INPUT`, Meihua=`STRUCTURE_STRESS_TEST`, ChatGPT=`FINAL_SYNTHESIS`.

### Time precision
- Upgrade runtime to `streamlit==1.61.0`; support second-level event time.
- Pin `tzdata==2026.3` as IANA tzdb fallback.
- Add DST nonexistent/ambiguous local-time inspection and explicit `fold=0/1` handling.
- Add configurable 120/150/180/210-minute Meihua football wall-clock audit, default 180.
- Detect hour-branch, civil-date, lunar-date and UTC-offset boundaries with immutable kickoff anchor and `SECONDARY_DIAGNOSTIC_ONLY` recasts.
- Add optional timestamped match-clock events; wall-clock is never silently presented as official match minute.

### Meihua classical-method fidelity
- Add `MEIHUA_CLASSICAL_METHOD_AUDIT` and distinguish `XIANTIAN_NUMBER_METHOD` from `HOUTIAN_OBJECT_METHOD`.
- Current year/month/day/hour engine is Xianti-number method; Zhouyi text is `SUPPORTING` while body/use, strength and mutual/change remain primary.
- Add explicit `body_mutual` / `use_mutual` identities while preserving raw `mutual_upper` / `mutual_lower`.
- Preserve 三要／十應／外應 as `NOT_RECORDED` until contemporaneous inputs exist; prohibit post-event backfill.
- Version leap-month and day-boundary conventions explicitly.

### Zhouyi 384-line deep review
- Materialize conditional `meaning_review` for **384/384** standard lines.
- Each review includes source text/provenance, text conditions, action/risk boundaries, turning-point lens, conditional tendency, misread warnings, ambiguity and football source-basis/observable/counter-signal fields.
- Authority is `PROJECT_REVIEW__NOT_CLASSICAL_COMMENTARY`; CI rejects automatic probability/fixed-score/final-result fields.

### Meihua × Zhouyi × Yilin coherence
- Verify Zhouyi original/changed ↔ Yilin from/to source pair before synthesis.
- Compare semantic domains only as `PROJECT_HEURISTIC`; preserve non-overlapping domains as independent signals.
- Source mismatch becomes a blocking contradiction.
- Add contradiction, uncertainty, source-coverage, method-weighting and temporal-context registers.

### Qimen review completion
- Keep the existing four-family catalog correctly named **Qimen Core 306 Matrix**.
- Materialize **378 static Extended Relations** with `PROJECT_HEURISTIC__COMPONENTS_SOURCE_BACKED` authority: 64 deity×door, 72 deity×star, 72 deity×palace, 80 stem×door, 90 stem×star.
- Keep void/horse/Fu Yin/Fan Yin/door pressure/tomb/punishment and related state modifiers as runtime condition stacks, not votes.
- Add four `SOURCE_DERIVED_METHOD_GOLDEN` fixtures anchored to 《遁甲演義》卷二: Yang4/Yiyou Tian Dun, Yin6/Gengshen Tian Dun, Yang1/Xinmao Di Dun, Yin9/Xiazhi Bingyin Di Dun.
- Golden validation checks full core earth plate, heaven stems, stars, doors, chief star/door and source anchor palace.
- These classical examples do not provide a complete Gregorian/IANA event and deity naming is method-dependent, so 10.2 **does not** claim full end-to-end calendar+timezone+deity external certification.

### Validation / release gates
CI requires pinned Yilin/Zhouyi rebuilds and zero diffs; Zhouyi textual/semantic/384-line validators; deep review; Meihua method/temporal/coherence validators; Qimen source-golden, Extended Relations and honesty-gate validators; Ruff; pytest; knowledge and Yilin validation.

**Completeness statement:** 10.2 completes Issue #62 acceptance for source-aware 64/384 review, Meihua deep packet review, football evidence/counter-evidence, reconstructable Qimen method-golden tests and extended Qimen review. It does not claim all historical editions, all Qimen schools, every Meihua casting method, or full end-to-end external Qimen chart certification are complete.

## 10.1.0 — JARVIS KNOWLEDGE COMPLETION
- Add pinned `kanripo/KR1a0001` Zhouyi source review at commit `8284adbf9e3435d713180e24f05bf75f8b7d1d96`.
- Materialize 64/64 hexagrams, 384/384 standard lines, guaci/Tuan/Da Xiang/line texts, 378 directly mapped Xiaoxiang, Qian grouped-source exception and Qian/Kun special lines.
- Add source-aware semantic review and `DIVINATION_PACKET_V2` with formal JSON Schema.
- Rename the existing Qimen relation catalog **Core 306 Matrix** and explicitly stop calling it all Qimen relations.

## 10.0.0 — JARVIS 10 YILIN FUSION
- Complete pinned WYG `kanripo/KR3g0029` Yilin matrix at **4096/4096** unique pairs and 64/64 source blocks.
- Preserve source text, raw transcription, page/volume, notes, gaiji, source-label anomaly, pinned commit and hashes.
- Add `MEIHUA_YILIN_BRIDGE`: original Meihua hexagram → final changed hexagram as transformation lens, not Jiaolin day-assignment practice.

## 9.1.0 — OPERATION STARK DEEP READING
- Add Qimen 8-layer palace reading hierarchy and deity/state-modifier deep profiles.
- Add Meihua original/mutual/changed roles, body/use strength, moving-line depth roles and football observation dimensions.

## 9.0.0 — OPERATION STARK
- Reset product scope to divination knowledge/casting/AI handoff.
- Remove former Football ML/research predictor product and calibration/training infrastructure.
- Establish: **JARVIS provides chart/book/source/review; ChatGPT interprets.**