from __future__ import annotations

import json
from datetime import date, datetime, time

import streamlit as st

from jarvis.case_bundle import build_divination_case_bundle, verify_bundle_integrity
from jarvis.divination_packet import build_meihua_packet, build_qimen_packet
from jarvis.time import EventLocalTimeError, aware_event_local_datetime, inspect_local_civil_time


st.set_page_config(page_title="足球雙術數案件 · JARVIS", page_icon="⚽", layout="wide")
st.title("⚽ 足球雙術數案件")
st.caption(
    "同一個事件時間一次建立奇門 RESULT_ENGINE_INPUT + 梅花 STRUCTURE_STRESS_TEST，"
    "先做 same-event alignment，再下載 DIVINATION_CASE_BUNDLE_V1 交給 ChatGPT。"
)

cast_tab, import_tab = st.tabs(["同時起局／起卦", "匯入既有 Packets"])

with cast_tab:
    with st.form("football_case_form"):
        a, b = st.columns(2)
        with a:
            home_team = st.text_input("主隊")
        with b:
            away_team = st.text_input("客隊")

        qimen_question = st.text_area(
            "🧭 奇門問題 · RESULT ENGINE",
            value=(
                "這場足球比賽在正規時間90分鐘及傷停補時結束後，最終勝負為主勝、和局或客勝？"
                "依完整奇門盤局判斷最可能的首選比分與一個備選比分，並列出支持與反證。"
            ),
            height=110,
        )
        meihua_question = st.text_area(
            "☯️ 梅花問題 · STRUCTURE / STRESS TEST",
            value=(
                "分析這場足球比賽從開局、中段到終局的發展結構，重點讀體用旺衰、體互／用互、變卦、"
                "動爻、周易 supporting review、焦氏易林與時間交界；指出支持與反證，不另行輸出第二套勝負或精確比分。"
            ),
            height=120,
        )

        m1, m2, m3 = st.columns(3)
        with m1:
            competition = st.text_input("賽事名稱（選填）")
        with m2:
            stage = st.text_input("比賽階段（選填）")
        with m3:
            mode = st.selectbox("案件模式", ["PREMATCH", "LIVE", "HISTORICAL_BACKTEST"])

        v1, v2, v3, v4 = st.columns(4)
        with v1:
            stadium = st.text_input("球場（選填）")
        with v2:
            city = st.text_input("城市（選填）")
        with v3:
            country = st.text_input("國家（選填）")
        with v4:
            kickoff_basis = st.selectbox(
                "起局時間基準",
                ["SCHEDULED_KICKOFF", "REVISED_KICKOFF", "VERIFIED_ACTUAL_KICKOFF"],
            )

        c1, c2, c3 = st.columns(3)
        with c1:
            event_date = st.date_input("事件所在地日期", value=date.today())
        with c2:
            event_time = st.time_input(
                "事件所在地時間",
                value=time(20, 0),
                step=1,
                format="24h",
                help="JARVIS 10.2 使用秒級 local civil time；足球官方資料只有分鐘時可把秒留 00。",
            )
        with c3:
            timezone_name = st.text_input("IANA timezone", value="Asia/Taipei")

        t1, t2, t3, t4 = st.columns(4)
        with t1:
            horizon = st.selectbox("梅花時間審查窗", [120, 150, 180, 210], index=2)
        with t2:
            fold_mode = st.selectbox(
                "DST 重複時間",
                ["AUTO_REJECT_AMBIGUOUS", "FIRST_FOLD_0", "SECOND_FOLD_1"],
                help="一般時間維持 AUTO；只有 DST 回撥造成同一 local time 出現兩次時才需明確選 fold。",
            )
        with t3:
            verification_status = st.selectbox(
                "時間驗證狀態",
                ["OFFICIAL_SCHEDULE_VERIFIED", "ACTUAL_KICKOFF_VERIFIED", "USER_PROVIDED", "NOT_VERIFIED"],
            )
        with t4:
            time_source = st.text_input("時間來源（選填）", placeholder="FIFA / UEFA / 官方聯賽…")

        match_clock_events_text = st.text_area(
            "LIVE 專用：timestamped match-clock events JSON（選填）",
            value="",
            height=130,
            placeholder=(
                '[{"type":"ACTUAL_KICKOFF","local_datetime":"2026-06-15T22:50:00+08:00","source":"official"},'
                '{"type":"FIRST_HALF_END","local_datetime":"2026-06-15T23:40:00+08:00","match_clock_label":"HT"},'
                '{"type":"SECOND_HALF_KICKOFF","local_datetime":"2026-06-15T23:55:00+08:00"}]'
            ),
            help=(
                "只接受可追溯的 aware local timestamps。PREMATCH / HISTORICAL_BACKTEST 預設禁止填入，"
                "避免把事後比賽資訊回填進原始占測。"
            ),
        )

        submitted = st.form_submit_button("建立奇門＋梅花 Case Bundle", type="primary", use_container_width=True)

    if submitted:
        try:
            wall = datetime.combine(event_date, event_time)
            audit = inspect_local_civil_time(wall, timezone_name.strip())
            if audit["nonexistent"]:
                raise EventLocalTimeError(
                    f"{wall.isoformat()} 在 {timezone_name.strip()} 是 DST 跳時造成的不存在時間，請修正事件時間。"
                )
            if audit["ambiguous"] and fold_mode == "AUTO_REJECT_AMBIGUOUS":
                raise EventLocalTimeError(
                    "此 local time 在 DST 回撥日出現兩次。請依官方 UTC offset 選 FIRST_FOLD_0 或 SECOND_FOLD_1。"
                )
            fold = 1 if fold_mode == "SECOND_FOLD_1" else 0
            event_at = aware_event_local_datetime(wall, timezone_name.strip(), fold=fold)

            match_clock_events = None
            if match_clock_events_text.strip():
                if mode != "LIVE":
                    raise ValueError("timestamped match-clock events 目前只允許 LIVE 模式，避免 PREMATCH／歷史盲測後見回填。")
                match_clock_events = json.loads(match_clock_events_text)
                if not isinstance(match_clock_events, list):
                    raise ValueError("match-clock JSON 必須是 event objects 的 array")

            qimen_packet = build_qimen_packet(
                question=qimen_question,
                event_at=event_at,
                timezone_name=timezone_name.strip(),
                category="football_match",
                home_team=home_team,
                away_team=away_team,
            )
            meihua_packet = build_meihua_packet(
                question=meihua_question,
                event_at=event_at,
                timezone_name=timezone_name.strip(),
                category="football_match",
                home_team=home_team,
                away_team=away_team,
                timeline_horizon_minutes=int(horizon),
                match_clock_events=match_clock_events,
            )
            metadata = {
                "competition": competition,
                "stage": stage,
                "stadium": stadium,
                "city": city,
                "country": country,
                "kickoff_basis": kickoff_basis,
                "time_verification_status": verification_status,
                "time_source": time_source,
                "mode": mode,
            }
            bundle = build_divination_case_bundle(qimen_packet, meihua_packet, event_metadata=metadata)
            st.session_state["stark_qimen_packet"] = qimen_packet
            st.session_state["stark_meihua_packet"] = meihua_packet
            st.session_state["stark_case_bundle"] = bundle
            st.session_state["stark_packet"] = meihua_packet
            st.success("雙術數案件建立完成：event alignment + packet SHA integrity = PASS")
        except (ValueError, EventLocalTimeError, RuntimeError, json.JSONDecodeError) as exc:
            st.error(str(exc))

