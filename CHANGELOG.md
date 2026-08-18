# Changelog

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
