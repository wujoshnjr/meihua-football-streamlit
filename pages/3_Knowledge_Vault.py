from __future__ import annotations

import streamlit as st

from jarvis.stark_vault import search_vault, vault_stats
from jarvis.yilin import search_yilin, yilin_catalog_stats, yilin_semantic_audit
from jarvis.yuanling_vault import search_yuanling, yuanling_catalog_stats
from jarvis.zhouyi import search_zhouyi, zhouyi_catalog_stats


st.set_page_config(page_title="術數知識庫 · JARVIS", page_icon="📚", layout="wide")
st.title("📚 奇門遁甲 × 梅花易數 × 周易 × 焦氏易林 × 元靈經知識庫")
st.caption(
    "古典原義、固定數位轉錄、結構化深層解析與足球衍生義分層保存；"
    "JARVIS 負責檢索，最後解讀交給 ChatGPT。"
)

stats = vault_stats()
zhouyi_stats = zhouyi_catalog_stats()
yilin_stats = yilin_catalog_stats()
yilin_audit = yilin_semantic_audit()
yuanling_stats = yuanling_catalog_stats()
a, b, c, d = st.columns(4)
a.metric("奇門九宮", stats["qimen_palaces"])
b.metric("八門／九星／八神", stats["qimen_doors"] + stats["qimen_stars"] + stats["qimen_deities"])
c.metric("奇門 Core 關係", stats["qimen_relations"])
d.metric("奇門深層層次", stats["qimen_deep_layers"])

e, f, g, h = st.columns(4)
e.metric("八神調制", stats["qimen_deity_modulations"])
f.metric("梅花八卦", stats["meihua_trigrams"])
g.metric("梅花六十四卦", stats["meihua_hexagrams"])
h.metric("梅花深層足球維度", stats["meihua_deep_dimensions"])

st.markdown("### 《周易》原典審查層")
z1, z2, z3, z4 = st.columns(4)
z1.metric("卦體原典", f"{zhouyi_stats['materialized_hexagrams']} / {zhouyi_stats['expected_hexagrams']}")
z2.metric("標準爻辭", f"{zhouyi_stats['materialized_standard_lines']} / {zhouyi_stats['expected_standard_lines']}")
z3.metric("用九／用六", zhouyi_stats["use_lines"])
z4.metric("來源", "PINNED")
st.success("固定 Kanripo《周易》數位轉錄已結構化 materialize 64 / 64 卦與 384 / 384 標準爻。")
st.caption(
    f"{zhouyi_stats['source_repository']} @ {zhouyi_stats['source_commit']}｜{zhouyi_stats['source_edition']}。"
    "這代表固定底本的資料鏈與爻位完整；不代表所有歷代版本、異文與注家校勘全部完成。"
)

st.markdown("### 《焦氏易林》完整轉卦層")
pair_col, block_col, ontology_col, audit_col = st.columns(4)
pair_col.metric("轉卦林辭", f"{yilin_stats['materialized_pairs']} / {yilin_stats['expected_pairs']}")
block_col.metric("本卦 blocks", f"{yilin_stats['materialized_from_hexagrams']} / 64")
ontology_col.metric("易林意象原子", yilin_stats["ontology_atoms"])
audit_col.metric("heuristic 命中", f"{yilin_audit['match_ratio']:.1%}")
st.success("WYG／文淵閣四庫全書數位轉錄已完整 materialize 4096 / 4096 本卦→之卦 pair。")
st.caption(
    "4096/4096 指轉卦矩陣與 WYG base transcription 完整；多版本異文、現代標點與歷代注解仍分層持續校勘。"
    "heuristic 命中率只是意象檢索覆蓋，不代表占測準確率。"
)

st.markdown("### 《奇門遁甲元靈經》Source-aware 數術層")
y1, y2, y3, y4, y5 = st.columns(5)
y1.metric("結構化原典條目", yuanling_stats["structured_sections"])
y2.metric("數術九星", yuanling_stats["numeric_stars"])
y3.metric("日奇門60日表", yuanling_stats["riqimen_day_rows"])
y4.metric("元靈方法", yuanling_stats["yuanling_methods"])
y5.metric("保留未決點", yuanling_stats["unresolved_source_points"])
st.success(
    "元靈資料庫已把卷一奇門起例、三元局表、伏身、演數七要、數主歌訣、日奇門，"
    "以及卷三中宮值日九星與射覆數目關聯分層結構化。"
)
st.caption(
    "原典 primary、crosscheck、project normalization 與 collateral reconstruction 分權保存。"
    "射覆數目與值日九星只屬古典數術資料，不直接轉足球總進球或比分。"
)

