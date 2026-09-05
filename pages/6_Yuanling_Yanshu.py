from __future__ import annotations

import json
from datetime import date, datetime, time

import streamlit as st

from jarvis.workspace_state import activate_packet

from jarvis.time import (
    EventLocalTimeError,
    aware_event_local_datetime,
    inspect_local_civil_time,
)
from jarvis.yuanling_packet import (
    YUANLING_PACKET_VERSION,
    build_yuanling_yanshu_packet,
    verify_yuanling_packet_integrity,
)
from jarvis.yuanling_vault import (
    casting_method,
    football_question_templates,
    yuanling_catalog_stats,
)


st.set_page_config(page_title="元靈經演數 · JARVIS", page_icon="🔢", layout="wide")
st.title("🔢 《元靈經》演數七要 / 日奇門")
st.caption(
    "兩個模組保持獨立：QIYAO_RAW 只整理演數七要；"
    "RIQIMEN_QIYAO_EXPERIMENT 才在 packet layer 另外保存日奇門 sibling。"
    "目前不自動把數宮、值日星或射覆數目轉成足球比分。"
)

stats = yuanling_catalog_stats()
qiyao_method = casting_method("YUANLING_YANSHU_QIYAO_RAW")
riqimen_method = casting_method("YUANLING_RI_QIMEN")
question_templates = football_question_templates()

with st.expander("📖 目前起法、資料庫內容與完成度", expanded=True):
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("原典結構化條目", stats["structured_sections"])
    m2.metric("數術九星", stats["numeric_stars"])
    m3.metric("日奇門60日表", stats["riqimen_day_rows"])
    m4.metric("保留未決點", stats["unresolved_source_points"])

    st.markdown("**演數七要 QIYAO_RAW**")
    st.write("必要輸入：" + "、".join(qiyao_method["required_inputs"]))
    for index, step in enumerate(qiyao_method["casting_steps"], 1):
        st.write(f"{index}. {step}")
    st.caption(qiyao_method["boundary"])

    st.markdown("**日奇門 Source-grounded Base**")
    for index, step in enumerate(riqimen_method["casting_steps"], 1):
        st.write(f"{index}. {step}")
    st.caption(riqimen_method["boundary"])

st.warning(
    "七要的數主／飛星／直日星角色關係已完成 crosschecked reconstruction；"
    "日奇門『穿宮』也已鎖定為九宮數序順飛、穿中五。"
    "仍保留的研究缺口是：數宮完整原典取法、入門完整演數步驟、"
    "以及《元靈經》本節缺少一個完整 end-to-end worked example。"
    "旁證值仍不會靜默覆寫 raw primary slots。"
)

with st.form("yuanling_yanshu_form"):
    question = st.text_area(
        "問題",
        value=question_templates["yuanling"],
        height=110,
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
            help=(
                "實驗模式只在 packet 最上層並列保存日奇門 sibling；"
                "Qiyao review 本身不嵌入日奇門，也不宣稱古法明文要求此串接。"
            ),
        )
    with m2:
        fold_mode = st.selectbox(
            "DST 重複時間",
            ["AUTO_REJECT_AMBIGUOUS", "FIRST_FOLD_0", "SECOND_FOLD_1"],
        )

    with st.expander("研究輸入（只有在你已由原典/人工重建取得時才填）"):
        st.caption(
            "這些欄位不是 JARVIS 猜出來的；未提供就維持 "
            "UNRESOLVED_BY_SOURCE_AUDIT。旁證候選不會偷偷寫進這些欄位。"
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
        f"建立 {YUANLING_PACKET_VERSION}",
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
        activate_packet(st.session_state, packet)
        st.success(
            "Yuanling packet 已建立；七要與日奇門保持 sibling separation，"
            "原典知識 context 已一併打包，比分映射保持 disabled。"
        )
    except (ValueError, EventLocalTimeError, RuntimeError) as exc:
        st.error(str(exc))

packet = st.session_state.get("stark_yuanling_packet")
if packet:
    st.divider()
    qiyao = packet["qiyao_review"]
    integrity = verify_yuanling_packet_integrity(packet)

    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Packet", packet["schema_version"])
    s2.metric("SHA integrity", "PASS" if integrity else "FAIL")
    s3.metric("Mode", packet["mode"])
    s4.metric("Ri-Qimen bridge", qiyao["riqimen_bridge"]["status"])

    if not integrity:
        st.error("Packet SHA integrity 驗證失敗；請勿將此 packet 交給下游解讀。")

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
        "角色關係已分開：數主＝數宮本位數術星並追蹤其落宮；"
        "飛星＝當日日遁盤臨到數宮之星；直日星＝中五當日占星。"
        "但候選數宮仍不是球數，旁證值也不自動升格為 raw primary fact。"
    )
    with st.expander("查看數主 / 飛星 / 直日星角色重建", expanded=True):
        st.json(qiyao["star_role_resolution"])
    with st.expander("查看旁證九星盤 / source tier / non-equivalence rules"):
        st.json(collateral)

    with st.expander("元靈數術九星 registry（獨立於天蓬/天芮系）"):
        st.dataframe(
            qiyao["numeric_star_registry"]["stars"],
            hide_index=True,
            use_container_width=True,
        )

    if packet["riqimen_base"]:
        st.markdown("## 日奇門 Base · Packet-layer Sibling")
        base = packet["riqimen_base"]
        b1, b2, b3, b4 = st.columns(4)
        b1.metric("狀態", base["status"])
        b2.metric("局", base["calendar"]["ju_label"])
        b3.metric("日干支", base["calendar"]["day_ganzhi"])
        b4.metric(
            "起休宮",
            base["source_reconstructed"]["rest_door_start_palace"],
        )
        st.caption(
            "此物件與 qiyao_review 平級保存；Qiyao review 不再重複嵌入第二份 Ri-Qimen。"
        )
        with st.expander("地盤與 unresolved steps"):
            st.json(base)

    st.markdown("## 原典知識 Context")
    context = packet["knowledge_context"]
    kc1, kc2, kc3 = st.columns(3)
    kc1.metric("方法", context["method"]["display_name"])
    kc2.metric("來源條目", len(context["source_sections"]))
    kc3.metric("資料庫", context["source_catalog_schema"])
    with st.expander("查看起法、原典條目、值日九星與射覆數目關聯"):
        st.json(context)
    st.caption(
        "射覆數目關聯只作古典數術資料；禁止直接換成足球總進球。"
    )

    st.markdown("## 邊界")
    st.info(qiyao["boundary"])
    st.caption(
        "raw numeric candidates = DISABLED_UNTIL_ALGORITHM_SOURCE_LOCK；"
        "score synthesis = deferred until blind-test protocol."
    )

    packet_json = json.dumps(packet, ensure_ascii=False, indent=2)
    version_slug = packet["schema_version"].lower()
    st.download_button(
        f"下載 {packet['schema_version']}",
        data=packet_json,
        file_name=f"{version_slug}.json",
        mime="application/json",
        disabled=not integrity,
        use_container_width=True,
    )
