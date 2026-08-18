from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from jarvis.zhouyi import zhouyi_hexagram, zhouyi_line_semantic_profile  # noqa: E402


ONTOLOGY_PATH = ROOT / "knowledge" / "zhouyi_semantic_ontology.json"
FORBIDDEN_RESULT_KEYS = {
    "win_probability",
    "home_win_probability",
    "draw_probability",
    "away_win_probability",
    "predicted_score",
    "fixed_score",
    "final_result",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"Zhouyi semantic validation failed: {message}")


def _keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key)
            yield from _keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _keys(child)


def main() -> None:
    ontology = json.loads(ONTOLOGY_PATH.read_text(encoding="utf-8"))
    require(
        ontology.get("inference_status") == "PROJECT_HEURISTIC__NOT_CLASSICAL_COMMENTARY",
        "semantic ontology must be explicitly project heuristic",
    )
    markers = ontology.get("judgment_markers", [])
    atoms = ontology.get("atoms", [])
    require(len(markers) >= 7, "at least seven judgment marker families are required")
    require(len(atoms) >= 20, "Zhouyi semantic ontology is too shallow")
    require(len({row.get("id") for row in markers}) == len(markers), "judgment marker ids must be unique")
    require(len({row.get("id") for row in atoms}) == len(atoms), "semantic atom ids must be unique")

    for marker in markers:
        require(bool(marker.get("id")), "judgment marker missing id")
        require(bool(marker.get("terms")), f"judgment marker {marker.get('id')} missing terms")
        require(bool(marker.get("project_note")), f"judgment marker {marker.get('id')} missing project note")
    for atom in atoms:
        atom_id = atom.get("id")
        for field in ("name", "domain", "match_terms", "project_abstraction", "football", "observable_signals", "counter_signals"):
            require(bool(atom.get(field)), f"semantic atom {atom_id} missing {field}")

    total = 0
    semantic_hit = 0
    judgment_hit = 0
    any_hit = 0
    source_with_xiaoxiang = 0
    uncovered: list[str] = []
    for number in range(1, 65):
        hexagram = zhouyi_hexagram(number)
        for line in hexagram["lines"]:
            total += 1
            profile = zhouyi_line_semantic_profile(line)
            has_semantic = bool(profile["semantic_atoms"])
            has_judgment = bool(profile["judgment_markers"])
            if has_semantic:
                semantic_hit += 1
            if has_judgment:
                judgment_hit += 1
            if has_semantic or has_judgment:
                any_hit += 1
            else:
                uncovered.append(f"{number:02d} {hexagram['name']} {line['marker']}：{line['classical_text']}")
            if profile["text_basis"]["xiaoxiang_classical_text"]:
                source_with_xiaoxiang += 1
            require(
                profile["inference_status"] == "PROJECT_HEURISTIC__NOT_CLASSICAL_COMMENTARY",
                "line semantic profile authority boundary changed",
            )
            present_keys = set(_keys(profile))
            require(
                not (present_keys & FORBIDDEN_RESULT_KEYS),
                f"semantic profile contains forbidden automatic result fields: {sorted(present_keys & FORBIDDEN_RESULT_KEYS)}",
            )

    require(total == 384, f"semantic audit expected 384 lines, got {total}")
    # Coverage is a retrieval-quality gate, not a divination-accuracy metric. A line
    # can remain uncovered because ChatGPT still receives the original text, but a
    # mature ontology should structurally assist most lines.
    require(any_hit >= 300, f"semantic/judgment retrieval coverage too low: {any_hit}/384")
    print(
        "Zhouyi semantic audit passed: "
        f"{total} lines / {semantic_hit} semantic hits / {judgment_hit} judgment hits / "
        f"{any_hit} any-layer hits / {source_with_xiaoxiang} lines with mapped Xiaoxiang / "
        f"{len(uncovered)} raw-text-only lines"
    )
    if uncovered:
        print("raw-text-only examples:")
        for item in uncovered[:20]:
            print(f"- {item}")


if __name__ == "__main__":
    main()
