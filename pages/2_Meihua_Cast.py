from __future__ import annotations

import json
from datetime import date, datetime, time

import streamlit as st

from jarvis.divination_packet import build_meihua_packet
from jarvis.time import EventLocalTimeError, aware_event_local_datetime, inspect_local_civil_time


st.set_page_config(page_title="梅花起卦 · JARVIS", page_icon="☯️", layout="wide")
st.title("☯️ 梅花易數起卦")
st.caption(
    "年月日時 deterministic 起卦；先做梅花古法方法審查，再整理本卦、互卦、變卦、體用、旺衰、動爻，"
    "核對《周易》原典並加入《焦氏易林》本卦→變卦鏡頭，最後交給 ChatGPT 合參。足球若要建立事件卦與 collision audit，請使用「足球多層案件」。"
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
        event_time = st.time_input("事件時間", value=time(20, 0), step=1, format="24h")
    with c3:
        timezone_name = st.text_input("事件所在地 IANA 時區", value="Asia/Taipei")
    fold_mode = st.selectbox(
        "DST 重複時間",
        ["AUTO_REJECT_AMBIGUOUS", "FIRST_FOLD_0", "SECOND_FOLD_1"],
        help="一般時間維持 AUTO；DST 回撥造成同一 local time 出現兩次時必須明確選 fold。",
    )

    submitted = st.form_submit_button("起梅花卦並建立 AI 解卦包", type="primary", use_container_width=True)

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
    except (ValueError, EventLocalTimeError, RuntimeError) as exc:
        st.error(str(exc))

packet = st.session_state.get("stark_packet")
if packet and packet.get("system") == "MEIHUA_YISHU":
    hx = packet["hexagram"]
    contexts = packet["knowledge_context"]
    original = next(row for row in contexts if row.get("kind") == "meihua_original_hexagram")
    mutual = next(row for row in contexts if row.get("kind") == "meihua_mutual_hexagram")
    changed = next(row for row in contexts if row.get("kind") == "meihua_changed_hexagram")
    deep = next(row for row in contexts if row.get("kind") == "meihua_deep_profile")
    method_audit = packet["meihua_method_audit"]
    zhouyi = packet["zhouyi_review"]
    yilin = packet["yilin_bridge"]
    review_summary = packet["review_summary"]

    st.success(f"起卦完成｜{packet['schema_version']}｜Packet SHA-256：{packet['packet_sha256']}")
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

    st.markdown("### 梅花古法方法審查")
    ma1, ma2, ma3, ma4 = st.columns(4)
    ma1.metric("起卦方法", method_audit["method"]["name"])
    ma2.metric("方法分類", method_audit["method"]["class"])
    ma3.metric("《周易》角色", method_audit["weighting_decision"]["zhouyi_role"])
    ma4.metric("外應紀錄", method_audit["external_response_audit"]["source_lock"])
    st.warning(
        "目前年月日時法被鎖定為 XIANTIAN_NUMBER_METHOD：體用、生克、旺衰、互變是主要梅花骨架；"
        "《周易》卦辭／彖／象／動爻屬 source-aware SUPPORTING review，不用單句爻辭覆蓋整體結構。"
    )
    st.dataframe(
        [
            {
                "作用層": row["layer"],
                "相對階段": row["relative_stage"],
                "卦": row["trigram"],
                "對體關係": row["relation_to_body"],
                "角色": row["role"],
            }
            for row in method_audit["body_use_network"]["layers"]
        ],
        hide_index=True,
        use_container_width=True,
    )
    with st.expander("古法原則、缺失層與禁止補造"):
        for principle in method_audit["classical_principles"]:
            st.markdown(f"**{principle['name']}**")
            st.write(principle["project_summary"])
            st.caption(principle["audit_requirement"])
        st.markdown("**目前尚未實作／未記錄**")
        for item in method_audit["unimplemented_classical_layers"]:
            st.write(f"- {item}")
        st.caption(method_audit["completion_note"])
        st.error(method_audit["external_response_audit"]["anti_backfill"])

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

    st.markdown("### 《周易》原典審查 · 64 卦 / 384 爻")
    zs = zhouyi["catalog_stats"]
    z1, z2, z3, z4 = st.columns(4)
    z1.metric("周易卦體", f"{zs['materialized_hexagrams']} / {zs['expected_hexagrams']}")
    z2.metric("標準爻辭", f"{zs['materialized_standard_lines']} / {zs['expected_standard_lines']}")
    z3.metric("用九／用六", zs["use_lines"])
    z4.metric("原典審查", "PASS" if zhouyi["source_audit"]["all_core_alignments_match"] else "REVIEW")
    st.caption(
        f"固定來源：{zs['source_repository']} @ {str(zs['source_commit'])[:12]}…｜{zs['source_edition']}。"
        "這代表固定數位底本的結構化轉錄完整，不宣稱所有歷代版本校勘已完成。"
    )

    if not zhouyi["source_audit"]["all_core_alignments_match"]:
        st.error("《周易》原典層與梅花 64 卦 catalog 存在對齊問題；本次解讀應先停止並檢查來源。")
    else:
        st.success("本卦／互卦／變卦的卦序、卦名、卦符、上下卦已通過 source-aware 對齊審查。")

    for label, key in (("本卦", "original"), ("互卦", "mutual"), ("變卦", "changed")):
        classical = zhouyi[key]
        with st.expander(f"{label} · {classical['symbol']} {classical['name']}｜卦辭／彖／象", expanded=(key == "original")):
            st.markdown("**卦辭**")
            st.write(classical["guaci"]["classical_text"])
            st.caption(f"source page: {classical['guaci'].get('source_page_start') or '—'}")
            st.markdown("**彖**")
            st.write(classical["tuan"]["classical_text"])
            st.caption(f"source page: {classical['tuan'].get('source_page_start') or '—'}")
            st.markdown("**象**")
            st.write(classical["xiang"]["classical_text"])
            if classical["xiang"].get("note"):
                st.caption(classical["xiang"]["note"])
            st.caption(
                f"{classical['source']['file']}｜page {classical['xiang'].get('source_page_start') or '—'}｜"
                f"SHA-256 {classical['source']['sha256'][:16]}…"
            )

    moving = zhouyi["moving_line"]
    st.markdown("#### 真正動爻原文")
    with st.container(border=True):
        st.markdown(f"**第 {moving['line']} 爻 · {moving['marker']}**")
        st.write(moving["classical_text"])
        st.caption(f"來源：{moving['source_file']}｜{moving['source_page_start']}")
        st.markdown(f"**JARVIS 爻位階段：{moving['phase']}**")
        st.write(moving["project_general"])
        if football:
            st.caption("足球 modern application：" + moving["football_modern_application"])
        st.info(moving["boundary"])
        st.warning("本次為先天數法：動爻原文必須閱讀，但在權重上屬 SUPPORTING，不得單句取代體用旺衰與互變。")

    with st.expander("易經審查維度與足球含意邊界"):
        for dimension in zhouyi["review_dimensions"]:
            st.markdown(f"**{dimension['name']}**")
            for question_item in dimension["questions"]:
                st.write(f"- {question_item}")
            st.caption(dimension["football_rule"])
        st.markdown("**禁止捷徑**")
        for shortcut in zhouyi["football_meaning_contract"]["forbidden_shortcuts"]:
            st.write(f"- {shortcut}")

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
            st.write("**原典爻辭 supporting 核對：** " + moving["classical_text"])

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

    st.markdown("### 矛盾、不確定性與來源覆蓋")
    ra1, ra2, ra3 = st.columns(3)
    ra1.metric("結構訊號", len(review_summary["relation_signals"]))
    ra2.metric("已登錄張力", len(review_summary["contradiction_register"]))
    ra3.metric("不確定性", len(review_summary["uncertainty_register"]))
    if review_summary["contradiction_register"]:
        with st.expander("查看矛盾／張力登錄", expanded=True):
            for item in review_summary["contradiction_register"]:
                st.markdown(f"**{item['id']} · {item['type']}**")
                st.write(item["why_tension_exists"])
                st.caption(item["resolution_rule"])
    with st.expander("查看不確定性登錄"):
        for item in review_summary["uncertainty_register"]:
            st.markdown(f"**{item['id']}**")
            st.write(item["unknown"])
            st.caption(f"影響：{item['impact']}｜降低方式：{item['what_would_reduce_uncertainty']}")
    with st.expander("來源覆蓋 audit"):
        st.json(review_summary["source_coverage_audit"])

    st.markdown("### 足球解讀檢查維度")
    st.dataframe(
        [{"維度": row["name"], "解讀問題": " / ".join(row["questions"])} for row in deep["football_dimensions"]],
        hide_index=True,
        use_container_width=True,
    )

    st.markdown("### AI 解卦包")
    st.write(
        f"JARVIS 已附上古法方法審查、《周易》64/384 原典審查、{len(contexts)} 筆梅花深層知識、"
        f"唯一的「{yilin['lookup_key']}」易林轉卦條目，以及矛盾／不確定性 register；"
        "ChatGPT 依『方法審查 → 梅花結構 → 周易 supporting review → 易林轉變情境 → 支持／反證／矛盾 → 綜合判讀』解讀。"
    )
    packet_json = json.dumps(packet, ensure_ascii=False, indent=2)
    with st.expander(f"查看完整 {packet['schema_version']}"):
        st.code(packet_json, language="json")
    st.download_button(
        "下載 AI 解卦包 JSON",
        data=packet_json,
        file_name=f"meihua-{packet['packet_sha256'][:12]}.json",
        mime="application/json",
        use_container_width=True,
    )
    st.page_link("pages/4_AI_Packet.py", label="前往 AI 解卦包頁", icon="🤖", use_container_width=True)
