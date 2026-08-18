from __future__ import annotations

import json

import streamlit as st


st.set_page_config(page_title="AI 解卦包 · JARVIS", page_icon="🤖", layout="wide")
st.title("🤖 AI 解卦包")
st.caption("JARVIS 到這裡為止：盤與知識整理完成。接下來把完整 packet 交給 ChatGPT 解讀。")

packet = st.session_state.get("stark_packet")
if not packet:
    st.info("目前工作階段還沒有 AI 解卦包。請從上方導覽前往「奇門起局」或「梅花起卦」建立一份。")
    st.stop()

context = packet.get("knowledge_context", [])
kinds = [row.get("kind") for row in context]
st.success(f"{packet['system']}｜{packet['schema_version']}｜{packet['packet_sha256']}")

c1, c2, c3 = st.columns(3)
c1.metric("知識條目", len(context))
if packet["system"] == "QIMEN_DUNJIA":
    c2.metric("深層宮位解析", kinds.count("qimen_palace_deep_profile"))
    c3.metric("關係條目", kinds.count("qimen_relation"))
else:
    c2.metric("本／互／變深層層次", 3 if "meihua_deep_profile" in kinds else 0)
    c3.metric("體用／動爻深層解析", 2 if "meihua_deep_profile" in kinds else 0)

st.markdown("### 交給 ChatGPT 時的固定指令")
st.code(
    "請依這份 JARVIS DIVINATION_PACKET_V1 解局／解卦。\n"
    "不要重新起局或起卦，也不要修改 packet 內的盤象。\n"
    "優先讀取 knowledge_context 內的 deep_reading_policy / deep_profile。\n"
    "奇門請按：整體局勢→主客用神→宮→門→星→神→天地盤干→格局／空馬→證據／反證。\n"
    "梅花請按：本卦→上下卦內外→體用→旺衰→互卦→變卦→動爻→證據／反證。\n"
    "請分成：盤象事實、古典／知識庫依據、足球現代類比、支持訊號、反證訊號、綜合判讀與不確定性。\n"
    "若內容互相矛盾，請直接指出，不要強行統一。",
    language=None,
)

packet_json = json.dumps(packet, ensure_ascii=False, indent=2)
st.markdown("### 完整 Packet")
st.code(packet_json, language="json")
st.download_button(
    "下載 DIVINATION_PACKET_V1.json",
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
        st.write("保存知識、起局／起卦、固定盤象、檢索相關條目、建立深層結構化上下文、產生 packet。")
with b:
    with st.container(border=True):
        st.markdown("**ChatGPT**")
        st.write("閱讀 packet，合參盤象、古典義理、深層關係與足球情境，完成最後解讀。")
