# Changelog

## 10.2.0 — JARVIS DEEP DIVINATION REVIEW

JARVIS 10.2 completes Issue #62's deep-review acceptance while preserving the product boundary: **JARVIS casts, retrieves, audits, and packages; ChatGPT performs final interpretation.** No predictive-accuracy improvement is claimed.

### Football case workflow

- Add `MATCH_EVENT_V1` deterministic same-event identity.
- Add `DIVINATION_CASE_BUNDLE_V1` with packet SHA verification and strict home/away/event-datetime/IANA-timezone alignment.
- Add the `⚽ 足球 Case` Streamlit workspace to create Qimen + Meihua from one event input, or re-import two existing packets and rebuild the bundle.
- Formalize football roles: Qimen=`RESULT_ENGINE_INPUT`, Meihua=`STRUCTURE_STRESS_TEST`, ChatGPT=`FINAL_SYNTHESIS`.
- Qimen may supply the evidence layer from which ChatGPT makes a regulation-time result / limited score-candidate judgment; Meihua does not emit an independent second result for voting.

### Time precision

- Upgrade runtime to `streamlit==1.61.0`; use second-level `st.time_input` when needed.
- Pin `tzdata==2026.3` as a reproducible IANA tzdb fallback.
- Add DST nonexistent/ambiguous local-time inspection and explicit PEP 495 `fold=0/1` handling.
- Keep the Meihua kickoff anchor immutable and add a configurable 120/150/180/210-minute football wall-clock audit (default 180).
- Detect hour-branch, civil-date, lunar-date, and UTC-offset boundaries using UTC-monotonic scanning.
- Boundary recasts remain `SECONDARY_DIAGNOSTIC_ONLY`; crossing an hour branch is not treated as automatic reversal.
- Add optional timestamped match-clock events; wall-clock elapsed time is never silently presented as official match minute.

### Meihua classical-method fidelity

- Add `MEIHUA_CLASSICAL_METHOD_AUDIT` and distinguish `XIANTIAN_NUMBER_METHOD` from `HOUTIAN_OBJECT_METHOD`.
- Current year/month/day/hour production engine is explicitly Xianti-number method; Zhouyi text is `SUPPORTING`, while body/use, strength, mutual/change, motion/static and internal/external structure remain primary.
- Add explicit `body_mutual` / `use_mutual` identities while preserving raw `mutual_upper` / `mutual_lower` positions.
- Preserve 三要／十應／外應 as `NOT_RECORDED` until real contemporaneous inputs exist; prohibit post-event backfill.
- Version leap-month and day-boundary conventions explicitly; engine schema advances to the 0.3 line.

### Zhouyi 384-line deep review

- Materialize a conditional `meaning_review` for **384/384** standard lines.
- Every moving-line review carries source text/provenance plus text conditions, action boundary, risk boundary, turning-point lens, conditional tendency, misread warnings, ambiguity, and football source-basis/observable/counter-signal fields.
- Authority is fixed as `PROJECT_REVIEW__NOT_CLASSICAL_COMMENTARY`; raw classical text remains primary evidence.
- CI validates exact 384/384 coverage and rejects automatic probability / fixed-score / final-result fields.

### Meihua × Zhouyi × Yilin coherence

- Add source-pair alignment between Zhouyi original/changed and Yilin from/to before synthesis.
- Compare semantic domains only as `PROJECT_HEURISTIC`; shared domains are conditional retrieval-level reinforcement, not classical mutual proof or outcome voting.
- Preserve non-overlapping domains as independent signals.
- Source mismatch becomes an explicit blocking contradiction.
- Add contradiction, uncertainty, source-coverage, method-weighting, and temporal-context registers to the Meihua packet.

### Qimen review completion

- Keep the existing four-family catalog correctly named **Qimen Core 306 Matrix**.
- Materialize **378 static Extended Relations** with `PROJECT_HEURISTIC__COMPONENTS_SOURCE_BACKED` authority:
  - 64 deity × door
  - 72 deity × star
  - 72 deity × palace
  - 80 stem × door
  - 90 stem × star
