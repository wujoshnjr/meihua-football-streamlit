# Changelog

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
- Current alpha validation requires each materialized source hexagram to be imported as a complete 64-target block and requires manifest coverage to match the files exactly.

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
