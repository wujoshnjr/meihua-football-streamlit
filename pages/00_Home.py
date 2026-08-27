from __future__ import annotations

import streamlit as st

from jarvis.stark_vault import vault_stats
from jarvis.yilin import yilin_catalog_stats, yilin_semantic_audit
from jarvis.yuanling_vault import yuanling_catalog_stats
from jarvis.zhouyi import zhouyi_catalog_stats
from version import __version__


st.set_page_config(page_title="JARVIS 術數 AI", page_icon="☯️", layout="wide")
st.title("JARVIS 術數 AI")
st.caption(f"Operation STARK｜v{__version__}｜JARVIS 起局／起卦、原典審查與知識整理，ChatGPT 負責最後解讀")

st.success(
    "核心：奇門遁甲 × 梅花易數 × 六爻納甲／文王卦 ×《周易》64卦/384爻 ×《焦氏易林》4096轉卦 ×《元靈經》演數七要/日奇門 × deterministic 起局／起卦 × AI 解卦包。",
    icon="⚡",
)

st.info(
    "《周易》已建立固定 Kanripo 數位底本的 64/64 卦與 384/384 標準爻來源層；"
    "《焦氏易林》完成 WYG base transcription 64×64＝4096/4096。"
    "《元靈經》把演數七要與日奇門拆成獨立研究元件；數主／飛星／直日星角色關係與日奇門穿宮 mechanics 已 crosschecked reconstruction，仍保留數宮、入門與完整 worked-example 等 authority gaps。"
)

with st.container(border=True):
    st.markdown("## ⚽ 推薦：足球多層術數案件")
    st.write(
        "同一個 event-local datetime / IANA timezone 建立奇門、梅花，並可選加入元靈七要 temporal sibling；再用賽前固定 event / participant identity 做同時開賽 differentiation："
        "**奇門 = RESULT_ENGINE_INPUT**，**梅花 = STRUCTURE_STRESS_TEST**，**元靈 = TEMPORAL_NUMERIC_CONTEXT**，最後才交給 ChatGPT 合參。"
        "元靈不直接加入比分合成，只提供共同時段數勢。"
    )
    st.page_link("pages/5_Football_Case.py", label="建立足球 Case Bundle", icon="⚽", use_container_width=True)

st.markdown(
    """
### 使用方式

1. 足球優先使用 **足球多層術數案件**：同一事件建立奇門、梅花與可選元靈 temporal sibling，並保存 event / participant signatures，處理同時開賽 collision。
2. **奇門起局**：輸入事件所在地 local datetime、IANA timezone、主客隊與問題；JARVIS 依時家轉盤拆補法排完整九宮盤。
3. **梅花起卦**：輸入同一事件時間；目前固定採年月日時先天數法，由年支＋農曆月日＋時支定本卦、動爻、體用、互變與旺衰。
4. **元靈演數**：七要 raw slots 與 crosschecked reconstruction 分層；數主／飛星／直日星角色已解，數宮完整古法與入門完整 mechanics 仍保持 source-tiered。若選實驗模式，另建立日奇門 sibling。
5. 《周易》真正動爻附 source-grounded conditional review；《焦氏易林》只查唯一「本卦→最終變卦」作 transformation lens。
6. 元靈卷三值日九星與射覆數目已入庫，但只作古典數術資料，禁止「宮數/星數/射覆數目 → 足球進球」直譯。
8. 產生 packet 後交給 ChatGPT；AI 不得重新起局／起卦或修改 deterministic 盤象。

**原則：同一時間 → 共同 temporal layers；不同 fixture → 賽前固定 event / participant identity；奇門主結果證據 × 梅花定結構 × 元靈共同數勢 × ChatGPT 最終合參。**
"""
)

q_col, m_col, l_col, y_col = st.columns(4)
with q_col:
    with st.container(border=True):
        st.markdown("## 🧭 奇門遁甲")
        st.write(
            "時家奇門・轉盤・拆補法。輸出九宮、天地盤、八門、九星、八神、值符值使、旬空、驛馬與格局。"
        )
        st.page_link("pages/1_Qimen_Cast.py", label="單獨奇門起局", icon="🧭", use_container_width=True)
with m_col:
    with st.container(border=True):
        st.markdown("## ☯️ 梅花 × 周易 × 易林")
        st.write(
            "年月日時起卦。輸出本卦、體用、互變與旺衰，再核對《周易》與本→變《焦氏易林》。"
        )
        st.page_link("pages/2_Meihua_Cast.py", label="單獨梅花起卦", icon="☯️", use_container_width=True)
with l_col:
    with st.container(border=True):
        st.markdown("## ☷ 六爻納甲")
        st.write(
            "六次 6/7/8/9 排文王卦：納甲、八宮、世應、六親、六神、日月空破、動變與伏神候選；斷法分層審查。"
        )
        st.page_link("pages/7_Liuyao_Cast.py", label="六爻起卦", icon="🪙", width="stretch")
with y_col:
    with st.container(border=True):
        st.markdown("## 🔢 元靈演數 × 日奇門")
        st.write(
            "演數七要與日奇門獨立保存；角色關係與穿宮已 crosschecked，primary、旁證、project normalization 仍分層。"
        )
        st.page_link("pages/6_Yuanling_Yanshu.py", label="元靈演數研究", icon="🔢", use_container_width=True)

stats = vault_stats()
zhouyi = zhouyi_catalog_stats()
yilin = yilin_catalog_stats()
yilin_audit = yilin_semantic_audit()
yuanling = yuanling_catalog_stats()
st.markdown("### 藏書庫核心覆蓋")
a, b, c, d, e = st.columns(5)
a.metric(
    "奇門基礎符號",
    stats["qimen_palaces"]
    + stats["qimen_doors"]
    + stats["qimen_stars"]
    + stats["qimen_deities"]
    + stats["qimen_stems"],
)
b.metric("奇門 Core 關係", stats["qimen_relations"])
c.metric("梅花六十四卦", stats["meihua_hexagrams"])
d.metric("周易原典", f"{zhouyi['materialized_hexagrams']}/64 · {zhouyi['materialized_standard_lines']}/384")
e.metric("元靈原典條目", yuanling["structured_sections"])

f, g, h, i, j = st.columns(5)
f.metric("八神深層調制", stats["qimen_deity_modulations"])
g.metric("梅花八卦", stats["meihua_trigrams"])
h.metric("焦氏易林", f"{yilin['materialized_pairs']}/{yilin['expected_pairs']}")
i.metric("元靈日奇門表", f"{yuanling['riqimen_day_rows']}/60")
j.metric("元靈數術九星", yuanling["numeric_stars"])
st.caption(
    "周易 64/384、易林 4096/4096 與元靈 60 日表是資料覆蓋指標，不是足球預測準確率。"
    f"易林 heuristic 覆蓋目前為 {yilin_audit['match_ratio']:.1%}，同樣只代表檢索覆蓋。"
)

st.markdown("### 輔助入口")
x, y = st.columns(2)
with x:
    st.page_link("pages/3_Knowledge_Vault.py", label="📚 搜尋奇門／梅花／六爻／周易／易林／元靈", use_container_width=True)
with y:
    st.page_link("pages/4_AI_Packet.py", label="🤖 查看最新單一 AI 解卦包", use_container_width=True)

st.divider()
st.caption("JARVIS 負責事件對齊、盤、原典審查與知識；ChatGPT 負責解。古籍、注解、專案 heuristic 與足球 modern application 嚴格分層。")
