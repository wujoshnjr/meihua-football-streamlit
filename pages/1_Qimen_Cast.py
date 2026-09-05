from __future__ import annotations

import json
from datetime import date, datetime, time

import streamlit as st

from jarvis.workspace_state import activate_packet

from jarvis.divination_packet import build_qimen_packet
from jarvis.time import EventLocalTimeError, aware_event_local_datetime, inspect_local_civil_time


st.set_page_config(page_title="奇門起局 · JARVIS", page_icon="🧭", layout="wide")
st.title("🧭 奇門遁甲起局")
st.caption("JARVIS 只負責固定方法起局、深層盤象整理與知識檢索；最後解局交給 ChatGPT。足球若要處理同時開賽 collision，請優先使用「足球多層案件」。")

with st.form("qimen_stark_form"):
    question = st.text_area("占問問題", placeholder="例如：西班牙對維德角，這場比賽整體走勢如何？")
    category_label = st.selectbox("問題類型", ["足球比賽", "一般問題"])
    football = category_label == "足球比賽"
    home_team = away_team = ""
    if football:
        a, b = st.columns(2)
        with a:
            home_team = st.text_input("主隊")
        with b:
            away_team = st.text_input("客隊")

    c1, c2, c3 = st.columns(3)
    with c1:
        event_date = st.date_input("事件日期", value=date.today())
    with c2:
        event_time = st.time_input("事件時間", value=time(20, 0), step=1, format="24h")
    with c3:
        timezone_name = st.text_input("事件所在地 IANA 時區", value="Asia/Taipei")
    fold_mode = st.selectbox(
        "DST 重複時間",
        ["AUTO_REJECT_AMBIGUOUS", "FIRST_FOLD_0", "SECOND_FOLD_1"],
        help="一般時間維持 AUTO；DST 回撥造成同一 local time 出現兩次時必須明確選 fold。",
    )

    submitted = st.form_submit_button("起奇門局並建立 AI 解局包", type="primary", use_container_width=True)

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
                "此 local time 在 DST 回撥日出現兩次；請依官方 UTC offset 明確選 fold。"
            )
        fold = 1 if fold_mode == "SECOND_FOLD_1" else 0
        event_at = aware_event_local_datetime(wall, timezone_name.strip(), fold=fold)
        packet = build_qimen_packet(
            question=question,
            event_at=event_at,
            timezone_name=timezone_name.strip(),
            category="football_match" if football else "general",
            home_team=home_team,
            away_team=away_team,
        )
        activate_packet(st.session_state, packet)
        st.session_state["stark_packet_system"] = "QIMEN_DUNJIA"
    except (ValueError, EventLocalTimeError, RuntimeError) as exc:
        st.error(str(exc))