query = st.text_input(
    "搜尋",
    placeholder=(
        "例如：生門、天蓬、未濟、乾九五、乾之坤、演數七要、數主、二黑、"
        "日奇門、甲子起休、年月日時起卦…"
    ),
)
if query.strip():
    results = [
        *search_vault(query),
        *search_zhouyi(query),
        *search_yilin(query),
        *search_yuanling(query),
    ]
    st.write(f"找到 {len(results)} 筆（跨庫結果依各檢索器上限顯示）")
    if results:
        for index, row in enumerate(results, 1):
            label = (
                row.get("lookup_key")
                or row.get("key")
                or row.get("name")
                or row.get("relation")
                or f"條目 {index}"
            )
            if row.get("system") == "ZHOUYI" and row.get("family") == "line_source":
                label = f"{row.get('name', '')} · {row.get('marker', '')}"
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
                elif row.get("system") == "ZHOUYI" and row.get("family") == "hexagram_source":
                    st.markdown(f"**{row.get('symbol', '')} {row.get('name', '')}**")
                    st.write(f"**卦辭**：{row.get('guaci', {}).get('classical_text', '')}")
                    st.write(f"**彖**：{row.get('tuan', {}).get('classical_text', '')}")
                    st.write(f"**象**：{row.get('xiang', {}).get('classical_text', '')}")
                    st.caption(f"{row.get('source', {}).get('file', '')}｜{row.get('source', {}).get('commit', '')}")
                elif row.get("system") == "ZHOUYI" and row.get("family") == "line_source":
                    st.markdown(f"**{row.get('symbol', '')} {row.get('name', '')} · {row.get('marker', '')}**")
                    st.write(row.get("classical_text", ""))
                    st.caption(
                        f"第 {row.get('line')} 爻｜{row.get('source_page_start', '')}｜"
                        f"{row.get('source', {}).get('file', '')}"
                    )
                elif row.get("system") in {"YUANLING", "CASTING_METHOD"}:
                    if row.get("summary"):
                        st.write(row["summary"])
                    if row.get("source_locator"):
                        st.caption(
                            f"{row.get('source_locator')}｜authority={row.get('authority', '—')}"
                        )
                    st.json(row)
                else:
                    st.json(row)
    else:
        st.info("沒有找到符合內容。")
else:
    st.info(
        "可搜尋完整《周易》64 卦／384 爻、4096 焦氏易林轉卦、易林意象 ontology、"
        "梅花八卦／體用／動爻／本互變、奇門九宮／八門／九星／八神、Core 306 關係，"
        "以及《元靈經》演數七要、伏身、值日九星、日奇門60日表與四種起局/起卦方法說明。"
    )

st.markdown("### 資料庫邊界")
st.markdown(
    """
- **《周易》原典層**：固定數位底本保存 64 卦、384 標準爻、卦辭、彖、象與來源頁碼；不把固定底本完整誇大成全部版本校勘完成。
- **古籍／傳統義理**：保存來源與結構化摘要；數位轉錄、後世注解、專案解析彼此分層。
- **奇門深層解析**：宮→門→星→神→天地盤干→格局／空馬，並只附本局真正命中的 Core 306 關係子集。
- **梅花深層解析**：本卦→上下卦→體用→旺衰→互卦→真正動爻經文→變卦，保持 deterministic 起卦權威。
- **元靈 source catalog**：卷一與卷三相關排盤／演數條目分層保存；演數七要與日奇門保持獨立，旁證候選不寫回 primary facts。
- **元靈數目資料**：射覆所列數目只作古典數術關聯資料，不能直接轉成足球總進球、比分或概率。
- **焦氏易林 bridge**：4096/4096 pair 已入庫；只使用梅花「本卦 → 最終變卦」查唯一林辭，不重新起卦、不拿互卦冒充焦林原始占法。
- **原文治理**：來源異體、校語、gaiji 或疑似誤標不靜默修改；AI 不可自行補寫古籍。
- **易林意象 ontology**：Operation STARK 的 project heuristic，只幫 AI 檢索具象情境，不是《焦氏易林》原註。
- **足球衍生義**：modern application，必須同時保留支持與反證；不冒充古籍，也不自動換算勝率或比分。
- **最終解讀**：JARVIS packet 交給 ChatGPT，AI 不得重新起局／起卦或修改 packet 盤象。
"""
)
