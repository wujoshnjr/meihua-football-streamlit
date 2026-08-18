from __future__ import annotations

import json

import streamlit as st


st.set_page_config(page_title="AI 解卦包 · JARVIS", page_icon="🤖", layout="wide")
st.title("🤖 AI 解卦包")
st.caption("JARVIS 到這裡為止：盤、卦、原典來源、易林與相關知識已固定。接下來把完整 packet 交給 ChatGPT 解讀。")

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
        f"請依這份 JARVIS {packet['schema_version']} 解梅花卦，合參 zhouyi_review 與 MEIHUA_YILIN_BRIDGE。\n"
        "不要重新起卦，也不要修改本卦、互卦、變卦、動爻、體用或 JARVIS 的來源 lookup。\n"
        "先核對 zhouyi_review.source_audit，再依序讀本卦卦辭／彖／象、上下卦內外、體用旺衰、互卦、真正動爻爻辭、變卦。\n"
        "周易 classical_text 是固定來源數位轉錄；project_general 與 football_modern_application 是專案層，必須分開。\n"
        "再讀焦氏易林 classical_entry.classical_text 與 semantic_profile；semantic_profile/image_atoms 是專案 heuristic，不是焦氏原註。\n"
        "若周易、梅花核心與易林情境互相矛盾，要把矛盾當作解讀資訊，不得強行統一。\n"
        "古籍數位轉錄、後世注解、專案 heuristic、football modern application 必須分層陳述。\n"
        "不可把單一卦、單一爻、單條林辭直接換成勝率、固定比分或必然勝負。\n"
        "最後才給出整體劇本、可能轉折、支持與反證，以及不確定性。"
    )
st.code(instruction, language=None)

if packet["system"] == "MEIHUA_YISHU":
    zhouyi = packet.get("zhouyi_review", {})
    with st.expander("《周易》原典 AI 交接摘要", expanded=True):
        audit = zhouyi.get("source_audit", {})
        st.write(
            f"**source audit**：{'PASS' if audit.get('all_core_alignments_match') else 'REVIEW'}｜"
            f"**moving line**：{'PASS' if audit.get('moving_line_matches_snapshot') else 'REVIEW'}"
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
            st.caption(
                f"{moving.get('source_file', '')}｜{moving.get('source_page_start', '')}｜"
                "爻辭是古籍原文；爻位階段與足球含意是 JARVIS 專案層。"
            )

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
        st.caption("周易核文本 × 梅花定結構 × 易林補劇情 × ChatGPT 合參。易林不重起卦，也不改變梅花 deterministic chart。")

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
        st.write("保存知識、固定起局／起卦、核對原典來源、查唯一相關條目、保存 provenance、建立深層上下文、產生 packet。")
with b:
    with st.container(border=True):
        st.markdown("**ChatGPT**")
        st.write("不重排盤；閱讀周易原典、梅花結構、易林情境、支持／反證與現代足球語義，完成最後合參。")
