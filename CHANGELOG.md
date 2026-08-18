# Changelog

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
