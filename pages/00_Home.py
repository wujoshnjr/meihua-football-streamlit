from __future__ import annotations

import streamlit as st

from jarvis.stark_vault import vault_stats
from jarvis.yilin import yilin_catalog_stats, yilin_semantic_audit
from jarvis.zhouyi import zhouyi_catalog_stats
from version import __version__


st.set_page_config(page_title="JARVIS 術數 AI", page_icon="☯️", layout="wide")
st.title("JARVIS 術數 AI")
st.caption(f"Operation STARK｜v{__version__}｜JARVIS 起局／起卦、原典審查與知識整理，ChatGPT 負責最後解讀")

st.success(
    "核心：奇門遁甲知識庫 × 梅花易數 ×《周易》64卦/384爻原典＋條件式審查 ×《焦氏易林》4096轉卦 × deterministic 起局／起卦 × AI 解卦包。",
    icon="⚡",
)

st.info(
    "《周易》已建立固定 Kanripo 數位底本的 64/64 卦與 384/384 標準爻來源層；"
    "每個標準爻現在另有 source-grounded conditional meaning review，但權威標記仍是 PROJECT_REVIEW__NOT_CLASSICAL_COMMENTARY。"
    "《焦氏易林》完成 WYG base transcription 64×64＝4096/4096；固定底本完整不等於所有歷代版本與注家都已校勘完成。"
)

with st.container(border=True):
    st.markdown("## ⚽ 推薦：足球雙術數案件")
    st.write(
        "同一個 event-local datetime / IANA timezone 一次建立兩份 packet，先做 SHA 與 same-event alignment："
        "**奇門 = RESULT_ENGINE_INPUT**，**梅花 = STRUCTURE_STRESS_TEST**，最後才交給 ChatGPT 合參。"
        "此工作區也提供秒級 kickoff、DST fold、120/150/180/210 分鐘時間審查、Temporal Timeline 與 JSON 重新匯入。"
    )
    st.page_link("pages/5_Football_Case.py", label="建立足球 Case Bundle", icon="⚽", use_container_width=True)

st.markdown(
    """
### 使用方式

1. 足球優先使用 **足球雙術數案件**：同一事件一次建立奇門與梅花，避免兩份 packet 時間／主客不一致。
2. JARVIS 用固定方法計算完整盤／卦，不讓 AI 重新排盤。
3. **奇門**整理主客用神、九宮、門星神、天地盤干、格局、空馬等結果證據；JARVIS 不自動產生勝負或比分。
4. **梅花**先辨起卦法，再讀體用旺衰、體互／用互、變卦、時間邊界；目前年月日時先天數法中《周易》屬 SUPPORTING review。
5. 《周易》真正動爻除原文／小象／semantic profile 外，再附條件、風險、轉折、誤讀警告與 football evidence/counter-evidence。
6. 以唯一的「本卦 → 最終變卦」查《焦氏易林》4096 catalog；易林補轉變情境，不重起另一套卦。
7. 產生 `DIVINATION_PACKET_V2`；足球雙術數再包成 `DIVINATION_CASE_BUNDLE_V1`，先通過 same-event alignment 與 SHA integrity。
8. ChatGPT 最終合參：奇門主結果、梅花做 mechanism / stress test；不是兩套術數各報比分再投票。

**原則：同一事件 → 奇門主結果證據 × 梅花定結構／驗結果 × 周易依方法定權重 × 易林補劇情 × ChatGPT 合參。**
"""
)

left, right = st.columns(2)
with left:
    with st.container(border=True):
        st.markdown("## 🧭 奇門遁甲")
        st.write(
            "時家奇門・轉盤・拆補法。輸出九宮、天地盤、八門、九星、八神、值符值使、旬空、驛馬、格局、"
            "Core 306 關係實際命中內容，以及每宮『宮→門→星→神→天地盤干→格局／空馬』深層解析。"
        )
        st.page_link("pages/1_Qimen_Cast.py", label="單獨奇門起局", icon="🧭", use_container_width=True)
with right:
    with st.container(border=True):
        st.markdown("## ☯️ 梅花 × 周易 × 焦氏易林")
        st.write(
            "年月日時起卦。輸出本卦、體用、旺衰、體互／用互、變卦、動爻；"
            "核對《周易》原典與 384 爻 conditional review，再查唯一『本卦→變卦』易林林辭與情境語義。"
        )
        st.page_link("pages/2_Meihua_Cast.py", label="單獨梅花起卦", icon="☯️", use_container_width=True)

stats = vault_stats()
zhouyi = zhouyi_catalog_stats()
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
b.metric("奇門 Core 關係", stats["qimen_relations"])
c.metric("梅花六十四卦", stats["meihua_hexagrams"])
d.metric("周易原典", f"{zhouyi['materialized_hexagrams']}/64 · {zhouyi['materialized_standard_lines']}/384")

e, f, g, h = st.columns(4)
e.metric("八神深層調制", stats["qimen_deity_modulations"])
f.metric("梅花八卦", stats["meihua_trigrams"])
g.metric("焦氏易林", f"{yilin['materialized_pairs']}/{yilin['expected_pairs']}")
h.metric("易林 heuristic 覆蓋", f"{yilin_audit['match_ratio']:.1%}")
st.caption("周易 64/384 是固定來源文本覆蓋；conditional review 是專案審查物件；易林 heuristic 覆蓋只是語義檢索覆蓋。以上都不是足球預測準確率。")

st.markdown("### 輔助入口")
x, y = st.columns(2)
with x:
    st.page_link("pages/3_Knowledge_Vault.py", label="📚 搜尋奇門／梅花／周易／焦氏易林", use_container_width=True)
with y:
    st.page_link("pages/4_AI_Packet.py", label="🤖 查看最新單一 AI 解卦包", use_container_width=True)

st.divider()
st.caption("JARVIS 負責事件對齊、盤、原典審查與知識；ChatGPT 負責解。古籍、注解、專案 heuristic 與足球 modern application 嚴格分層。")
