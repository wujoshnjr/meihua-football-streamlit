from __future__ import annotations

import json

import streamlit as st


st.set_page_config(page_title="AI 解卦包 · JARVIS", page_icon="🤖", layout="wide")
st.title("🤖 AI 解卦包")
st.caption("JARVIS 到這裡為止：方法身份、盤／卦、原典來源、易林、矛盾與不確定性已固定。接下來把完整 packet 交給 ChatGPT 解讀。")

packet = st.session_state.get("stark_packet")
if not packet:
    st.info("目前工作階段還沒有 AI 解卦包。請從上方導覽前往「奇門起局」或「梅花起卦」建立一份。")
    st.stop()

context = packet.get("knowledge_context", [])
kinds = [row.get("kind") for row in context]
st.success(f"{packet['system']}｜{packet['schema_version']}｜{packet['packet_sha256']}")

c1, c2, c3, c4 = st.columns(4)
c1.metric("知識條目", len(context))
if packet["system"] == "QIMEN_DUNJIA":
    c2.metric("深層宮位解析", kinds.count("qimen_palace_deep_profile"))
    c3.metric("關係條目", kinds.count("qimen_relation"))
    c4.metric("周易／易林", "不適用")
else:
    c2.metric("本／互／變", 3 if "meihua_deep_profile" in kinds else 0)
    zhouyi = packet.get("zhouyi_review", {})
    zstats = zhouyi.get("catalog_stats", {})
    c3.metric(
        "周易原典",
        f"{zstats.get('materialized_hexagrams', 0)}/64 · {zstats.get('materialized_standard_lines', 0)}/384",
    )
    yilin = packet.get("yilin_bridge", {})
    stats = yilin.get("catalog_stats", {})
    c4.metric("焦氏易林", f"{stats.get('materialized_pairs', 0)}/{stats.get('expected_pairs', 4096)}")

st.markdown("### 交給 ChatGPT 時的固定指令")
if packet["system"] == "QIMEN_DUNJIA":
    instruction = (
        f"請依這份 JARVIS {packet['schema_version']} 解奇門局。\n"
        "不要重新起局，也不要修改 packet 內的盤象。\n"
        "先讀整體局勢與主客用神，再按：宮→門→星→神→天地盤干→格局／空馬。\n"
        "每一個足球推論都分清盤象事實、知識庫依據、modern application、支持訊號與反證訊號。\n"
        "遇到相互矛盾的宮位或格局要保留矛盾，不可為了給單一答案而刪除反證。\n"
        "最後才做綜合判讀，並說明關鍵轉折與不確定性。"
    )
else:
    instruction = (
        f"請依這份 JARVIS {packet['schema_version']} 解梅花卦。\n"
        "不要重新起卦，也不要修改本卦、互卦、變卦、動爻、體用或 JARVIS 的來源 lookup。\n"
        "第一步先讀 meihua_method_audit，確認本次起卦方法分類與周易文本權重。\n"
        "本 packet 的年月日時法屬 XIANTIAN_NUMBER_METHOD：先讀本卦／體用、旺衰、互卦與變用的作用網；《周易》卦辭／彖／象／真正動爻爻辭屬 SUPPORTING source-aware review。\n"
        "不得讓單句爻辭覆蓋體用旺衰與互變，也不得把通用爻位直接換成固定比賽分鐘。\n"
        "三要、十應與外應若標記 NOT_RECORDED，就是缺失資料；不可用賽後事件或想像內容補造。\n"
        "再讀焦氏易林 classical_entry.classical_text；MEIHUA_YILIN_BRIDGE 只補本卦→最終變卦情境，不重起一套卦。\n"
        "先檢查 review_summary.contradiction_register 與 uncertainty_register，任何衝突與資料缺口都必須保留。\n"
        "周易／易林原文、數位轉錄、project heuristic、football modern application 必須分層陳述。\n"
        "不可把單一卦、單一爻、單條林辭直接換成勝率、固定比分或必然勝負。\n"
        "最後才給出整體劇本、可能轉折、支持與反證，以及不確定性。"
    )
st.code(instruction, language=None)

