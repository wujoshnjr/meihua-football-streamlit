from __future__ import annotations

import json
from datetime import date, datetime, time

import streamlit as st

from jarvis.time import (
    EventLocalTimeError,
    aware_event_local_datetime,
    inspect_local_civil_time,
)
from jarvis.yuanling_packet import build_yuanling_yanshu_packet


st.set_page_config(page_title="元靈經演數 · JARVIS", page_icon="🔢", layout="wide")
st.title("🔢 《元靈經》演數七要 / 日奇門")
st.caption(
    "兩個模組保持獨立：QIYAO_RAW 只整理演數七要；"
    "RIQIMEN_QIYAO_EXPERIMENT 才額外保存日奇門 base。"
    "目前不自動把數宮或數主轉成足球比分。"
)

st.warning(
    "原典已能確定七要項目、數主落宮的重要性、日奇門60日『某宮起休』表與部分排法；"
    "『遁至本時之星』與日奇門『穿宮數去』仍未完全 source-lock。"
    "相關奇門旁證現在只以候選 reconstruction 顯示，不會自動寫回原典七要欄。"
)

with st.form("yuanling_yanshu_form"):
    question = st.text_area(
        "問題",
        value=(
            "依《元靈經》演數七要整理此事件之數術原始資料；"
            "保留未決項，不直接換算足球比分。"
        ),
        height=90,
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
        )
    with c3:
        timezone_name = st.text_input("IANA timezone", value="Asia/Taipei")

    m1, m2 = st.columns(2)
    with m1:
        mode = st.selectbox(
            "模式",
            ["QIYAO_RAW", "RIQIMEN_QIYAO_EXPERIMENT"],
            help="實驗模式只串接並列保存日奇門 base，不宣稱古法明文要求此串接。",
        )
    with m2:
        fold_mode = st.selectbox(
            "DST 重複時間",
            ["AUTO_REJECT_AMBIGUOUS", "FIRST_FOLD_0", "SECOND_FOLD_1"],
        )

    with st.expander("研究輸入（只有在你已由原典/人工重建取得時才填）"):
        st.caption(
            "這些欄位不是 JARVIS 猜出來的；未提供就維持 "
            "UNRESOLVED_BY_SOURCE_AUDIT。"
        )
        options = ["未提供", 1, 2, 3, 4, 5, 6, 7, 8, 9]
        r1, r2, r3 = st.columns(3)
        with r1:
            number_palace = st.selectbox("數宮", options)
        with r2:
            chief_star = st.selectbox(
                "數主星號（一白=1…九紫=9）",
                options,
            )
        with r3:
            chief_palace = st.selectbox("數主落宮", options)

        r4, r5, r6 = st.columns(3)
        with r4:
            flying_star = st.text_input("飛星（原始研究值，選填）")
        with r5:
            entry_door = st.text_input("入門（原始研究值，選填）")
        with r6:
            daily_star = st.selectbox("直日星號", options)

    submitted = st.form_submit_button(
        "建立 YUANLING_YANSHU_PACKET_V1",
        type="primary",
        use_container_width=True,
    )

if submitted:
    try:
        wall = datetime.combine(event_date, event_time)
        audit = inspect_local_civil_time(wall, timezone_name.strip())
        if audit["nonexistent"]:
            raise EventLocalTimeError("此 local civil time 因 DST 跳時不存在，請修正。")
        if audit["ambiguous"] and fold_mode == "AUTO_REJECT_AMBIGUOUS":
            raise EventLocalTimeError(
                "此 local time 在 DST 回撥時出現兩次，請明確選 fold。"
            )
        fold = 1 if fold_mode == "SECOND_FOLD_1" else 0
        event_at = aware_event_local_datetime(
            wall,
            timezone_name.strip(),
            fold=fold,
        )

        packet = build_yuanling_yanshu_packet(
            question=question,
            event_at=event_at,
            timezone_name=timezone_name.strip(),
            mode=mode,
            number_palace=(
                None if number_palace == "未提供" else int(number_palace)
            ),
            number_chief_star_number=(
                None if chief_star == "未提供" else int(chief_star)
            ),
            number_chief_landing_palace=(
                None if chief_palace == "未提供" else int(chief_palace)
            ),
            flying_star=flying_star.strip() or None,
            entry_door=entry_door.strip() or None,
            daily_star_number=(
                None if daily_star == "未提供" else int(daily_star)
            ),
        )
        st.session_state["stark_yuanling_packet"] = packet
        st.success(
            "Yuanling packet 已建立；未解規則維持 unresolved，比分映射保持 disabled。"
        )
    except (ValueError, EventLocalTimeError, RuntimeError) as exc:
        st.error(str(exc))

