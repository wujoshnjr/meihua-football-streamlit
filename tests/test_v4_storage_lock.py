from __future__ import annotations

from pathlib import Path

from config import AppConfig
from meihua_engine import calculate_match_hexagram
from models import MatchInput
from score_engine import predict_scores
from storage_v33 import CaseStore, build_case_row


def make_match(body_rating: float = 68.0) -> MatchInput:
    return MatchInput(
        match_name="甲 vs 乙",
        body_team="甲",
        use_team="乙",
        body_text="甲方整體實力較完整並重視控制節奏。",
        use_text="乙方防守緊密並尋找快速反擊機會。",
        full_text="本場只判斷九十分鐘，雙方將以組織、防守與攻守轉換爭取優勢。",
        body_strength_rating=body_rating,
        use_strength_rating=54,
        prior_confidence=0.75,
        venue="中立場",
    )


def make_row(match: MatchInput) -> dict:
    result = calculate_match_hexagram(match)
    prediction = predict_scores(result, match)
    return build_case_row(
        match,
        result,
        prediction,
        None,
        [],
        actual_score="",
        calibration_reason="",
        calibration_summary="賽前鎖定",
        confirmed_ai_calibration=False,
        report_path="reports/test.md",
    )


def test_locked_postmatch_result_cannot_be_blanked_by_resave(tmp_path: Path) -> None:
    store = CaseStore(AppConfig(data_dir=tmp_path / "data", reports_dir=tmp_path / "reports"))
    original = make_row(make_match())
    saved, action = store.upsert(original)
    assert action == "新增鎖定案例"
    case_id = str(saved.iloc[0]["案例ID"])

    updated, _ = store.update_postmatch(
        case_id=case_id,
        actual_score="2-1",
        calibration_reason="人工確認",
        calibration_summary="方向正確",
        calibration_status="已確認",
        case_quality="高",
    )
    assert updated.iloc[0]["實際比分"] == "2-1"
    assert updated.iloc[0]["足球基線勝平負Brier"] != ""
    assert updated.iloc[0]["卦象調整勝平負Brier"] != ""
    assert updated.iloc[0]["卦象是否改善"] in {"改善", "惡化", "持平"}

    repeated, action = store.upsert(original)
    assert action == "確認既有鎖定版本"
    assert len(repeated) == 1
    assert repeated.iloc[0]["實際比分"] == "2-1"
    assert repeated.iloc[0]["校準狀態"] == "已確認"


def test_changed_prediction_becomes_linked_version(tmp_path: Path) -> None:
    store = CaseStore(AppConfig(data_dir=tmp_path / "data", reports_dir=tmp_path / "reports"))
    first, _ = store.upsert(make_row(make_match(68)))
    first_id = str(first.iloc[0]["案例ID"])

    second, action = store.upsert(make_row(make_match(74)))
    assert action == "新增預測版本"
    assert len(second) == 2
    assert str(second.iloc[1]["取代案例ID"]) == first_id
    assert int(second.iloc[1]["版本序號"]) == 2
    assert second.iloc[0]["預測內容雜湊"] != second.iloc[1]["預測內容雜湊"]
