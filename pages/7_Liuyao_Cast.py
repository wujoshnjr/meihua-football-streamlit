from __future__ import annotations

import json
from datetime import date, datetime, time

import streamlit as st

from jarvis.liuyao_packet import (
    LIUYAO_PACKET_VERSION,
    build_liuyao_packet,
    verify_liuyao_packet_integrity,
)
from jarvis.time import EventLocalTimeError, aware_event_local_datetime, inspect_local_civil_time


st.set_page_config(page_title="六爻納甲 · JARVIS", page_icon="☷", layout="wide")
st.title("☷ 六爻納甲 · 文王卦")
st.caption(
    "Source-aware 六爻子系統：先固定六次爻值，再排本／變卦、納甲、八宮、世應、六親、六神、旬空與日月動變；"
    "JARVIS 不在排卦階段偷選用神或自動判吉凶。"
)

st.info(
    "輸入順序固定為 **初爻 → 二爻 → … → 上爻**。"
    "JARVIS 直接接受 6/7/8/9，避免不同師承對硬幣『字／背／正反』命名不同造成換算錯誤："
    "6=老陰動、7=少陽靜、8=少陰靜、9=老陽動。"
)

CATEGORY_LABELS = {
    "GENERAL": "一般／尚未分類",
    "SELF": "本人／自身",
    "OTHER_PERSON": "對方／他人",
    "WEALTH": "財帛／貨物",
    "CAREER_OFFICE": "功名／官職／事業",
    "DOCUMENT_CONTRACT": "文書／契約／房舍舟車",
    "CHILDREN_MEDICINE_RELIEF": "子女／醫藥／解憂",
    "SIBLINGS_PEERS": "兄弟／同輩／朋友",
    "FOOTBALL_MATCH": "足球比賽（研究候選映射）",
}
VALUE_LABELS = {
    6: "6 · 老陰 ⚋ → ⚊",
    7: "7 · 少陽 ⚊",
    8: "8 · 少陰 ⚋",
    9: "9 · 老陽 ⚊ → ⚋",
}

with st.form("liuyao_cast"):
    question = st.text_area("占問內容", placeholder="請把問題一次說清楚；不要看結果後改題意。")
    category_label = st.selectbox("問題類別", list(CATEGORY_LABELS.values()))
    category = next(key for key, value in CATEGORY_LABELS.items() if value == category_label)

    c1, c2, c3 = st.columns(3)
    with c1:
        event_date = st.date_input("起卦日期", value=date.today())
    with c2:
        event_time = st.time_input("起卦時間", value=time(20, 0), step=1, format="24h")
    with c3:
        timezone_name = st.text_input("起卦所在地 IANA 時區", value="Asia/Taipei")

    fold_mode = st.selectbox(
        "DST 重複時間",
        ["AUTO_REJECT_AMBIGUOUS", "FIRST_FOLD_0", "SECOND_FOLD_1"],
        help="一般時間維持 AUTO；DST 回撥造成同一 local time 出現兩次時必須依實際 offset 選 fold。",
    )

    st.markdown("### 六次爻值")
    cols = st.columns(6)
    values: list[int] = []
    for index, col in enumerate(cols, start=1):
        with col:
            value = st.selectbox(
                f"{index}爻",
                options=list(VALUE_LABELS),
                format_func=lambda item: VALUE_LABELS[item],
                index=2,
                key=f"liuyao_line_{index}",
            )
            values.append(int(value))

    submitted = st.form_submit_button(
        f"建立 {LIUYAO_PACKET_VERSION}",
        type="primary",
        use_container_width=True,
    )

if submitted:
    try:
        wall = datetime.combine(event_date, event_time)
        audit = inspect_local_civil_time(wall, timezone_name.strip())
        if audit["nonexistent"]:
            raise EventLocalTimeError(
                f"{wall.isoformat()} 在 {timezone_name.strip()} 是 DST 跳時造成的不存在時間。"
            )
        if audit["ambiguous"] and fold_mode == "AUTO_REJECT_AMBIGUOUS":
            raise EventLocalTimeError(
                "此 local time 在 DST 回撥日出現兩次；請依實際 UTC offset 明確選 fold。"
            )
        fold = 1 if fold_mode == "SECOND_FOLD_1" else 0
        event_at = aware_event_local_datetime(wall, timezone_name.strip(), fold=fold)

        packet = build_liuyao_packet(
            question=question,
            line_values=values,
            event_at=event_at,
            timezone_name=timezone_name.strip(),
            question_category=category,
        )
        st.session_state["stark_packet"] = packet
        st.success(
            f"六爻 packet 已建立｜SHA {'PASS' if verify_liuyao_packet_integrity(packet) else 'FAIL'}"
        )
    except (ValueError, EventLocalTimeError, RuntimeError) as exc:
        st.error(str(exc))