- Keep void/horse/Fu Yin/Fan Yin/door pressure/tomb/punishment and related state modifiers as runtime condition stacks, not extra votes.
- Add four `SOURCE_DERIVED_METHOD_GOLDEN` fixtures anchored to classical examples in 《遁甲演義》卷二 and reconstructed with the source rules recorded in 《奇門遁甲統宗》:
  - Yang Dun 4 / Yiyou / Tian Dun
  - Yin Dun 6 / Gengshen / Tian Dun
  - Yang Dun 1 / Xinmao / Di Dun
  - Yin Dun 9 / Xiazhi Bingyin / Di Dun
- Golden validation checks full core earth plate, heaven stems, stars, doors, chief star/door and the source anchor palace.
- Because the classical examples do not supply a complete Gregorian/IANA event and deity naming is method-dependent, 10.2 **does not** claim full end-to-end calendar+timezone+deity external certification.

### Validation / release gates

CI now requires:

- pinned Yilin rebuild + zero diff;
- pinned Zhouyi rebuild + zero diff;
- Zhouyi textual + semantic + 384-line conditional review validation;
- deep review contract;
- Meihua classical-method, temporal-precision, and cross-system-coherence validation;
- Qimen source-derived golden validation;
- Qimen Extended Relations validation;
- Qimen review-gate honesty validation;
- Ruff, pytest, knowledge validation, and Yilin validation.

**Completeness statement:** 10.2 completes the repository's Issue #62 acceptance criteria for source-aware 64/384 review, Meihua deep packet review, football evidence/counter-evidence, reconstructable Qimen method-golden tests, and extended Qimen review. It does not claim all historical editions, all Qimen schools, every Meihua casting method, or full end-to-end external Qimen chart certification are complete.

## 10.1.0 — JARVIS KNOWLEDGE COMPLETION

- Add pinned `kanripo/KR1a0001` Zhouyi source review at commit `8284adbf9e3435d713180e24f05bf75f8b7d1d96`.
- Materialize 64/64 hexagrams, 384/384 standard lines, guaci/Tuan/Da Xiang/line texts, 378 directly mapped Xiaoxiang, Qian grouped-source exception, and Qian/Kun special lines.
- Add source-aware semantic review and `DIVINATION_PACKET_V2` with formal JSON Schema.
- Rename the existing Qimen relation catalog **Core 306 Matrix** and explicitly stop calling it all Qimen relations.
- Keep corpus provenance, zero-diff rebuild validation, and project-heuristic boundaries explicit.

## 10.0.0 — JARVIS 10 YILIN FUSION

- Complete the pinned WYG `kanripo/KR3g0029` Yilin matrix at **4096/4096** unique pairs and 64/64 source blocks.
- Preserve source text, raw transcription, page/volume, notes, gaiji, source-label anomaly, pinned commit, and hashes.
- Add `MEIHUA_YILIN_BRIDGE`: exactly original Meihua hexagram → final changed hexagram as a transformation lens, not a claim to reproduce Jiaolin day-assignment practice.
- Add project image/semantic retrieval with football observable and counter-evidence while keeping classical text separate.

## 9.1.0 — OPERATION STARK DEEP READING

- Add Qimen 8-layer palace reading hierarchy and 8-deity/state-modifier deep profiles.
- Add Meihua original/mutual/changed roles, body/use strength, six moving-line depth roles, and football observation dimensions.
- Expand packet knowledge handoff without adding automatic result rules.

## 9.0.0 — OPERATION STARK

- Reset product scope to divination knowledge/casting/AI handoff.
- Keep deterministic Qimen and Meihua engines, knowledge vault, and AI packet.
- Remove the former Football ML/research predictor product and related calibration/training infrastructure.
- Establish the core rule: **JARVIS provides chart/book/source/review; ChatGPT interprets.**

For pre-9.0 historical details, use repository history and the corresponding merged pull requests.
