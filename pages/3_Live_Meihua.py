from __future__ import annotations

from datetime import date, datetime, time, timedelta

import pandas as pd
import streamlit as st

from jarvis.live_meihua import (
    DEPLOYED_MEIHUA_ARTIFACT_PATH,
    LIVE_MEIHUA_VERSION,
    build_live_meihua_forecast,
    load_deployed_live_meihua_artifact,
)
from jarvis.release import runtime_release_status
from meihua import MEIHUA_ENGINE_VERSION, MEIHUA_OUTCOME_DESIGN_VERSION
from qimen.calendar import LocalTimeError, aware_local_datetime
from qimen.engine import cast_qimen
from qimen.football import interpret_football
from qimen.prediction import PrematchModelInput, TeamForm, build_prediction


release = runtime_release_status()

st.set_page_config(page_title="JARVIS Live Predictor", page_icon="🎯", layout="wide")
st.title("JARVIS Live Predictor")
st.caption(
    f"Web App v{release.web_app_version}｜Football base v{release.live_predictor_code_version}｜"
    f"Meihua live bridge {LIVE_MEIHUA_VERSION}"
)

try:
    deployed_artifact = load_deployed_live_meihua_artifact()
except ValueError as exc:
    st.error(f"部署中的梅花 artifact 驗證失敗：{exc}")
    st.stop()

meihua_probability_status = (
    "ACTIVE · M2 promoted"
    if deployed_artifact is not None and deployed_artifact.shrinkage_alpha > 1e-15
    else "BASELINE FALLBACK"
    if deployed_artifact is not None
    else "ADVISORY · awaiting artifact"
)

m1, m2, m3, m4 = st.columns(4)
m1.metric("JARVIS", f"v{release.web_app_version}")
m2.metric("Football base", f"v{release.live_predictor_code_version}")
m3.metric("梅花引擎", MEIHUA_ENGINE_VERSION.rsplit("-v", 1)[-1])
m4.metric("梅花機率層", meihua_probability_status)

st.success(
    "梅花易數現在是 Live Predictor 的正式運算層：每場都會依事件所在地時間建立卦象、"
    "轉成固定 schema features 並建立 SHA-256 指紋。",
    icon="☯️",
)
if deployed_artifact is None:
    st.warning(
        "目前 repository 還沒有通過 TRAIN → VALIDATION → CALIBRATION → TEST_UNTOUCHED → human review "
        "的 M2 deployment artifact，因此梅花不會被允許任意改寫主勝／和局／客勝機率。"
        "這不是沒有接入；而是 production gate 正在阻止未驗證權重進入正式機率。",
        icon="🛡️",
    )
else:
    st.info(
        f"已載入 {deployed_artifact.artifact_source}；"
        f"alpha={deployed_artifact.shrinkage_alpha:.3f}，promotion={deployed_artifact.promotion_status}。"
    )