packet = st.session_state.get("stark_packet")
if packet and packet.get("system") == "LIUYAO_WENWANGGUA":
    chart = packet["chart"]
    review = packet["review"]

    h1, h2, h3, h4, h5 = st.columns(5)
    h1.metric("本卦", chart["original_hexagram"])
    h2.metric("變卦", chart["changed_hexagram"])
    h3.metric("卦宮", f"{chart['palace']}宮 · {chart['palace_stage']}")
    h4.metric("世／應", f"{chart['shi_line']}／{chart['ying_line']}")
    h5.metric("動爻", "、".join(map(str, chart["moving_lines"])) or "無")

    st.caption(
        f"月建：{chart['month_ganzhi']}｜日辰：{chart['day_ganzhi']}｜"
        f"旬：{chart['day_xun']}｜空亡：{'、'.join(chart['void_branches'])}｜"
        f"六神初爻起：{chart['six_spirit_start']}"
    )

    st.markdown("### 六爻排盤")
    rows = []
    for line in reversed(chart["lines"]):
        flags = []
        if line["is_shi"]:
            flags.append("世")
        if line["is_ying"]:
            flags.append("應")
        if line["is_void"]:
            flags.append("空")
        if line["month_break"]:
            flags.append("月破")
        if line["day_clash"]:
            flags.append("日沖")
        rows.append(
            {
                "爻位": line["position"],
                "六神": line["six_spirit"],
                "六親": line["relative"],
                "納甲": f"{line['stem']}{line['branch']}{line['element']}",
                "陰陽": line["line_kind"],
                "動": "●" if line["moving"] else "",
                "世應/狀態": "、".join(flags),
                "月": line["month_relation"] or "—",
                "日": line["day_relation"] or "—",
                "變爻": (
                    f"{line['changed_relative']} {line['changed_stem']}{line['changed_branch']}"
                    if line["moving"]
                    else "—"
                ),
                "回頭": line["changed_relation_to_original"] or "—",
                "伏神候選": (
                    f"{line['hidden_relative']} {line['hidden_branch']}{line['hidden_element']}"
                    if line["hidden_relative"]
                    else "—"
                ),
            }
        )
    st.dataframe(rows, hide_index=True, use_container_width=True)

    role = review["question_role"]
    st.markdown("### 用神／題型入口")
    if role["primary_use"]:
        st.success(
            f"類別：{role['question_category']}｜primary：{role['primary_use']}｜"
            f"secondary：{'、'.join(role['secondary_uses']) or '—'}"
        )
    elif role["question_category"] == "FOOTBALL_MATCH":
        st.warning(
            "足球沒有已 source-lock 的唯一古法用神。JARVIS 只列候選："
            "L-F1 世 vs 應；L-F2 子孫 vs 官鬼。兩套必須同 cohort 平行測試，禁止逐場挑選。"
        )
    else:
        st.warning("此題型尚未自動映射用神；交給 ChatGPT 依原典規則與題意選擇，不硬猜。")
    for item in role["rationale"]:
        st.write(f"- {item}")

    with st.expander("用神／元神／忌神／仇神候選", expanded=True):
        st.json(review["use_god_review"])
    with st.expander("日月旺衰 direct relations", expanded=True):
        st.json(review["strength_review"])
    with st.expander("動變／伏神審查", expanded=True):
        st.json(review["motion_review"])
    with st.expander("來源／authority audit"):
        st.json(review["source_audit"])

    if review["contradiction_register"] or review["uncertainty_register"]:
        with st.expander("矛盾與不確定性", expanded=True):
            st.json(
                {
                    "contradictions": review["contradiction_register"],
                    "uncertainties": review["uncertainty_register"],
                }
            )

    st.markdown("### AI 交接硬規則")
    for rule in packet["ai_interpretation_contract"]:
        st.write(f"- {rule}")

    packet_json = json.dumps(packet, ensure_ascii=False, indent=2)
    a, b = st.columns(2)
    with a:
        st.download_button(
            f"下載 {packet['schema_version']}",
            packet_json,
            file_name=f"liuyao-{packet['packet_sha256'][:12]}.json",
            mime="application/json",
            use_container_width=True,
        )
    with b:
        st.page_link("pages/4_AI_Packet.py", label="交給 AI 解卦包", icon="🤖", use_container_width=True)

st.divider()
st.caption(
    "Source boundary：古典六爻 core 與後世／現代技巧分層。"
    "指定影片 -qgDHCHaDpo 目前搜尋端未取得字幕／逐字稿，因此尚未把任何未知說法寫入 core。"
)
