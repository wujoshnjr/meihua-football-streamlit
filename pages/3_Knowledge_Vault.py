from __future__ import annotations

import streamlit as st

from jarvis.stark_vault import search_vault, vault_stats
from jarvis.yilin import search_yilin, yilin_catalog_stats, yilin_semantic_audit


st.set_page_config(page_title="術數知識庫 · JARVIS", page_icon="📚", layout="wide")
st.title("📚 奇門遁甲 × 梅花易數 × 焦氏易林知識庫")
st.caption("古典原義、數位轉錄、結構化深層解析與足球衍生義分層保存；JARVIS 負責檢索，最後解讀交給 ChatGPT。")

stats = vault_stats()
yilin_stats = yilin_catalog_stats()
yilin_audit = yilin_semantic_audit()
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

st.markdown("### 《焦氏易林》完整轉卦層")
i, j, k, l = st.columns(4)
i.metric("轉卦林辭", f"{yilin_stats['materialized_pairs']} / {yilin_stats['expected_pairs']}")
j.metric("本卦 blocks", f"{yilin_stats['materialized_from_hexagrams']} / 64")
k.metric("易林意象原子", yilin_stats["ontology_atoms"])
l.metric("heuristic 命中", f"{yilin_audit['match_ratio']:.1%}")
st.success("WYG／文淵閣四庫全書數位轉錄已完整 materialize 4096 / 4096 本卦→之卦 pair。")
st.caption(
    "4096/4096 指轉卦矩陣與 WYG base transcription 完整；多版本異文、現代標點與歷代注解仍分層持續校勘。"
    "heuristic 命中率只是意象檢索覆蓋，不代表占測準確率。"
)

query = st.text_input(
    "搜尋",
    placeholder="例如：生門、天蓬、九天、未濟、乾之坤、坤之乾、道路、傷病、轉折、反擊…",
)
if query.strip():
    results = [*search_vault(query), *search_yilin(query)]
    st.write(f"找到 {len(results)} 筆（單次最多顯示 200 筆跨庫結果）")
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
                if row.get("system") == "JIAOSHI_YILIN" and row.get("family") == "transformation":
                    st.markdown(f"**林辭**：{row.get('classical_text', '')}")
                    st.caption(
                        f"{row.get('source_edition', '')}｜{row.get('source_volume_file', '')}｜"
                        f"{row.get('source_page_start', '')}"
                    )
                    if row.get("source_label_order_anomaly"):
                        st.warning("此條存在已登錄的來源卦名標籤 anomaly；原轉錄標籤已保留。")
                    with st.expander("完整 provenance / raw record"):
                        st.json(row)
                else:
                    st.json(row)
    else:
        st.info("沒有找到符合內容。")
else:
    st.info(
        "可搜尋完整 4096 焦氏易林轉卦、易林意象 ontology、梅花六十四卦／八卦／體用／動爻／本互變，"
        "以及奇門九宮／八門／九星／八神、306 關係槽位、八神深層調制、空馬／迫墓刑與格局。"
    )

st.markdown("### 資料庫邊界")
st.markdown(
    """
- **古籍／傳統義理**：保存來源與結構化摘要；數位轉錄不等於所有版本已完成校勘。
- **奇門深層解析**：宮→門→星→神→天地盤干→格局／空馬，並只附本局真正命中的關係。
- **梅花深層解析**：本卦→上下卦→體用→旺衰→互卦→變卦→動爻，保持 deterministic 起卦權威。
- **焦氏易林 bridge**：4096/4096 pair 已入庫；只使用梅花「本卦 → 最終變卦」查唯一林辭，不重新起卦、不拿互卦冒充焦林原始占法。
- **原文治理**：每條易林保存 WYG 來源卷、頁、raw transcription、校語、gaiji token；來源異體或疑似誤標不靜默修改。
- **易林意象 ontology**：Operation STARK 的 project heuristic，只幫 AI 檢索具象情境，不是《焦氏易林》原註。
- **足球衍生義**：modern application，必須同時保留支持與反證；不冒充古籍，也不自動換算勝率或比分。
- **多版本校勘**：Wikisource、Chinese Text Project 等作 crosscheck；異文與後世注解另層版本化，不混進林辭原文。
- **最終解讀**：`DIVINATION_PACKET_V1` 交給 ChatGPT，AI 不得重新起局／起卦或修改 packet 盤象。
"""
)