if packet["system"] == "MEIHUA_YISHU":
    method_audit = packet.get("meihua_method_audit", {})
    with st.expander("梅花古法方法審查", expanded=True):
        method = method_audit.get("method", {})
        weighting = method_audit.get("weighting_decision", {})
        st.write(
            f"**方法**：{method.get('name', '—')}｜**分類**：{method.get('class', '—')}｜"
            f"**周易角色**：{weighting.get('zhouyi_role', '—')}｜**status**：{method_audit.get('status', '—')}"
        )
        st.info(weighting.get("zhouyi_rule", ""))
        network = method_audit.get("body_use_network", {})
        layers = network.get("layers", [])
        if layers:
            st.dataframe(
                [
                    {
                        "作用層": row["layer"],
                        "相對階段": row["relative_stage"],
                        "卦": row["trigram"],
                        "對體關係": row["relation_to_body"],
                    }
                    for row in layers
                ],
                hide_index=True,
                use_container_width=True,
            )
        external = method_audit.get("external_response_audit", {})
        st.warning(
            f"三要：{external.get('three_essentials', '—')}｜十應：{external.get('ten_responses', '—')}｜"
            f"外應：{external.get('external_omens', '—')}。{external.get('anti_backfill', '')}"
        )
        if method_audit.get("unimplemented_classical_layers"):
            st.markdown("**目前未實作／未記錄的古法層**")
            for item in method_audit["unimplemented_classical_layers"]:
                st.write(f"- {item}")

    zhouyi = packet.get("zhouyi_review", {})
    with st.expander("《周易》原典 AI 交接摘要", expanded=True):
        audit = zhouyi.get("source_audit", {})
        st.write(
            f"**source audit**：{'PASS' if audit.get('all_core_alignments_match') else 'REVIEW'}｜"
            f"**moving line**：{'PASS' if audit.get('moving_line_matches_snapshot') else 'REVIEW'}｜"
            f"**小象**：{audit.get('moving_line_xiaoxiang_status', '—')}｜"
            f"**本次文本權重**：{method_audit.get('weighting_decision', {}).get('zhouyi_role', '—')}"
        )
        for label, key in (("本卦", "original"), ("互卦", "mutual"), ("變卦", "changed")):
            row = zhouyi.get(key, {})
            if row:
                st.markdown(f"**{label} · {row.get('symbol', '')} {row.get('name', '')}**")
                st.write(f"卦辭：{row.get('guaci', {}).get('classical_text', '')}")
        moving = zhouyi.get("moving_line", {})
        if moving:
            st.markdown(f"**真正動爻 · {moving.get('marker', '')}**")
            st.write(moving.get("classical_text", ""))
            small = moving.get("xiaoxiang") or {}
            if small.get("status") == "MAPPED":
                st.markdown("**小象**")
                st.write(small.get("classical_text", ""))
            elif small.get("status") == "GROUPED_IN_QIAN_XIANG_BLOCK":
                st.info("此乾卦底本把六小象集中在同一象傳 block；JARVIS 保留來源例外，不擅自切分成假定原文。")
            st.caption(
                f"{moving.get('source_file', '')}｜{moving.get('source_page_start', '')}｜"
                "爻辭／可直接映射的小象是古籍原文；爻位階段、語義 atom 與足球含意是 JARVIS 專案層。"
            )

            profile = moving.get("semantic_profile") or {}
            if profile:
                marker_rows = profile.get("judgment_markers", [])
                atom_rows = profile.get("semantic_atoms", [])
                if marker_rows:
                    st.markdown("**經文字詞判斷標記（僅作審查，不直接定賽果）**")
                    for row in marker_rows:
                        st.write(f"- {'／'.join(row['matched_terms'])}：{row['project_note']}")
                if atom_rows:
                    st.markdown("**動爻語義 atoms · PROJECT_HEURISTIC**")
                    st.dataframe(
                        [
                            {
                                "領域": row["domain"],
                                "意象": row["name"],
                                "命中字詞": "、".join(row["matched_terms"]),
                                "專案抽象": row["project_abstraction"],
                                "足球候選情境": "；".join(row["football"]),
                            }
                            for row in atom_rows
                        ],
                        hide_index=True,
                        use_container_width=True,
                    )
                    left, right = st.columns(2)
                    with left:
                        st.markdown("**支持訊號**")
                        for item in profile.get("observable_signals", []):
                            st.write(f"- {item}")
                    with right:
                        st.markdown("**反證訊號**")
                        for item in profile.get("counter_signals", []):
                            st.write(f"- {item}")
                else:
                    st.caption("此動爻未命中目前 ontology；ChatGPT 仍須直接閱讀經文，不能把未命中當成無義。")

    yilin = packet.get("yilin_bridge", {})
    with st.expander("《焦氏易林》AI 交接摘要", expanded=True):
        st.write(f"**lookup**：{yilin.get('lookup_key', '—')}｜**status**：{yilin.get('status', '—')}")
        entry = yilin.get("classical_entry") or {}
        if entry:
            st.write(f"**林辭**：{entry.get('classical_text', '')}")
            provenance = yilin.get("provenance", {})
            st.caption(
                f"{provenance.get('edition', '')}｜{provenance.get('volume_file', '')}｜"
                f"{provenance.get('page_start', '')}"
            )
        st.caption("梅花定結構 × 周易依方法定權重 × 易林補劇情 × ChatGPT 合參。易林不重起卦，也不改變梅花 deterministic chart。")

    review = packet.get("review_summary", {})
    with st.expander("矛盾／不確定性／來源覆蓋", expanded=True):
        st.write(
            f"**review status**：{review.get('status', '—')}｜"
            f"**張力**：{len(review.get('contradiction_register', []))}｜"
            f"**不確定性**：{len(review.get('uncertainty_register', []))}"
        )
        for item in review.get("contradiction_register", []):
            st.markdown(f"**{item['id']} · {item['type']}**")
            st.write(item["why_tension_exists"])
            st.caption(item["resolution_rule"])
        for item in review.get("uncertainty_register", []):
            st.markdown(f"**{item['id']}**")
            st.write(item["unknown"])
            st.caption(f"影響：{item['impact']}｜降低方式：{item['what_would_reduce_uncertainty']}")
        if review.get("source_coverage_audit"):
            st.markdown("**source coverage audit**")
            st.json(review["source_coverage_audit"])

packet_json = json.dumps(packet, ensure_ascii=False, indent=2)
st.markdown("### 完整 Packet")
st.code(packet_json, language="json")
st.download_button(
    f"下載 {packet['schema_version']}.json",
    data=packet_json,
    file_name=f"divination-{packet['packet_sha256'][:12]}.json",
    mime="application/json",
    use_container_width=True,
)

st.markdown("### JARVIS / AI 分工")
a, b = st.columns(2)
with a:
    with st.container(border=True):
        st.markdown("**JARVIS**")
        st.write("保存知識、固定起局／起卦、辨別方法、核對原典來源、查唯一相關條目、登錄矛盾／不確定性、建立 packet。")
with b:
    with st.container(border=True):
        st.markdown("**ChatGPT**")
        st.write("不重排盤；按方法權重閱讀梅花結構、周易原典、易林情境、支持／反證與 modern application，完成最後合參。")