packet = st.session_state.get("stark_packet")
if packet and packet.get("system") == "QIMEN_DUNJIA":
    chart = packet["chart"]
    contexts = packet["knowledge_context"]
    st.success(f"起局完成｜{packet['schema_version']}｜Packet SHA-256：{packet['packet_sha256']}")
    a, b, c, d = st.columns(4)
    a.metric("遁", chart["dun"])
    b.metric("局", chart["ju_label"])
    c.metric("值符", chart["chief_star"])
    d.metric("值使", chart["chief_door"])

    st.markdown("### 九宮盤")
    layout = ((4, 9, 2), (3, 5, 7), (8, 1, 6))
    palaces = chart["palaces"]
    for row in layout:
        cols = st.columns(3)
        for col, number in zip(cols, row):
            state = palaces[str(number)]
            with col:
                with st.container(border=True):
                    flags = []
                    if state["is_void"]:
                        flags.append("旬空")
                    if state["is_horse"]:
                        flags.append("驛馬")
                    st.markdown(f"#### {state['name']} · {state['direction']}")
                    st.caption(" · ".join(flags) if flags else "—")
                    st.write(f"**門**：{state['door'] or '—'}")
                    st.write(f"**星**：{'、'.join(state['stars']) or '—'}")
                    st.write(f"**神**：{state['deity'] or '—'}")
                    st.write(f"**天盤**：{'、'.join(state['heaven_stems']) or '—'}")
                    st.write(f"**地盤**：{state['earth_stem']}")

    if packet.get("host_guest"):
        hg = packet["host_guest"]
        st.markdown("### 足球主客用神")
        x, y = st.columns(2)
        x.info(f"主隊 {hg['home_team']}｜日干 {hg['home_stem']}｜{hg['home_palace']} 宮")
        y.info(f"客隊 {hg['away_team']}｜時干 {hg['away_stem']}｜{hg['away_palace']} 宮")
        st.caption(hg["policy"])

    st.markdown("### 本局格局")
    if chart["patterns"]:
        st.dataframe(chart["patterns"], hide_index=True, use_container_width=True)
    else:
        st.info("本局未命中目前 catalog 中的特殊格局。")

    relation_context = [item for item in contexts if item.get("kind") == "qimen_relation"]
    st.markdown("### 本盤組合關係")
    st.caption(
        "Core 306 Matrix 覆蓋天地盤干、星門、門宮、星宮四類關係；這裡只顯示本盤實際命中的子集。"
        "足球欄位屬現代應用類比，不是古籍固定勝負公式。"
    )
    relation_rows = [
        {
            "宮": item["palace"],
            "類型": item["relation_label"],
            "組合": f"{item['first']} → {item['second']}",
            "五行": item["element_relation"],
            "一般解析": item["general_interpretation"],
            "足球衍生義": item["football_meaning"],
            "可觀察": "；".join(item["observable_signals"]),
            "反證": "；".join(item["counter_signals"]),
        }
        for item in relation_context
    ]
    if relation_rows:
        st.dataframe(relation_rows, hide_index=True, use_container_width=True)

    st.markdown("### 深層九宮合參")
    st.caption("每宮固定依『宮 → 門 → 星 → 神 → 天地盤干 → 格局／空馬』整理；八神附調制方式、足球證據與反證。")
    deep_palaces = [item for item in contexts if item.get("kind") == "qimen_palace_deep_profile"]
    deep_palaces.sort(key=lambda item: item["palace"])
    for item in deep_palaces:
        with st.expander(f"{item['palace_name']}｜深層盤象", expanded=False):
            st.write(item["reading_prompt"])
            stack = item["stack"]
            st.json(stack)
            deity = item.get("deity_detail")
            if deity:
                st.markdown(f"**八神調制：{stack['deity_modulation']}**")
                st.write(deity["general"])
                st.caption(deity["football"])
                st.write("可觀察：" + "；".join(deity["observable"]))
                st.write("反證：" + "；".join(deity["counter"]))
            if item["active_modifiers"]:
                st.markdown("**結構修飾**")
                for modifier in item["active_modifiers"]:
                    st.write(f"- {modifier['name']}：{modifier.get('general', '')}")
                    if modifier.get("football"):
                        st.caption(modifier["football"])
            st.markdown("**本宮解讀問題**")
            for question_item in item["football_questions"]:
                st.write(f"- {question_item}")

    st.markdown("### AI 解局包")
    st.write(f"JARVIS 已附上 {len(contexts)} 筆與本盤相關的基礎、Core 關係、八神調制、結構修飾與深層九宮知識。")
    packet_json = json.dumps(packet, ensure_ascii=False, indent=2)
    with st.expander(f"查看完整 {packet['schema_version']}"):
        st.code(packet_json, language="json")
    st.download_button(
        "下載 AI 解局包 JSON",
        data=packet_json,
        file_name=f"qimen-{packet['packet_sha256'][:12]}.json",
        mime="application/json",
        use_container_width=True,
    )
    st.page_link("pages/4_AI_Packet.py", label="前往 AI 解卦包頁", icon="🤖", use_container_width=True)
