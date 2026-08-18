from __future__ import annotations

import json
from datetime import date, datetime, time

import streamlit as st

from jarvis.divination_packet import build_meihua_packet
from qimen.calendar import LocalTimeError, aware_local_datetime


st.set_page_config(page_title="梅花起卦 · JARVIS", page_icon="☯️", layout="wide")
st.title("☯️ 梅花易數起卦")
st.caption(
    "年月日時 deterministic 起卦；JARVIS 整理本卦、互卦、變卦、體用、旺衰、動爻，"
    "再加入《焦氏易林》本卦→變卦完整轉卦鏡頭，最後交給 ChatGPT 合參。"
)

with st.form("meihua_stark_form"):
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
        event_time = st.time_input("事件時間", value=time(20, 0), step=300)
    with c3:
        timezone_name = st.text_input("事件所在地 IANA 時區", value="Asia/Taipei")

    submitted = st.form_submit_button("起梅花卦並建立 AI 解卦包", type="primary", use_container_width=True)

if submitted:
    try:
        event_at = aware_local_datetime(datetime.combine(event_date, event_time), timezone_name.strip())
        packet = build_meihua_packet(
            question=question,
            event_at=event_at,
            timezone_name=timezone_name.strip(),
            category="football_match" if football else "general",
            home_team=home_team,
            away_team=away_team,
        )
        st.session_state["stark_packet"] = packet
        st.session_state["stark_packet_system"] = "MEIHUA_YISHU"
    except (ValueError, LocalTimeError, RuntimeError) as exc:
        st.error(str(exc))