st.markdown("### 賽事與盤前 Football 輸入")
with st.form("live_meihua_form"):
    a, b, c = st.columns(3)
    with a:
        match_id = st.text_input("Match ID", value="LIVE-DEMO-001")
        home_team = st.text_input("主隊", value="主隊")
        away_team = st.text_input("客隊", value="客隊")
        competition = st.text_input("賽事", value="賽前研究")
    with b:
        event_date = st.date_input("開賽日期", value=date.today() + timedelta(days=1))
        event_time = st.time_input("開賽時間", value=time(20, 0), step=300)
        timezone_name = st.text_input("事件所在地 IANA 時區", value="Asia/Taipei")
        st.caption("梅花起卦固定使用事件所在地民用時間；同一 event/timezone 必須重現同一卦。")
    with c:
        league_home_mean = st.number_input("聯盟主場場均進球", 0.10, 5.00, 1.50, 0.05)
        league_away_mean = st.number_input("聯盟客場場均進球", 0.10, 5.00, 1.20, 0.05)
        prior_matches = st.number_input("先驗等效場次", 0.0, 30.0, 5.0, 1.0)
        xg_weight = st.number_input("xG 權重", 0.0, 1.0, 0.65, 0.05)
        st.caption("正式 base score model：Independent Poisson frozen champion。")

    home_col, away_col = st.columns(2)
    team_payload: dict[str, dict[str, float | int | None]] = {}
    for column, prefix, label, default_for, default_against in (
        (home_col, "home", "主隊 Football snapshot", 1.50, 1.20),
        (away_col, "away", "客隊 Football snapshot", 1.20, 1.50),
    ):
        with column:
            st.markdown(f"#### {label}")
            matches = st.number_input("盤前樣本場次", 0, 100, 10, 1, key=f"{prefix}_matches")
            goals_for = st.number_input("場均進球", 0.0, 8.0, default_for, 0.05, key=f"{prefix}_gf")
            goals_against = st.number_input("場均失球", 0.0, 8.0, default_against, 0.05, key=f"{prefix}_ga")
            use_xg = st.checkbox("提供 xG / xGA", key=f"{prefix}_use_xg")
            xg_for = xg_against = None
            if use_xg:
                x1, x2 = st.columns(2)
                with x1:
                    xg_for = st.number_input("場均 xG", 0.0, 8.0, default_for, 0.05, key=f"{prefix}_xg")
                with x2:
                    xg_against = st.number_input("場均 xGA", 0.0, 8.0, default_against, 0.05, key=f"{prefix}_xga")
            team_payload[prefix] = {
                "matches": int(matches),
                "goals_for_per_match": float(goals_for),
                "goals_against_per_match": float(goals_against),
                "xg_for_per_match": None if xg_for is None else float(xg_for),
                "xg_against_per_match": None if xg_against is None else float(xg_against),
            }

    confirmed = st.checkbox("我確認 Football 數據都是開賽前已知資料")
    submitted = st.form_submit_button("建立 Football + 梅花 Live 預測", type="primary", use_container_width=True)

if submitted:
    try:
        if not match_id.strip() or not home_team.strip() or not away_team.strip() or not competition.strip():
            raise ValueError("Match ID、主隊、客隊與賽事不可空白")
        if home_team.strip() == away_team.strip():
            raise ValueError("主客隊不可相同")
        event_at = aware_local_datetime(
            datetime.combine(event_date, event_time),
            timezone_name.strip(),
        )
        generated_at = datetime.now(tz=event_at.tzinfo)
        board = cast_qimen(event_at, timezone_name.strip())
        reading = interpret_football(board)
        model_input = PrematchModelInput(
            home=TeamForm(**team_payload["home"]),
            away=TeamForm(**team_payload["away"]),
            league_home_goals_per_match=float(league_home_mean),
            league_away_goals_per_match=float(league_away_mean),
            prior_match_equivalent=float(prior_matches),
            xg_weight=float(xg_weight),
            data_as_of=generated_at,
            data_source="JARVIS live manual prematch input",
            score_model="INDEPENDENT_POISSON",
            forecast_horizon="EARLY",
            lineup_status="UNAVAILABLE",
        )
        base_prediction = build_prediction(model_input, board, reading)
        live_forecast = build_live_meihua_forecast(
            base_prediction,
            event_at=event_at,
            timezone_name=timezone_name.strip(),
            artifact=deployed_artifact,
        )
        st.session_state.live_meihua_event = {
            "match_id": match_id.strip(),
            "home_team": home_team.strip(),
            "away_team": away_team.strip(),
            "competition": competition.strip(),
            "event_at": event_at,
            "generated_at": generated_at,
            "confirmed": confirmed,
        }
        st.session_state.live_meihua_base_prediction = base_prediction
        st.session_state.live_meihua_forecast = live_forecast
    except (ValueError, LocalTimeError, RuntimeError) as exc:
        st.error(str(exc))

