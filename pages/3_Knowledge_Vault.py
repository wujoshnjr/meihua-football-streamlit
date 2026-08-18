from __future__ import annotations

import streamlit as st

from jarvis.stark_vault import search_vault, vault_stats
from jarvis.yilin import search_yilin, yilin_catalog_stats


st.set_page_config(page_title="術數知識庫 · JARVIS", page_icon="📚", layout="wide")
st.title("📚 奇門遁甲 × 梅花易數 × 焦氏易林知識庫")
st.caption("古典原義、結構化深層解析、足球衍生義分欄保存；JARVIS 負責檢索，不在這裡替你下最終結論。")

stats = vault_stats()
yilin_stats = yilin_catalog_stats()
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

i, j, k = st.columns(3)
i.metric("焦氏易林已入庫", yilin_stats["materialized_pairs"])
j.metric("焦氏易林目標", yilin_stats["expected_pairs"])
k.metric("易林覆蓋率", f"{yilin_stats['coverage_ratio']:.2%}")
st.caption("JARVIS 10 alpha 目前只 materialize《四庫全書本》卷一『乾之第一』64 條；其餘不得生成、猜測或假裝已入庫。")

query = st.text_input("搜尋", placeholder="例如：生門、天蓬、九天、未濟、乾之坤、道路、傷病、終局極限、反擊…")
if query.strip():
    results = [*search_vault(query), *search_yilin(query)]
    st.write(f"找到 {len(results)} 筆")
    if results:
        for index, row in enumerate(results, 1):
            label = (
                row.get("lookup_key")
                or row.get("key")
                or row.get("name")
                or row.get("relation")
                or f"條目 {index}"
            )
            with st.expander(f"{row.get('system', '')} · {row.get('family', '')} · {label}"):
                st.json(row)
    else:
        st.info("沒有找到符合內容。")
else:
    st.info(
        "可搜尋六十四卦、八卦、體用、動爻、本互變、焦氏易林已 materialize 的轉卦林辭與意象原子、"
        "奇門九宮／八門／九星／八神、306 關係槽位、八神深層調制、空馬／迫墓刑與格局。"
    )

st.markdown("### 資料庫邊界")
st.markdown(
    """
- **古籍／傳統義理**：保存來源與結構化摘要。
- **深層解析層**：把奇門的宮→門→星→神→天地盤干→格局／空馬，以及梅花的本卦→上下卦→體用→旺衰→互卦→變卦→動爻整理成可交給 AI 的固定結構。
- **焦氏易林 bridge**：只使用梅花「本卦 → 最終變卦」查唯一林辭；不重新起卦，也不把互卦冒充焦林原始占法。
- **易林意象原子**：是 Operation STARK 的 project heuristic，不是《焦氏易林》古注。
- **足球衍生義**：是 JARVIS 專案的現代應用推演，不冒充古籍原文。
- **奇門完整性**：採「基礎符號 + 306 關係矩陣 + 八神調制 + 動態盤面格局」，不是捏造一個有限的奇門卦列表。
- **梅花完整性**：八卦、六十四卦、體用、旺衰、動爻、本互變與上下卦內外共同構成實際解卦上下文。
- **易林完整性**：目標為 4096/4096；在達成以前，網站必須公開實際 materialized coverage，缺條目時只回報 `SOURCE_PENDING`。
- **最終解讀**：不由資料庫自動決定，需把起局／起卦後的 `DIVINATION_PACKET_V1` 交給 ChatGPT 綜合判讀。
- **禁止事後改盤**：賽後結果不能回寫原始盤象、卦象或原問題。
"""
)