packet = st.session_state.get("stark_packet")
if packet and packet.get("system") == "MEIHUA_YISHU":
    hx = packet["hexagram"]
    contexts = packet["knowledge_context"]
    original = next(row for row in contexts if row.get("kind") == "meihua_original_hexagram")
    mutual = next(row for row in contexts if row.get("kind") == "meihua_mutual_hexagram")
    changed = next(row for row in contexts if row.get("kind") == "meihua_changed_hexagram")
    deep = next(row for row in contexts if row.get("kind") == "meihua_deep_profile")
    yilin = packet["yilin_bridge"]

    st.success(f"起卦完成｜Packet SHA-256：{packet['packet_sha256']}")
    a, b, c = st.columns(3)
    with a:
        st.metric("本卦", f"{original['symbol']} {original['name']}")
        st.caption(f"{hx['upper_trigram']}上 {hx['lower_trigram']}下｜{original['theme']}")
    with b:
        st.metric("互卦", f"{mutual['symbol']} {mutual['name']}")
        st.caption(f"{hx['mutual_upper_trigram']}上 {hx['mutual_lower_trigram']}下｜{mutual['theme']}")
    with c:
        st.metric("變卦", f"{changed['symbol']} {changed['name']}")
        st.caption(f"{hx['changed_upper_trigram']}上 {hx['changed_lower_trigram']}下｜{changed['theme']}")

    st.markdown("### 體用與動爻")
    q1, q2, q3, q4 = st.columns(4)
    q1.metric("動爻", f"第 {hx['moving_line']} 爻")
    q2.metric("體卦", hx["body_trigram"])
    q3.metric("用卦", hx["use_trigram"])
    q4.metric("體用關係", hx["body_use_relation"])
    st.info(f"體卦旺衰：{hx['body_season_state']}｜變用關係：{hx['changed_use_relation_to_body']}")

    st.markdown("### 三層卦義與足球衍生義")
    rows = []
    for label, row in (("本卦", original), ("互卦", mutual), ("變卦", changed)):
        rows.append(
            {
                "層次": label,
                "卦": row["name"],
                "主題": row["theme"],
                "一般解析": row["summary"],
                "足球衍生義": row["football"],
            }
        )
    st.dataframe(rows, hide_index=True, use_container_width=True)
    st.caption("足球衍生義屬 modern application，不是《周易》或《梅花易數》古籍原文。")

    st.markdown("### 深層卦象結構")
    for label, key in (
        ("本卦 · 目前結構", "original"),
        ("互卦 · 中段機制", "mutual"),
        ("變卦 · 後段走向", "changed"),
    ):
        stage = deep[key]
        relation = stage["upper_lower_element_relation"]
        with st.expander(label, expanded=(key == "original")):
            st.write(stage["stage_role"]["general"])
            st.caption(stage["stage_role"]["football"])
            x, y = st.columns(2)
            with x:
                trigram = stage["lower_role"]["trigram"]
                st.markdown(f"**下卦／內部**：{trigram['name']} · {trigram.get('core', '')}")
                st.write(stage["lower_role"]["general"])
            with y:
                trigram = stage["upper_role"]["trigram"]
                st.markdown(f"**上卦／外部**：{trigram['name']} · {trigram.get('core', '')}")
                st.write(stage["upper_role"]["general"])
            st.markdown(f"**上下卦五行關係**：{relation['lower_element']} → {relation['upper_element']}")
            st.write(relation["interpretation"])

    st.markdown("### 體用、旺衰與動爻深讀")
    body_use = deep["body_use"]
    mline = deep["moving_line"]
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.markdown(f"**{body_use['body']}體 × {body_use['use']}用｜{body_use['relation']}**")
            st.write(body_use["relation_detail"]["general"])
            st.caption(body_use["relation_detail"]["football"])
            st.write(f"**體卦旺衰：{body_use['body_season_state']}** — {body_use['strength_detail']['general']}")
            st.caption(body_use["strength_detail"]["football"])
    with col2:
        with st.container(border=True):
            st.markdown(f"**第 {mline['line']} 爻｜{mline['phase']}**")
            st.write(mline["general"])
            st.caption(mline["football"])

    st.markdown("### 《焦氏易林》本卦 → 變卦")
    ys = yilin["catalog_stats"]
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("易林轉卦", f"{ys['materialized_pairs']} / {ys['expected_pairs']}")
    m2.metric("本卦 blocks", f"{ys['materialized_from_hexagrams']} / 64")
    m3.metric("意象原子", ys["ontology_atoms"])
    m4.metric("來源異常登錄", ys["source_label_anomaly_count"])
    st.caption(
        "WYG／文淵閣四庫全書數位轉錄已達 4096/4096 pair coverage。"
        "多版本異文與後世注解仍是獨立校勘層，不把『pair 完整』誇大成『所有版本研究已完成』。"
    )

    if yilin["status"] != "MATERIALIZED":
        st.error(f"完整 catalog 不應缺此 pair：{yilin['lookup_key']}｜{yilin.get('missing_reason', '')}")
    else:
        entry = yilin["classical_entry"]
        provenance = yilin["provenance"]
        st.success(f"已命中：{yilin['lookup_key']}｜{provenance['source_section']}")
        st.markdown("#### 林辭原文")
        st.write(entry["classical_text"])
        st.caption(
            f"來源：{provenance['edition']}｜{provenance['volume_file']}｜{provenance['page_start']}｜"
            f"pinned commit {str(provenance['commit'])[:12]}…"
        )

        if provenance.get("source_label_order_anomaly"):
            st.warning(
                f"此條來源轉錄卦名標籤為「{provenance.get('source_target_label')}」，"
                "與該位置的文王卦序不一致；JARVIS 保留原標籤並登錄 anomaly，沒有靜默改寫來源。"
            )
        if provenance.get("gaiji_tokens"):
            st.warning("此條含尚未擅自猜字的 gaiji token：" + "、".join(provenance["gaiji_tokens"]))

        with st.expander("查看原轉錄、校語與來源細節"):
            st.write(f"**原轉錄**：{entry['transcription_raw']}")
            st.write("**校語／括注**：" + ("；".join(provenance.get("editorial_notes", [])) or "—"))
            st.write(f"**source target label**：{provenance.get('source_target_label') or '—'}")
            st.write(f"**source id**：{provenance['source_id']}")
            st.write(f"**repository / commit**：{provenance['repository']} @ {provenance['commit']}")

        profile = yilin.get("semantic_profile") or {}
        atoms = profile.get("image_atoms", [])
        st.markdown("#### 易林情境語義")
        st.caption("以下是 Operation STARK 的檢索 heuristic，不是《焦氏易林》原註。先讀林辭，再看候選意象。")
        if atoms:
            st.dataframe(
                [
                    {
                        "領域": row["domain"],
                        "意象": row["name"],
                        "命中字詞": "、".join(row["matched_terms"]),
                        "抽象義": row["classical_abstraction"],
                        "足球可能情境": "；".join(row["football"]),
                    }
                    for row in atoms
                ],
                hide_index=True,
                use_container_width=True,
            )
            if football:
                s1, s2 = st.columns(2)
                with s1:
                    st.markdown("**足球支持訊號**")
                    for item in profile.get("observable_signals", []):
                        st.write(f"- {item}")
                with s2:
                    st.markdown("**足球反證訊號**")
                    for item in profile.get("counter_signals", []):
                        st.write(f"- {item}")
        else:
            st.info("此林辭沒有命中目前的意象 ontology；AI 仍應直接閱讀林辭，不能把『未命中』當成『無意義』。")

    with st.expander("易林融合方法邊界"):
        st.write(yilin["historical_method_notice"])
        for rule in yilin["interpretation_contract"]:
            st.write(f"- {rule}")

    st.markdown("### 足球解讀檢查維度")
    st.dataframe(
        [{"維度": row["name"], "解讀問題": " / ".join(row["questions"])} for row in deep["football_dimensions"]],
        hide_index=True,
        use_container_width=True,
    )

    st.markdown("### AI 解卦包")
    st.write(
        f"JARVIS 已附上 {len(contexts)} 筆梅花深層知識與唯一的「{yilin['lookup_key']}」易林轉卦條目；"
        "ChatGPT 依『梅花核心 → 易林轉變情境 → 支持／反證 → 綜合判讀』解讀。"
    )
    packet_json = json.dumps(packet, ensure_ascii=False, indent=2)
    with st.expander("查看完整 DIVINATION_PACKET_V1"):
        st.code(packet_json, language="json")
    st.download_button(
        "下載 AI 解卦包 JSON",
        data=packet_json,
        file_name=f"meihua-{packet['packet_sha256'][:12]}.json",
        mime="application/json",
        use_container_width=True,
    )
    st.page_link("pages/4_AI_Packet.py", label="前往 AI 解卦包頁", icon="🤖", use_container_width=True)