packet = st.session_state.get("stark_yuanling_packet")
if packet:
    st.divider()
    qiyao = packet["qiyao_review"]
    st.markdown("## 演數七要 · Primary Review")
    rows = [
        {
            "七要": row["name"],
            "status": row["status"],
            "value": (
                json.dumps(row["value"], ensure_ascii=False)
                if row["value"] is not None
                else "—"
            ),
            "note": row["note"],
        }
        for row in qiyao["seven_factors"]
    ]
    st.dataframe(rows, hide_index=True, use_container_width=True)

    chief = qiyao.get("number_chief_landing_state")
    if chief:
        st.markdown("### 數主落宮")
        c1, c2, c3 = st.columns(3)
        c1.metric("數主", chief["star_name"])
        c2.metric("落宮", chief["landing_palace_name"])
        c3.metric("歌訣分類", chief["source_song_state"])
        st.caption(chief["explanation"])

    collateral = qiyao["collateral_reconstruction"]
    st.markdown("## 旁證 Reconstruction · 不寫回 Primary")
    p1, p2, p3 = st.columns(3)
    p1.metric(
        "候選數宮",
        collateral["number_palace_candidate"]["palace"],
    )
    p2.metric(
        "數宮上的日遁星候選",
        collateral["daily_star_at_number_palace_candidate"]["star_name"],
    )
    p3.metric(
        "中宮日遁星候選",
        collateral["center_daily_star_candidate"]["star_name"],
    )
    st.info(
        "這三項來自《奇門寶鑑》洞庭老人法與《金函玉鏡》日遁九星旁證。"
        "候選數宮仍不是球數；數宮上的星也尚不能自動等同『數主』。"
    )
    with st.expander("查看旁證九星盤 / source tier / non-equivalence rules"):
        st.json(collateral)

    with st.expander("元靈數術九星 registry（獨立於天蓬/天芮系）"):
        st.dataframe(
            qiyao["numeric_star_registry"]["stars"],
            hide_index=True,
            use_container_width=True,
        )

    if packet["riqimen_base"]:
        st.markdown("## 日奇門 Base（實驗串接）")
        base = packet["riqimen_base"]
        b1, b2, b3, b4 = st.columns(4)
        b1.metric("狀態", base["status"])
        b2.metric("局", base["calendar"]["ju_label"])
        b3.metric("日干支", base["calendar"]["day_ganzhi"])
        b4.metric(
            "起休宮",
            base["source_reconstructed"]["rest_door_start_palace"],
        )
        with st.expander("地盤與 unresolved steps"):
            st.json(base)

    st.markdown("## 邊界")
    st.info(qiyao["boundary"])
    st.caption(
        "raw numeric candidates = DISABLED_UNTIL_ALGORITHM_SOURCE_LOCK；"
        "score synthesis = deferred until blind-test protocol."
    )

    packet_json = json.dumps(packet, ensure_ascii=False, indent=2)
    st.download_button(
        "下載 YUANLING_YANSHU_PACKET_V1",
        data=packet_json,
        file_name="yuanling_yanshu_packet_v1.json",
        mime="application/json",
        use_container_width=True,
    )