if "live_meihua_forecast" in st.session_state:
    event = st.session_state.live_meihua_event
    base = st.session_state.live_meihua_base_prediction
    forecast = st.session_state.live_meihua_forecast
    snapshot = forecast.meihua_snapshot

    st.divider()
    st.markdown(f"### {event['home_team']} vs {event['away_team']}")
    st.caption(
        f"{event['competition']}｜{event['event_at'].isoformat()}｜"
        f"forecast {forecast.forecast_sha256}"
    )

    if forecast.active_probability_adjustment:
        st.success("M2_MEIHUA promoted artifact 已正式改動本場 λ 與 1X2。", icon="✅")
    elif forecast.mode == "PROMOTED_M2_BASELINE_FALLBACK":
        st.info("M2 已通過部署治理，但 VALIDATION 選出的 alpha=0；本場依法精確退回 Football baseline。")
    else:
        st.warning("梅花卦象已正式計算與記錄；目前沒有 promoted M2 artifact，所以數值機率保持 Football baseline。")

    p1, p2, p3, p4 = st.columns(4)
    p1.metric("主勝", f"{forecast.home_win_probability:.1%}")
    p2.metric("和局", f"{forecast.draw_probability:.1%}")
    p3.metric("客勝", f"{forecast.away_win_probability:.1%}")
    p4.metric("首選", forecast.predicted_result)

    l1, l2, l3 = st.columns(3)
    l1.metric(
        "主隊 xG λ",
        f"{forecast.expected_home_goals:.2f}",
        delta=f"{forecast.expected_home_goals - forecast.baseline_expected_home_goals:+.2f}" if forecast.active_probability_adjustment else None,
    )
    l2.metric(
        "客隊 xG λ",
        f"{forecast.expected_away_goals:.2f}",
        delta=f"{forecast.expected_away_goals - forecast.baseline_expected_away_goals:+.2f}" if forecast.active_probability_adjustment else None,
    )
    l3.metric("Meihua mode", forecast.mode)

    st.dataframe(
        pd.DataFrame(
            [
                {
                    "排名": index,
                    "比分": f"{item.home_goals}–{item.away_goals}",
                    "機率": item.probability,
                }
                for index, item in enumerate(forecast.top_scorelines, 1)
            ]
        ),
        hide_index=True,
        use_container_width=True,
    )

    st.markdown("### 梅花易數 Live snapshot")
    q1, q2, q3, q4 = st.columns(4)
    q1.metric("本卦", f"{snapshot.upper_trigram} / {snapshot.lower_trigram}")
    q2.metric("動爻", f"第 {snapshot.moving_line} 爻")
    q3.metric("體 / 用", f"{snapshot.body_trigram} / {snapshot.use_trigram}")
    q4.metric("體用關係", snapshot.body_use_relation)

    left, right = st.columns(2)
    with left:
        with st.container(border=True):
            st.markdown("#### 互卦與變卦")
            st.write(f"互卦：{snapshot.mutual_upper_trigram} / {snapshot.mutual_lower_trigram}")
            st.write(f"變卦：{snapshot.changed_upper_trigram} / {snapshot.changed_lower_trigram}")
            st.write(f"變用：{snapshot.changed_use_trigram}｜{snapshot.changed_use_relation_to_body}")
    with right:
        with st.container(border=True):
            st.markdown("#### 可重現性")
            st.write(f"Feature schema：`{MEIHUA_OUTCOME_DESIGN_VERSION}`")
            st.write(f"Feature SHA-256：`{forecast.meihua_feature_sha256}`")
            st.write(f"Probability adjustment：**{'ON' if forecast.active_probability_adjustment else 'OFF'}**")
            st.write(f"Artifact：`{forecast.artifact_source or 'NONE'}`")

    with st.expander("梅花 raw features / audit payload"):
        st.json(
            {
                "event": {
                    **event,
                    "event_at": event["event_at"].isoformat(),
                    "generated_at": event["generated_at"].isoformat(),
                },
                "base_model_version": base.model_version,
                "live_meihua": forecast.to_dict(),
            }
        )

    if event["generated_at"] >= event["event_at"]:
        st.warning("本次建立時間已不早於開賽，僅可作回溯探索，不得列入 prospective 命中率。")
    elif not event["confirmed"]:
        st.warning("尚未確認盤前資料聲明；本次輸出不可列入正式 prospective evaluation。")
    else:
        st.info("本頁已保留盤前時間與 forecast SHA；完整來源證據鎖與報告匯出請使用 Audit Workbench。")

st.divider()
st.caption(
    f"部署 artifact 路徑：{DEPLOYED_MEIHUA_ARTIFACT_PATH}。"
    "梅花易數屬傳統術數；未經 untouched evidence 不宣稱能提高足球預測準確率。"
)
