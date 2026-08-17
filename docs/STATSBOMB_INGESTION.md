# StatsBomb Open Data ingestion

Status: RESEARCH DATA PROVIDER.

`jarvis.data.statsbomb` normalizes one StatsBomb match JSON plus its event JSON into a 90-minute historical row suitable for the existing JARVIS football feature builder.

## Inputs

- one match object from `data/matches/{competition_id}/{season_id}.json`;
- the corresponding event array from `data/events/{match_id}.json`;
- an explicit IANA event timezone;
- an explicit `available_at` timestamp representing when the historical information is allowed to enter a later prematch cutoff.

The provider deliberately does not infer `available_at` from StatsBomb's current repository `last_updated`, because repository publication time and historical football-information availability are different concepts. Dataset builders must register their availability policy explicitly.

## 90-minute target rule

For matches whose event stream contains only periods 1 and 2, the match metadata score is accepted as the normal-time result.

If any event has period > 2, the provider refuses to guess whether the metadata score includes extra time or shootout progression. The dataset builder must provide `normal_time_score_override=(home, away)` from a registered 90-minute source.

StatsBomb xG is summed only from `Shot` events in periods 1 and 2. Extra-time and shootout events never enter normal-time xG.

## Provenance

The provider hashes the complete match payload, event payload and any explicit score override into `source_payload_sha256`. The resulting row can be converted to `qimen.features.HistoricalMatch`, preserving `available_at`, goals and xG.

## Upstream source

StatsBomb Open Data publishes competition/season match files plus per-match events, lineups and selected 360 data for public research. Published work using the upstream data must follow StatsBomb's attribution and user-agreement requirements. This repository does not vendor or redistribute the upstream match/event datasets.
