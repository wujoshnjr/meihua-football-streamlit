from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from qimen.constants import SOLAR_TERM_JU  # noqa: E402
from qimen.knowledge import KNOWLEDGE_FILES, load_knowledge  # noqa: E402


def require_unique(items, key, label):
    values = [item[key] for item in items]
    if len(values) != len(set(values)):
        raise AssertionError(f"{label} 有重複 {key}")


def main() -> int:
    data = load_knowledge()["files"]
    for filename in KNOWLEDGE_FILES:
        path = ROOT / "knowledge" / filename
        json.loads(path.read_text(encoding="utf-8"))
        if not data[filename]["schema_version"].startswith("qimen-"):
            raise AssertionError(f"{filename} 缺少 qimen schema 版本")

    entities = data["entities.json"]
    expected = {"palaces": 9, "doors": 8, "stars": 9, "deities": 8, "stems": 10}
    for section, count in expected.items():
        if len(entities[section]) != count:
            raise AssertionError(f"{section} 應有 {count} 筆")
        require_unique(entities[section], "key", section)

    calendar = data["calendar.json"]
    require_unique(calendar["solar_terms"], "name", "solar_terms")
    require_unique(calendar["earthly_branches"], "name", "earthly_branches")
    knowledge_ju = {item["name"]: tuple(item["ju"]) for item in calendar["solar_terms"]}
    if knowledge_ju != SOLAR_TERM_JU:
        raise AssertionError("calendar.json 十八局表與引擎常數不一致")

    sources = {item["id"] for item in data["sources.json"]["sources"]}
    patterns = data["patterns.json"]["patterns"]
    require_unique(patterns, "name", "patterns")
    for item in patterns:
        for field in ("category", "condition", "reading", "caution", "automation", "source_id"):
            if not item.get(field):
                raise AssertionError(f"格局 {item['name']} 缺少 {field}")
        if item["automation"] not in {"implemented", "knowledge_only"}:
            raise AssertionError(f"格局 {item['name']} automation 無效")
        if item["source_id"] not in sources:
            raise AssertionError(f"格局 {item['name']} 來源不存在")

    print(f"OK: {sum(len(v) for v in entities.values() if isinstance(v, list))} 個核心實體、{len(patterns)} 個格局、24 節氣。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
