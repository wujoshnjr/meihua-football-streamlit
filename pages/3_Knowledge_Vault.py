from __future__ import annotations

import streamlit as st

from jarvis.stark_vault import search_vault, vault_stats


st.set_page_config(page_title="術數知識庫 · JARVIS", page_icon="📚", layout="wide")
st.title("📚 奇門遁甲 × 梅花易數知識庫")
st.caption("古典原義、專案摘要、足球衍生義分欄保存；JARVIS 負責檢索，不在這裡替你下最終結論。")

stats = vault_stats()
a, b, c, d, e = st.columns(5)
a.metric("奇門九宮", stats["qimen_palaces"])
b.metric("八門", stats["qimen_doors"])
c.metric("九星／八神", stats["qimen_stars"] + stats["qimen_deities"])
d.metric("梅花八卦", stats["meihua_trigrams"])
e.metric("六十四卦", stats["meihua_hexagrams"])

query = st.text_input("搜尋", placeholder="例如：生門、天蓬、伏吟、乾、未濟、體克用、反擊、傷停…")
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
    st.info("輸入關鍵字後搜尋。六十四卦、八卦、奇門九宮／八門／九星／八神與格局均可檢索。")

st.markdown("### 資料庫邊界")
st.markdown(
    """
- **古籍／傳統義理**：保存來源與結構化摘要。
- **足球衍生義**：是 JARVIS 專案的現代應用推演，不冒充古籍原文。
- **最終解讀**：不由資料庫自動決定，需把起局／起卦後的 `DIVINATION_PACKET_V1` 交給 ChatGPT 綜合判讀。
- **禁止事後改盤**：賽後結果不能回寫原始盤象、卦象或原問題。
"""
)
