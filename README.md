# JARVIS 術數 AI — Operation STARK

**JARVIS 10.2 · Deep Divination Review**：JARVIS 負責事件時間、奇門起局、梅花起卦、古籍／知識檢索、來源審查、矛盾與不確定性整理；最後術數綜合判讀交給 ChatGPT。

> **奇門多層合參 × 梅花定結構 × 周易依方法決定權重 × 易林補轉變情境 × ChatGPT 最終解讀**

JARVIS 不自動把任何單一門、星、神、卦、爻或林辭換成勝率、固定比分或必然賽果。足球欄位屬 `modern application`，必須保留 source basis、observable 與 counter-signal。

## 足球 Case 工作流

```text
MATCH_EVENT_V1
同一事件所在地 aware local datetime + IANA timezone
        ↓
┌───────────────────────┬────────────────────────┐
│ Qimen Packet          │ Meihua Packet          │
│ RESULT_ENGINE_INPUT   │ STRUCTURE_STRESS_TEST  │
└───────────────────────┴────────────────────────┘
        ↓
DIVINATION_CASE_BUNDLE_V1
same-event alignment + packet SHA audit
        ↓
ChatGPT FINAL_SYNTHESIS
```

`pages/5_Football_Case.py` 可一次輸入主客隊、賽事／階段／球場、事件時間與 IANA timezone，同時建立奇門與梅花 packet；兩份 packet 只有在主客、事件時間與 timezone 完全一致時才能組成 Case Bundle。

- **奇門 = `RESULT_ENGINE_INPUT`**：提供主客用神與完整盤局，交由 ChatGPT 判斷正規時間勝負及有限比分候選；JARVIS 本身不下結果。
- **梅花 = `STRUCTURE_STRESS_TEST`**：讀開局／中段／終局、體用、旺衰、體互／用互、變卦、動爻、周易、易林與時間交界；不另產生第二套比分和奇門投票。
- **ChatGPT = `FINAL_SYNTHESIS`**：保留支持、反證、矛盾與未知後再作最後解讀。

## 時間精準度

Runtime：`streamlit==1.61.0`、`lunar_python==1.4.8`、`tzdata==2026.3`。

- 事件時間支援秒級輸入。
- 使用 IANA timezone，不只存 EST / EDT / CDT 等縮寫。
- DST ambiguous local time 必須明確選 `fold=0` / `fold=1`；nonexistent time 直接拒絕。
- 梅花足球 wall-clock audit 可選 120 / 150 / 180 / 210 分鐘，預設 180。
- 偵測 `HOUR_BRANCH_CHANGE`、`CIVIL_DATE_CHANGE`、`LUNAR_DATE_CHANGE`、`UTC_OFFSET_CHANGE`。
- kickoff anchor cast 永遠不變；交界 diagnostic recast 只屬 `SECONDARY_DIAGNOSTIC_ONLY`，**跨時辰不等於必然逆轉**。
- 可選 timestamped match-clock events；wall-clock 不得冒充官方比賽分鐘。

## 奇門遁甲

正式引擎鎖定：**時家奇門・轉盤・拆補法・事件所在地民用時・晚子時換日・中五寄坤二・天禽隨天芮・八神同名制。**

### Core 306 Matrix

- 81 天地盤干
- 72 星 × 門
- 72 門 × 宮
- 81 星 × 宮

`Core 306` 只指這四族，不宣稱等於所有奇門交互。

### Extended Review 378

10.2 另外 materialize：

- 64 神 × 門
- 72 神 × 星
- 72 神 × 宮
- 80 十天干 × 八門
- 90 十天干 × 九星

共 **378 個靜態 Extended Relations**；旬空、驛馬、伏吟、反吟、門迫、入墓、擊刑等 modifier 仍依實際盤面動態疊加。Authority 固定為 `PROJECT_HEURISTIC__COMPONENTS_SOURCE_BACKED`，不是古籍逐條專名，不得做符號投票、勝率或固定比分。

### Source-derived Qimen golden fixtures

10.2 新增四個可重建 classical method fixtures，來源錨定《遁甲演義》卷二，並依傳世轉布規則人工固定 full-core expected plate：

1. 陽遁四局・乙酉時・天遁例
2. 陰遁六局・庚申時・天遁例
3. 陽遁一局・辛卯時・地遁例
4. 陰遁九局・夏至丙寅時・地遁例

