from __future__ import annotations

from input_protocol import build_input_protocol_audit, validate_input_protocol
from meihua_engine import count_symbols


def _pad_to(text: str, target: int) -> str:
    missing = target - count_symbols(text)
    assert missing >= 0
    return text + "穩" * missing


def self_narrative(name: str, target: int = 180) -> str:
    return _pad_to(
        f"我是{name}。"
        "目前我的整體狀態穩定。"
        "我的士氣專注。"
        "我的比賽策略是控制節奏。"
        "我主要依靠整體合作。"
        "我的進攻方式是持續施壓。"
        "我的防守方式是保持距離。"
        "我最大的優勢是行動一致。"
        "我最需要注意快速反擊。"
        "我希望在九十分鐘內掌握主動。",
        target,
    )


def neutral_introduction(body: str, use: str, target: int = 300) -> str:
    return _pad_to(
        f"這場比賽由{body}對陣{use}，判斷範圍為九十分鐘。"
        f"{body}希望主動控制節奏並持續施壓，{use}則準備穩定防守並尋找轉換空間。"
        "比賽關鍵在於雙方能否維持陣形、限制對手的推進並把握實際破門機會。",
        target,
    )


def test_v2_protocol_accepts_fixed_voice_structure_and_count_ranges() -> None:
    body = self_narrative("巴西", 180)
    use = self_narrative("日本", 220)
    neutral = neutral_introduction("巴西", "日本", 450)

    assert validate_input_protocol("巴西", "日本", body, use, neutral) == []
    audit = build_input_protocol_audit("巴西", "日本", body, use, neutral)
    assert audit["version"] == "team-self-narrative-v2"
    assert audit["sections"]["body"]["actual_count"] == 180
    assert audit["sections"]["use"]["actual_count"] == 220
    assert audit["sections"]["neutral"]["actual_count"] == 450


def test_v2_protocol_rejects_short_or_incomplete_first_person_text() -> None:
    issues = validate_input_protocol(
        "巴西",
        "日本",
        "巴西目前狀態很好。",
        self_narrative("日本"),
        neutral_introduction("巴西", "日本"),
    )

    assert any("體方自述（起象）目前為" in issue for issue in issues)
    assert any("必須以「我是巴西。」開始" in issue for issue in issues)
    assert any("缺少固定結構" in issue for issue in issues)


def test_v2_protocol_requires_third_person_neutral_text_and_both_names() -> None:
    neutral = _pad_to("我是旁觀者。這場比賽只介紹巴西。", 300)
    issues = validate_input_protocol(
        "巴西",
        "日本",
        self_narrative("巴西"),
        self_narrative("日本"),
        neutral,
    )

    assert any("必須使用第三人稱" in issue for issue in issues)
    assert any("必須同時提到雙方名稱：日本" in issue for issue in issues)
