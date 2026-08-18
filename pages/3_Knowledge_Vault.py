from __future__ import annotations

import streamlit as st

from jarvis.stark_vault import search_vault, vault_stats


st.set_page_config(page_title="術數知識庫 · JARVIS", page_icon="📚", layout="wide")
st.title("📚 奇門遁甲 × 梅花易數知識庫")
st.caption("古典原義、結構化深層解析、足球衍生義分欄保存；JARVIS 負責檢索，不在這裡替你下最終結論。")

stats = vault_stats()
a, b, c, d = st.columns(4)
a.metric("奇門九宮", stats["qimen_palaces"])
b.metric("八門／九星／八神", stats["qimen_doors"] + stats["qimen_stars"] + stats["qimen_deities"])
c.metric("奇門關係", stats["qimen_relations"])
d.metric("奇門深層層次", stats["qimen_deep_layers"])

e, f, g, h = st.columns(4)
e.metric("八神調制", stats["qimen_deity_modulations"])
f.metric("梅花八卦", stats["meihua_trigrams"])
g.metric("梅花六十四卦", stats["meihua_hexagrams"])
h.metric("梅花深層足球維度", stats["meihua_deep_dimensions"])

query = st.text_input("搜尋", placeholder="例如：生門、天蓬、九天、高位擴張、未濟、體克用、終局極限、反擊、傷停…")
if query.strip():
    results = search_vault(query)
    st.write(f"找到 {len(results)} 筆")
    if results:
        for index, row in enumerate(results, 1):
            label = row.get("key") or row.get("name") or row.get("relation") or f"條目 {index}"
            with st.expander(f"{row.get('system', '')} · {row.get('family', '')} · {label}"):
                st.json(row)
    else:
        st.info("沒有找到符合內容。")
else:
    st.info(
        "可搜尋六十四卦、八卦、體用、動爻、本互變、奇門九宮／八門／九星／八神、"
        "306 關係槽位、八神深層調制、空馬／迫墓刑與格局。"
    )

st.markdown("### 資料庫邊界")
st.markdown(
    """
- **古籍／傳統義理**：保存來源與結構化摘要。
- **深層解析層**：把奇門的宮→門→星→神→天地盤干→格局／空馬，以及梅花的本卦→上下卦→體用→旺衰→互卦→變卦→動爻整理成可交給 AI 的固定結構。
- **足球衍生義**：是 JARVIS 專案的現代應用推演，不冒充古籍原文。
- **奇門完整性**：採「基礎符號 + 306 關係矩陣 + 八神調制 + 動態盤面格局」，不是捏造一個有限的奇門卦列表。
- **梅花完整性**：八卦、六十四卦、體用、旺衰、動爻、本互變與上下卦內外共同構成實際解卦上下文。
- **最終解讀**：不由資料庫自動決定，需把起局／起卦後的 `DIVINATION_PACKET_V1` 交給 ChatGPT 綜合判讀。
- **禁止事後改盤**：賽後結果不能回寫原始盤象、卦象或原問題。
"""
)
