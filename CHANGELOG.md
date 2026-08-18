# Changelog

## 10.0.0 — JARVIS 10 YILIN FUSION

JARVIS 10 completes the local 《焦氏易林》 transformation matrix while preserving the Operation STARK boundary: **JARVIS casts and retrieves; ChatGPT interprets**.

### Complete Yilin base corpus

- Expand from the alpha 64/4096 block to **4096/4096 unique pairs**: 64 source hexagrams × 64 target hexagrams.
- Materialize all **64/64 source blocks** from a pinned WYG / 文淵閣四庫全書 digital transcription in `kanripo/KR3g0029` at commit `764e995ce74aa249081918ca1b0c23bbca62bec8`.
- Preserve exact source provenance: source volume, section, page locator, raw transcription, editorial parenthetical notes, gaiji tokens, upstream repository and pinned commit.
- Add source-file SHA-256 hashes and `knowledge/yilin/source_snapshot.json` so the corpus can be audited and reproduced.
- Never use AI to create, complete or silently rewrite missing classical text.

### Textual integrity

- Runtime lookup is keyed by canonical King Wen numeric pairs, preventing glyph variants such as 无/無, 恒/恆, 兊/兌 and 㢲/巽 from breaking the bridge.
- Reconstruct each source block using the documented 易林 order: the block's own hexagram first, followed by the remaining King Wen hexagrams.
- Preserve one detected WYG source-target label anomaly instead of silently correcting it: 艮 block target position #9 is transcribed as `小過`; JARVIS keeps that source label and records the anomaly while the canonical lookup remains `艮之小畜`.
- Add `knowledge/yilin/collation_status.json` to distinguish **pair-matrix completeness** from still-ongoing multi-edition variant collation, modern punctuation and commentary work.

### Deep semantic layer

- Expand the Yilin image ontology to dozens of explicit semantic atoms spanning movement, crossing, vehicles, obstruction, timing, access, defense, conflict, discipline, deception, communication, cooperation, isolation, authority, resources, gain/loss, supply, growth, fitness, recovery, reversal, collapse, ascent, weather, visibility, psychology and collective structure.
- Every atom retains `PROJECT_HEURISTIC__NOT_CLASSICAL_COMMENTARY` authority and includes football hypotheses, observable evidence and counter-evidence.
- Add `yilin_semantic_profile()` to aggregate matched domains, football hypotheses, support signals and counter-signals for the single active forest verse.
- Add `yilin_semantic_audit()` to expose heuristic retrieval coverage without presenting it as textual completeness or predictive accuracy.

### Runtime and AI handoff

- Harden `MEIHUA_YILIN_BRIDGE` so Meihua remains the authority for original/mutual/changed hexagrams, moving line, body/use and strength.
- Consult exactly one Yilin pair: **original hexagram → final changed hexagram**.
- Include classical text, source apparatus, provenance, semantic profile and compatibility image atoms in `DIVINATION_PACKET_V1`.
- AI instructions explicitly separate: digital transcription → source apparatus → sourced commentary → project heuristic → football modern application → ChatGPT final synthesis.
- Keep the historical-method notice: this bridge is a project cross-system synthesis, not a claim that it reproduces Jiaolin day-assignment practice.

### UI

- Home page now reports complete 4096/4096 Yilin pair coverage and clearly states the textual-collation boundary.
- Meihua page exposes the active `本卦之變卦`, forest verse, edition, volume/page, raw transcription, notes, gaiji warnings, anomaly warnings, semantic domains, football support and counter-evidence.
- Knowledge Vault searches the complete 4096 corpus and the expanded image ontology.
- AI Packet page gives ChatGPT the exact Meihua → Yilin → evidence/counter-evidence interpretation order.

### Validation and reproducibility

- `tools/import_yilin_kanripo.py` deterministically reproduces the complete corpus from the pinned upstream source.
- `tools/validate_yilin.py` rejects anything other than an exact 64×64 matrix with complete required provenance and consistent snapshot/hash metadata.
- Tests cover first/middle/last source blocks, forward/reverse lookups, orthographic normalization, semantic profiles, search and packet-level full coverage.
- No Yilin content is converted directly into a probability, fixed score or automatic match result.

**Completeness statement:** JARVIS 10 is complete at the 4096-pair / WYG-base-transcription layer. Multi-edition textual variants, editorial punctuation and historical commentary remain explicitly separate ongoing scholarly layers.

## 10.0.0-alpha.1 — JARVIS 10 YILIN FUSION

Operation STARK begins the staged integration of the full 《焦氏易林》 64×64 transformation corpus.

### Yilin catalog

- Add `knowledge/yilin/manifest.json` with a hard target of **4096/4096** unique `from_hexagram → to_hexagram` records.
- Materialize the first complete 64-entry source block: 《易林（四庫全書本）》卷一「乾之第一」.
- The catalog is explicitly marked `PARTIAL_BUILD__DO_NOT_CLAIM_4096_COMPLETE`; missing pairs are never fabricated.
- Every materialized record keeps classical text, source provenance, verification status, pending variant status and semantic-status boundaries.

### Meihua bridge

