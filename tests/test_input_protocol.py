from __future__ import annotations

from input_protocol import build_input_protocol_audit, validate_input_protocol
from meihua_engine import count_symbols


def _pad_to(text: str, target: int) -> str:
    missing = target - count_symbols(text)
    assert missing >= 0
    return text + "穩" * missing


def self_narrative(name: str, target: int = 180) -> str:
    return _pad_to(
        "\n".join(
            (
                f"我是{name}。",
                "目前我的客觀狀態為略正面，陣容完整。",
                "我的士氣與比賽壓力為中性，壓力明確。",
                "我的預計比賽策略是主動控球。",
                "我主要依靠的組織支點是後腰出球。",
                "我的主要進攻通道是右路推進。",
                "我的主要防守結構是中位四後衛。",
                "我最大的相對優勢是邊路速度。",
                "我目前最明顯的限制是終結不穩。",
                "我最需要防範對手的是快速反擊。",
                "我希望在九十分鐘內減少失誤提高射門品質。",
            )
        ),
        target,
    )


def neutral_introduction(body: str, use: str, target: int = 300) -> str:
    return _pad_to(
        f"這場比賽由{body}對陣{use}，判斷範圍為九十分鐘。"
        f"{body}希望主動控制節奏並持續施壓，{use}則準備穩定防守並尋找轉換空間。"
        "比賽關鍵在於雙方能否維持陣形、限制對手的推進並把握實際破門機會。",
        target,
    )


def test_v3_protocol_accepts_fixed_voice_structure_and_count_ranges() -> None:
    body = self_narrative("巴西", 180)
    use = self_narrative("日本", 220)
    neutral = neutral_introduction("巴西", "日本", 450)

    assert validate_input_protocol("巴西", "日本", body, use, neutral) == []
    audit = build_input_protocol_audit("巴西", "日本", body, use, neutral)
    assert audit["version"] == "team-self-narrative-v3"
    assert audit["sections"]["body"]["actual_count"] == 180
    assert audit["sections"]["use"]["actual_count"] == 220
    assert audit["sections"]["neutral"]["actual_count"] == 450
    assert audit["sections"]["body"]["actual_non_empty_lines"] == 11
    assert audit["sections"]["body"]["line_order_valid"] is True
    assert audit["sections"]["body"]["empty_fields"] == []
    assert "略正面" in audit["controlled_vocabulary"]["狀態評級"]
    assert "三段原文" in audit["versioning_policy"]


def test_v3_protocol_rejects_short_or_incomplete_first_person_text() -> None:
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


def test_v3_protocol_requires_third_person_neutral_text_and_both_names() -> None:
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


def test_v3_protocol_requires_exact_line_order_and_separate_limit_field() -> None:
    body = self_narrative("巴西")
    lines = body.splitlines()
    lines[8], lines[9] = lines[9], lines[8]
    issues = validate_input_protocol(
        "巴西",
        "日本",
        "\n".join(lines),
        self_narrative("日本"),
        neutral_introduction("巴西", "日本"),
    )

    assert any("行序或固定開頭不正確" in issue for issue in issues)


def test_v3_protocol_rejects_result_language_and_post_match_information() -> None:
    body = self_narrative("巴西").replace("減少失誤", "希望取勝")
    neutral = neutral_introduction("巴西", "日本").replace("比賽關鍵", "賽後統計顯示")
    issues = validate_input_protocol(
        "巴西",
        "日本",
        body,
        self_narrative("日本"),
        neutral,
    )

    assert any("結果導向或情緒化詞語：希望取勝" in issue for issue in issues)
    assert any("疑似賽後資訊：賽後" in issue for issue in issues)


def test_v3_protocol_warns_about_generic_content_without_blocking_casting() -> None:
    body = _pad_to(
        self_narrative("巴西").replace("為中性，壓力明確", "保持專注"),
        180,
    )
    audit = build_input_protocol_audit(
        "巴西",
        "日本",
        body,
        self_narrative("日本"),
        neutral_introduction("巴西", "日本"),
    )

    assert audit["sections"]["body"]["quality_warnings"] == [
        "士氣與比賽壓力只使用泛用詞，建議改成可核對且能區分本場的訊號。"
    ]
    assert validate_input_protocol(
        "巴西",
        "日本",
        body,
        self_narrative("日本"),
        neutral_introduction("巴西", "日本"),
    ) == []
