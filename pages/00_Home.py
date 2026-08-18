from __future__ import annotations

import streamlit as st

from jarvis.stark_vault import vault_stats
from version import __version__


st.set_page_config(page_title="JARVIS 術數 AI", page_icon="☯️", layout="wide")
st.title("JARVIS 術數 AI")
st.caption(f"Operation STARK｜v{__version__}｜JARVIS 起局／起卦與深層知識整理，ChatGPT 負責最後解讀")

st.success(
    "核心已收斂為：奇門遁甲知識庫、梅花易數知識庫、deterministic 起局／起卦、深層盤象上下文、AI 解卦包。",
    icon="⚡",
)

st.markdown(
    """
### 使用方式

1. **奇門起局**或**梅花起卦**：輸入問題與事件所在地時間。
2. JARVIS 用固定方法計算完整盤／卦，不讓 AI 重新排盤。
3. JARVIS 自動從知識庫抓本盤真正相關的古典義理、深層組合關係與足球衍生語義。
4. 系統產生 `DIVINATION_PACKET_V1`。
5. 把 AI 解卦包交給 ChatGPT，最後的綜合解讀由 AI 完成。

足球語義是現代應用層，會和古籍原義分開保存；JARVIS 本身不把任何單一門、星、神、卦直接寫死成勝率或比分。
"""
)

left, right = st.columns(2)
with left:
    with st.container(border=True):
        st.markdown("## 🧭 奇門遁甲")
        st.write(
            "時家奇門・轉盤・拆補法。起局後輸出九宮、天地盤、八門、九星、八神、值符值使、"
            "旬空、驛馬、格局、本盤關係，以及每宮『宮→門→星→神→天地盤干→格局／空馬』深層解析。"
        )
        st.page_link("pages/1_Qimen_Cast.py", label="開始奇門起局", icon="🧭", use_container_width=True)
with right:
    with st.container(border=True):
        st.markdown("## ☯️ 梅花易數")
        st.write(
            "年月日時起卦。輸出本卦、互卦、變卦、動爻、體用、生克、旺衰，"
            "並加入上下卦內外、五行互動、動爻階段與本→互→變深層結構。"
        )
        st.page_link("pages/2_Meihua_Cast.py", label="開始梅花起卦", icon="☯️", use_container_width=True)

stats = vault_stats()
st.markdown("### 藏書庫核心覆蓋")
a, b, c, d, e, f = st.columns(6)
a.metric("奇門基礎符號", stats["qimen_palaces"] + stats["qimen_doors"] + stats["qimen_stars"] + stats["qimen_deities"] + stats["qimen_stems"])
b.metric("奇門關係矩陣", stats["qimen_relations"])
c.metric("八神深層調制", stats["qimen_deity_modulations"])
d.metric("梅花八卦", stats["meihua_trigrams"])
e.metric("梅花六十四卦", stats["meihua_hexagrams"])
f.metric("梅花深層維度", stats["meihua_deep_dimensions"])

st.markdown("### 兩個輔助入口")
x, y = st.columns(2)
with x:
    st.page_link("pages/3_Knowledge_Vault.py", label="📚 搜尋奇門／梅花知識庫", use_container_width=True)
with y:
    st.page_link("pages/4_AI_Packet.py", label="🤖 查看最新 AI 解卦包", use_container_width=True)

st.divider()
st.caption("JARVIS 負責盤與知識；ChatGPT 負責解。術數內容屬傳統文化與研究用途，足球衍生義為現代應用推演。")
