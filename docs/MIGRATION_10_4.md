# JARVIS 10.4 Migration Guide

This note covers artifact migration after JARVIS 10.4.

## DIVINATION_PACKET_V1 → DIVINATION_PACKET_V2

`schemas/divination-packet.schema.json` is retained only as a deprecated compatibility schema.

New casts must use `DIVINATION_PACKET_V2`. Football packets may additionally contain:
- `event_identity_layer`
- `participant_layer` on Qimen packets

Do not manufacture these fields when importing a historical V1 packet. If the original prematch identity inputs were not preserved, leave the differentiation layer absent rather than reconstructing it from post-match knowledge.

## DIVINATION_CASE_BUNDLE_V1 → DIVINATION_CASE_BUNDLE_V2

V1 contained Qimen + Meihua only. V2 adds:
- optional Yuanling V1.3 temporal sibling;
- `differentiation_audit`;
- optional canonical fixture identity;
- optional coach participant layer;
- stronger SHA / temporal alignment contracts.

There is intentionally no automatic V1→V2 upgrade that invents event identity. The safe migration path is:

1. verify the legacy packets;
2. retain the original event datetime, timezone and home/away orientation;
3. rebuild V2 only when the original prematch fixture identity inputs are known;
4. otherwise keep the case explicitly temporal-only.

## Yuanling packet migration

Current packet contract: `YUANLING_YANSHU_PACKET_V1_3`.

Older Yuanling artifacts must not be relabeled by editing `schema_version`. Rebuild from the original event inputs and any contemporaneously recorded research values. Collateral reconstruction must remain collateral and must not be copied into raw primary slots merely to satisfy a newer schema.

## Collision audit

Use `FOOTBALL_COLLISION_GROUP_AUDIT_V1` for a kickoff cohort. It accepts only SHA-valid `DIVINATION_CASE_BUNDLE_V2` artifacts.

A temporal collision without canonical event identity is a REVIEW condition, not evidence that the fixtures can be differentiated from the shared temporal layer.

## Non-backfill rule

Migration must never use:
- final score;
- goals/cards/substitutions learned after the cast;
- post-match coach or fixture corrections that were unavailable prematch;
- a later interpretation chosen because the result is known.

Migration is format recovery, not model retuning.
