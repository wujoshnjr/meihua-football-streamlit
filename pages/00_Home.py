from __future__ import annotations

import streamlit as st

from jarvis.stark_vault import vault_stats
from jarvis.yilin import yilin_catalog_stats, yilin_semantic_audit
from version import __version__


st.set_page_config(page_title="JARVIS 術數 AI", page_icon="☯️", layout="wide")
st.title("JARVIS 術數 AI")
st.caption(f"Operation STARK｜v{__version__}｜JARVIS 起局／起卦與知識整理，ChatGPT 負責最後解讀")

st.success(
    "核心：奇門遁甲知識庫 × 梅花易數知識庫 × 焦氏易林 4096 轉卦層 × deterministic 起局／起卦 × AI 解卦包。",
    icon="⚡",
)

st.info(
    "《焦氏易林》已完成 WYG／文淵閣四庫全書 base transcription 的 64×64＝4096/4096 轉卦覆蓋。"
    "『完整』指 pair matrix 與 WYG base；多版本異文、標點及後世注解仍獨立校勘，不混入古籍原文。"
)

st.markdown(
    """
### 使用方式

1. **奇門起局**或**梅花起卦**：輸入問題與事件所在地時間。
2. JARVIS 用固定方法計算完整盤／卦，不讓 AI 重新排盤。
3. JARVIS 自動抓本盤真正相關的古典義理、深層結構與足球現代應用語義。
4. 梅花起卦再以唯一的「本卦 → 最終變卦」查《焦氏易林》完整 4096 catalog；易林補轉變情境，不重起一套卦。
5. 系統產生 `DIVINATION_PACKET_V1`，保留盤象、林辭、來源、校語、意象 heuristic、支持與反證。
6. 把 AI 解卦包交給 ChatGPT；最後綜合判讀由 AI 完成。

**原則：梅花定結構 × 易林補劇情 × ChatGPT 合參。** 任何足球語義都是 modern application，JARVIS 不把單一符號或林辭寫死成勝率或固定比分。
"""
)

left, right = st.columns(2)
with left:
    with st.container(border=True):
        st.markdown("## 🧭 奇門遁甲")
        st.write(
            "時家奇門・轉盤・拆補法。輸出九宮、天地盤、八門、九星、八神、值符值使、旬空、驛馬、格局、"
            "306 關係槽位實際命中內容，以及每宮『宮→門→星→神→天地盤干→格局／空馬』深層解析。"
        )
        st.page_link("pages/1_Qimen_Cast.py", label="開始奇門起局", icon="🧭", use_container_width=True)
with right:
    with st.container(border=True):
        st.markdown("## ☯️ 梅花易數 × 焦氏易林")
        st.write(
            "年月日時起卦。輸出本卦、互卦、變卦、動爻、體用、生克、旺衰、上下卦內外與五行互動；"
            "再查唯一『本卦→變卦』易林林辭、來源定位與情境語義。"
        )
        st.page_link("pages/2_Meihua_Cast.py", label="開始梅花起卦", icon="☯️", use_container_width=True)

stats = vault_stats()
yilin = yilin_catalog_stats()
yilin_audit = yilin_semantic_audit()
st.markdown("### 藏書庫核心覆蓋")
a, b, c, d = st.columns(4)
a.metric(
    "奇門基礎符號",
    stats["qimen_palaces"]
    + stats["qimen_doors"]
    + stats["qimen_stars"]
    + stats["qimen_deities"]
    + stats["qimen_stems"],
)
b.metric("奇門關係矩陣", stats["qimen_relations"])
c.metric("梅花六十四卦", stats["meihua_hexagrams"])
d.metric("焦氏易林", f"{yilin['materialized_pairs']}/{yilin['expected_pairs']}")

e, f, g, h = st.columns(4)
e.metric("八神深層調制", stats["qimen_deity_modulations"])
f.metric("梅花八卦", stats["meihua_trigrams"])
g.metric("易林意象原子", yilin["ontology_atoms"])
h.metric("易林 heuristic 覆蓋", f"{yilin_audit['match_ratio']:.1%}")
st.caption("易林 heuristic 覆蓋只是語義檢索覆蓋，不是術數有效率或足球預測準確率。")

st.markdown("### 輔助入口")
x, y = st.columns(2)
with x:
    st.page_link("pages/3_Knowledge_Vault.py", label="📚 搜尋奇門／梅花／焦氏易林", use_container_width=True)
with y:
    st.page_link("pages/4_AI_Packet.py", label="🤖 查看最新 AI 解卦包", use_container_width=True)

st.divider()
st.caption("JARVIS 負責盤與知識；ChatGPT 負責解。古籍、注解、專案 heuristic 與足球 modern application 嚴格分層。")