with import_tab:
    st.write("可重新匯入先前下載的兩份 `DIVINATION_PACKET_V2`；JARVIS 會先驗 SHA，再做 same-event alignment。")
    q_upload = st.file_uploader("Qimen packet JSON", type=["json"], key="qimen_import")
    m_upload = st.file_uploader("Meihua packet JSON", type=["json"], key="meihua_import")
    if st.button("驗證並建立 Case Bundle", use_container_width=True):
        if not q_upload or not m_upload:
            st.error("請同時提供 Qimen 與 Meihua packet。")
        else:
            try:
                qimen_packet = json.loads(q_upload.getvalue().decode("utf-8"))
                meihua_packet = json.loads(m_upload.getvalue().decode("utf-8"))
                bundle = build_divination_case_bundle(qimen_packet, meihua_packet)
                st.session_state["stark_qimen_packet"] = qimen_packet
                st.session_state["stark_meihua_packet"] = meihua_packet
                st.session_state["stark_case_bundle"] = bundle
                st.success("匯入成功：packet integrity + same-event alignment = PASS")
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
                st.error(str(exc))

bundle = st.session_state.get("stark_case_bundle")
if bundle:
    st.divider()
    st.markdown("## Case Bundle 狀態")
    event = bundle["match_event"]
    metadata = bundle.get("event_metadata") or {}
    qimen_packet = bundle["qimen_packet"]
    meihua_packet = bundle["meihua_packet"]
    integrity = verify_bundle_integrity(bundle)

    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Alignment", bundle["alignment_audit"]["status"])
    s2.metric("Bundle SHA", "PASS" if integrity["status"] == "PASS" else "FAIL")
    s3.metric("Qimen Role", bundle["interpretation_roles"]["qimen"]["role"])
    s4.metric("Meihua Role", bundle["interpretation_roles"]["meihua"]["role"])

    st.info(
        f"{event['home_team']} vs {event['away_team']}｜{event['event_datetime']}｜{event['timezone']}｜"
        f"match_event {event['match_event_sha256'][:12]}…"
    )
    if metadata:
        st.caption("｜".join(f"{key}={value}" for key, value in metadata.items()))

    with st.expander("Same-event alignment / SHA audit", expanded=True):
        st.json(bundle["alignment_audit"])

    temporal = meihua_packet.get("temporal_precision_audit") or {}
    if temporal:
        st.markdown("## ⏱️ 梅花時間邊界 Timeline")
        summary = temporal.get("boundary_summary", {})
        match_clock_audit = temporal.get("match_clock_audit", {})
        x1, x2, x3, x4, x5 = st.columns(5)
        x1.metric("審查窗", f"{temporal.get('analysis_window', {}).get('horizon_minutes', '—')} min")
        x2.metric("時支變化", summary.get("hour_branch_changes", 0))
        x3.metric("日期變化", summary.get("calendar_changes", 0))
        x4.metric("UTC offset 變化", summary.get("utc_offset_changes", 0))
        x5.metric("Match Clock", match_clock_audit.get("status", "—"))

        rows = []
        for boundary in temporal.get("boundaries", []):
            diagnostic = boundary.get("diagnostic_recast") or {}
            alignment = boundary.get("match_clock_alignment") or {}
            hint = boundary.get("football_phase_hint") or {}
            rows.append(
                {
                    "local timestamp": boundary.get("local_datetime"),
                    "elapsed wall min": boundary.get("elapsed_real_minutes_from_kickoff"),
                    "boundary": " / ".join(boundary.get("boundary_types", [])),
                    "from hour": (boundary.get("from") or {}).get("hour_branch"),
                    "to hour": (boundary.get("to") or {}).get("hour_branch"),
                    "verified phase": alignment.get("phase"),
                    "nominal hint": hint.get("phase"),
                    "diagnostic changed": diagnostic.get("changed_field_count", 0),
                }
            )
        if rows:
            st.dataframe(rows, hide_index=True, use_container_width=True)
        else:
            st.success("目前審查窗內沒有偵測到時支／日界／UTC offset 邊界。")
        if match_clock_audit.get("events"):
            with st.expander("查看 timestamped match-clock evidence"):
                st.json(match_clock_audit)
        st.caption(
            "wall-clock 不等於官方 match minute；timestamped events 只用於定位實際賽事階段，"
            "不做線性分鐘猜測；diagnostic recast 永遠是 SECONDARY_DIAGNOSTIC_ONLY。"
        )

    method_audit = meihua_packet.get("meihua_method_audit") or {}
    time_convention = method_audit.get("time_convention") or {}
    if time_convention:
        with st.expander("梅花時間慣例 audit"):
            st.json(time_convention)

    moving = (meihua_packet.get("zhouyi_review") or {}).get("moving_line") or {}
    meaning_review = moving.get("meaning_review") or {}
    if meaning_review:
        st.markdown("## 📜 動爻 Conditional Meaning Review")
        r1, r2, r3 = st.columns(3)
        r1.metric("動爻", moving.get("marker", "—"))
        r2.metric("條件傾向", meaning_review["conditional_outcome_tendency"]["status"])
        r3.metric("Authority", meaning_review["authority"])
        st.write(moving.get("classical_text", ""))
        st.caption(meaning_review["conditional_outcome_tendency"]["note"])
        with st.expander("條件、風險、誤讀警告與足球 evidence/counter-evidence"):
            st.json(meaning_review)

    st.markdown("## 下載")
    bundle_json = json.dumps(bundle, ensure_ascii=False, indent=2)
    qimen_json = json.dumps(qimen_packet, ensure_ascii=False, indent=2)
    meihua_json = json.dumps(meihua_packet, ensure_ascii=False, indent=2)
    d1, d2, d3 = st.columns(3)
    with d1:
        st.download_button(
            "下載 Case Bundle",
            bundle_json,
            file_name=f"case-{bundle['bundle_sha256'][:12]}.json",
            mime="application/json",
            use_container_width=True,
        )
    with d2:
        st.download_button(
            "下載 Qimen Packet",
            qimen_json,
            file_name=f"qimen-{qimen_packet['packet_sha256'][:12]}.json",
            mime="application/json",
            use_container_width=True,
        )
    with d3:
        st.download_button(
            "下載 Meihua Packet",
            meihua_json,
            file_name=f"meihua-{meihua_packet['packet_sha256'][:12]}.json",
            mime="application/json",
            use_container_width=True,
        )

    st.markdown("## 給 ChatGPT 的角色契約")
    st.code(
        "奇門 = RESULT_ENGINE_INPUT：主判正規時間勝負＋有限比分候選。\n"
        "梅花 = STRUCTURE_STRESS_TEST：只分析開局／中段／終局、轉折、支持與反證，不另報第二套比分。\n"
        "ChatGPT = FINAL_SYNTHESIS：先驗 alignment / SHA，不重起局、不重起卦、不修改事件時間。",
        language=None,
    )