CI 逐宮核對地盤、天盤干、星、門、值符／值使與 source anchor。古籍例沒有完整西曆年份／IANA timezone，且八神名制存在流派差異，因此稱為 **`SOURCE_DERIVED_METHOD_GOLDEN`**，不冒充完整 calendar + timezone + deity 的 end-to-end external certification。

## 梅花易數古法方法審查

目前 production engine 只實作 **年月日時起卦**，分類為 `XIANTIAN_NUMBER_METHOD`。

- 先天數法：體用、旺衰、互變、動靜與內外是主要骨架，《周易》文本為 `SUPPORTING`。
- 後天物卦法：知識層已辨識，但 production engine 尚未假裝實作。
- `體一用百`：不只看一個 body/use relation。
- 正式區分 `body_mutual / use_mutual`，同時保存原始 `mutual_upper / mutual_lower` 供排卦稽核。
- 三要、十應、外應未在占測當時記錄時標為 `NOT_RECORDED`，禁止賽後回填。
- 閏月與日界 convention 顯式版本化。

## 《周易》64 / 384 深層審查

固定來源：`kanripo/KR1a0001`，pinned commit `8284adbf9e3435d713180e24f05bf75f8b7d1d96`。

- 64 / 64 卦
- 384 / 384 標準爻
- 卦辭、彖、大象、逐爻爻辭
- 378 條可直接映射小象；乾卦六小象保留 grouped-source exception
- 乾用九／坤用六另存

10.2 對 **384 / 384** 每一標準爻新增 `meaning_review`：

`classical_text → text_conditions → action_boundary → risk_boundary → turning_point → conditional_outcome_tendency → misread_warnings → ambiguity → football evidence/counter-evidence`

Authority 固定為 `PROJECT_REVIEW__NOT_CLASSICAL_COMMENTARY`；原文仍是第一層證據。

## 《焦氏易林》4096

固定 base corpus：`kanripo/KR3g0029`，pinned commit `764e995ce74aa249081918ca1b0c23bbca62bec8`。

- 64 × 64 = **4096 / 4096** 本→之卦條目
- 保留 raw transcription、卷／頁、source notes、gaiji、source-label anomaly 與 SHA provenance
- 梅花只查 **本卦 → 最終變卦** 作 transformation lens
- 不宣稱等同焦林直日法

`cross_system_coherence` 只有在來源 pair 對齊後才比較周易動爻與易林條目的 project semantic domains；共同 domain 是條件式候選 reinforcement，不是吉凶投票。

## Packet contracts

### `DIVINATION_PACKET_V2`
保存 deterministic chart/hexagram facts、來源審查、method audit、temporal audit、meaning review、Yilin bridge、contradiction register、uncertainty register 與 deterministic SHA-256。

### `DIVINATION_CASE_BUNDLE_V1`
保存同一場足球的 Qimen + Meihua packets，強制驗證 same home/away、same aware event datetime、same IANA timezone、packet SHA integrity 與 deterministic match-event identity。任何不一致都停止合參。

## 驗證

```bash
pip install -r requirements-dev.txt
python tools/import_yilin_kanripo.py
python tools/import_zhouyi_kanripo.py
python tools/validate_zhouyi.py
python tools/validate_zhouyi_semantics.py
python tools/validate_zhouyi_line_meaning_review.py
python tools/validate_divination_review.py
python tools/validate_meihua_classical_method.py
python tools/validate_meihua_temporal_precision.py
python tools/validate_meihua_coherence.py
python tools/validate_qimen_source_golden.py
python tools/validate_qimen_extended_review.py
python tools/validate_qimen_review_gates.py
ruff check .
python -m pytest -q
python tools/validate_knowledge.py
python tools/validate_yilin.py
```

## 完整性邊界

JARVIS 10.2 完成 pinned Zhouyi/Yilin source review、384 爻條件式 review、Meihua method-aware/temporal review、Qimen Core 306 + Extended 378、source-derived Qimen method golden tests，以及 deterministic Case Bundle handoff。

它**不宣稱**所有歷代版本已校勘、所有奇門流派已統一、所有古法起卦法都已實作、Qimen 已完成跨 timezone 的 end-to-end 外部盤認證，或足球預測準確率有所提升。

**JARVIS 負責盤、原典、知識與稽核；ChatGPT 負責最後解局／解卦。**