- Add `jarvis/yilin.py` and `MEIHUA_YILIN_BRIDGE`.
- Meihua still determines the original, mutual and changed hexagrams, moving line, body/use and strength.
- Yilin is consulted only as **original hexagram → final changed hexagram** transformation context.
- Mutual hexagrams are not silently reinterpreted as a historical Yilin method.
- Missing source pairs return `SOURCE_PENDING` with no generated classical text.

### Image ontology and football semantics

- Add an initial Yilin image ontology for path/movement, obstruction, conflict, injury/fatigue, gain/support, loss/failure, cooperation, communication, environment, authority, recovery and defensive enclosure.
- Image matching is explicitly labeled `PROJECT_HEURISTIC__NOT_CLASSICAL_COMMENTARY`.
- Football mappings remain modern application hypotheses with observable evidence and counter-evidence, never classical quotations or automatic probabilities.

### UI and AI packet

- The Meihua page now displays the Yilin transformation lookup, source text when materialized, project image atoms, coverage and method boundary.
- The knowledge vault now searches Yilin materialized entries and image ontology alongside Qimen and Meihua.
- `DIVINATION_PACKET_V1` gains an additive `yilin_bridge` field while preserving the existing deterministic packet contract.
- ChatGPT is instructed to read: Meihua core → Yilin transformation context → modern application → support/counter-evidence → final synthesis.

### Validation

- Add `tests/test_yilin_fusion.py`.
- Add `tools/validate_yilin.py` and run it in GitHub Actions.
- Alpha validation requires each materialized source hexagram to be imported as a complete 64-target block and manifest coverage to match the files exactly.

## 9.1.0 — Operation STARK Deep Reading

JARVIS keeps the same responsibility boundary — **cast + retrieve + package** — but the divination packet now carries materially deeper structured knowledge for ChatGPT to interpret.

### Qimen Dunjia

- Add an 8-layer reading hierarchy: palace → door → star → deity → heaven stem → earth stem → structural pattern → void/horse modifiers.
- Add deep modulation profiles for all 8 deities, each with general meaning, football modern-application meaning, observable evidence and counter-evidence.
- Add explicit deep state modifiers for void, horse, Fu Yin, Fan Yin, door/palace pressure, tomb and punishment.
- Every cast now receives 9 `qimen_palace_deep_profile` records that synthesize the actual stack and active 306-matrix relations in that palace.
- The Qimen page exposes the deep palace profiles instead of limiting the UI to raw symbols and relation rows.

### Meihua Yishu

- Add explicit roles for original / mutual / changed hexagrams.
- Add upper/lower trigram internal-external reading roles and their five-element interaction.
- Expand all 5 body/use relations with strength-sensitive general meaning, football application, observables and counter-evidence.
- Add deep 旺 / 平 / 衰 rules and detailed phase meanings for all 6 moving-line positions.
- Every cast now receives one `meihua_deep_profile` containing original/mutual/changed stage structures, body/use, strength, moving line and 8 football reading dimensions.
- The Meihua page now shows these deeper layers directly before packet download.

### Knowledge vault and AI handoff

- Add `knowledge/qimen_deep_layers.json` and `knowledge/meihua_deep_layers.json`.
- Deep-layer content is searchable from the knowledge vault.
- AI packet instructions now explicitly tell ChatGPT which deep reading order to use for Qimen and Meihua.
- Football meanings remain labeled modern application; no symbol is converted into an automatic probability, fixed score or deterministic match result.

## 9.0.0 — Operation STARK

JARVIS product scope has been reset around divination knowledge and AI handoff.

### Product

- Keep only: JARVIS home, Qimen casting, Meihua casting, knowledge vault, AI packet.
- Remove Dashboard, Research Lab, Football Live Predictor and the former model-governance product UI.
- JARVIS responsibility is now fixed as **cast + retrieve + package**; final interpretation belongs to ChatGPT.

### Qimen Dunjia

- Retain the deterministic Shijia / rotating-plate / Chaibu engine.
- Retain structured palaces, doors, stars, deities, stems, patterns, interpretation protocol and football ontology.
- Football semantics remain observable/counter-observable modern application hypotheses, never classical quotations or automatic probabilities.

### Meihua Yishu

- Retain the deterministic year-month-day-hour engine.
- Add all eight trigrams with element/direction/core/football semantics.
- Add all 64 King-Wen-order hexagrams with upper/lower trigram, theme, structured interpretation summary and football application meaning.
- Add all five body/use relations and six moving-line position roles.
- Original, mutual and changed hexagrams are retrieved automatically for each cast.

### AI handoff

- Add `DIVINATION_PACKET_V1` and JSON Schema.
- Packets contain immutable question/event/method/chart facts plus only relevant knowledge context.
- Packet SHA-256 is deterministic for the same event and method.
- The contract explicitly forbids the AI from recasting or silently changing the chart.

### Repository cleanup

- Remove Football ML / M0–M3 / Poisson / xG / StatsBomb ingestion / training / calibration / promotion infrastructure.
- Remove the former research artifacts, schemas, docs and tests associated with those systems.
- Runtime dependencies are reduced to Streamlit and lunar-python.

### Knowledge validation

- CI checks exact core coverage: Qimen 9 palaces / 8 doors / 9 stars / 8 deities / 10 stems; Meihua 8 trigrams / 64 hexagrams / 5 body-use relations / 6 moving-line roles.
- All 64 upper/lower trigram combinations must exist exactly once.
- Every football mapping must retain observable and counter-signal fields.
