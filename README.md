# JARVIS 術數 AI — Operation STARK

**JARVIS 10.3 alpha · Yuanling Source Reconstruction**：JARVIS 負責事件時間、奇門起局、梅花起卦、《元靈經》原典／旁證重建、古籍／知識檢索、來源審查、矛盾與不確定性整理；最後術數綜合判讀交給 ChatGPT。

> **奇門多層合參 × 梅花定結構 × 周易依方法決定權重 × 易林補轉變情境 × 元靈演數保持原始資料 × ChatGPT 最終解讀**

JARVIS 不自動把任何單一門、星、神、卦、爻、林辭、數宮或數主換成勝率、固定比分或必然賽果。足球欄位屬 `modern application`，必須保留 source basis、observable 與 counter-signal。

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

## 《元靈經》演數七要 × 日奇門 — 10.3 alpha

10.3 不建立一張混合的「日奇門・演數七要盤」。卷一把 **演數七要、數主吉凶歌訣、日奇門**列成相鄰但獨立條目，因此工程上拆成：

- `yuanling.yanshu_qiyao`：七要 primary review。
- `yuanling.riqimen`：日奇門 source-grounded base。
- `RIQIMEN_QIYAO_EXPERIMENT`：只允許把兩份獨立結果並列保存；不宣稱古籍明文規定兩者必須串接。

### 七要 primary slots

固定保存：

`數宮 → 數主 → 飛星 → 入門 → 直日星 → 日干 → 時支`

目前能由曆法直接確定的 `日干 / 時支` 會寫入；其餘若《元靈經》本法尚未完成 algorithm reconstruction，就保留 `UNRESOLVED_BY_SOURCE_AUDIT`，而不是借用現有時家盤硬補。

### 元靈數術九星與時家九星分離

數術層使用獨立 registry：

`一白 / 二黑 / 三碧 / 四綠 / 五黃 / 六白 / 七赤 / 八白 / 九紫`

並保存 `太乙 / 攝提 / 軒轅 / 招搖 / 天符 / 青龍 / 咸池 / 太陰 / 天乙` 及 `貪狼 / 巨門 / ...` 等別名層。它**不等同**時家奇門的 `天蓬 / 天芮 / 天沖 / ...`。

數術九星五行屬性若用洛書對應，authority 明示為 `LUOSHU_STANDARD__PROJECT_NORMALIZATION`，不冒充《元靈經》逐字原文。

### 旁證 reconstruction 不寫回 primary

10.3 另設 `COLLATERAL_QIMEN_TEXT_RECONSTRUCTION`：

- 《金函玉鏡》九星落局法可 deterministic 重建太乙→天乙日遁九星，並以甲子陽遁／陰遁完整盤作 golden anchors。
- 《奇門寶鑑》洞庭老人捷徑占法提供從日干、時支求候選時宮／數宮，再布日遁九星與八門的旁證步驟。

因此 packet 會顯示：

- `number_palace_candidate`
- `daily_nine_star_chart_candidate`
- `daily_star_at_number_palace_candidate`
- `center_daily_star_candidate`

但這些只屬 **candidate**，不會自動填入七要 primary slots。尤其：

- 候選數宮 ≠ 球數；
- 數宮上的日遁星 ≠ 已證成的數主；
- 中宮日遁星 ≠ 已證成的直日星。

### 異文／跨文本差異

JARVIS 明確保留：

- 《元靈經》：`四曰入門`；《奇門寶鑑》旁證：`四曰八門`。
- 《元靈經》黑星例：`數在乾宮`；《奇門寶鑑》旁證：`數在坤宮`。

不因旁證較完整就靜默改正文。

### 日奇門目前完成度

已 machine-reconstruct 並 exact-test 六十日「某宮起休」表，以及：

- 事件節氣／三元；
- 陰陽遁與局數；
- 地盤奇儀；
- 日旬頭。

`值符之上星加本日干穿宮數去` 的完整天盤機械步驟仍標為 unresolved，因此 status 是：

`PARTIAL_SOURCE_GROUNDED__HEAVEN_PLATE_PENDING`

### Yuanling Packet

`YUANLING_YANSHU_PACKET_V1` 保存 source tier、七要 slots、numeric-star registry、旁證 reconstruction、optional Ri-Qimen base、uncertainty 與 deterministic SHA。

硬性邊界：

- `raw_numeric_candidates = []`
- `score_synthesis = DEFERRED_UNTIL_BLIND_TEST_PROTOCOL`
- 禁止 `數宮3 → 3球`
- 禁止自動勝率／固定比分
- 禁止賽後 fitting
- 禁止旁證候選升格成原典事實

研究 UI：`/yuanling`。

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

### `YUANLING_YANSHU_PACKET_V1`
保存元靈演數研究資料；目前獨立於 football Case Bundle，不參與自動比分 synthesis。

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
python tools/validate_yuanling.py
ruff check .
python -m pytest -q
python tools/validate_knowledge.py
python tools/validate_yilin.py
```

## 完整性邊界

JARVIS 10.2 完成 pinned Zhouyi/Yilin source review、384 爻條件式 review、Meihua method-aware/temporal review、Qimen Core 306 + Extended 378、source-derived Qimen method golden tests，以及 deterministic Case Bundle handoff。

JARVIS 10.3 alpha 進一步建立《元靈經》演數七要／日奇門的**獨立、可稽核研究層**，並加入旁證 reconstruction；但它尚未宣稱數主／飛星／直日星之間的完整關係或日奇門 `穿宮數去` 已 source-lock。

本專案**不宣稱**所有歷代版本已校勘、所有奇門流派已統一、所有古法起卦／演數法都已實作、Qimen 已完成跨 timezone 的 end-to-end 外部盤認證，或足球預測準確率有所提升。

**JARVIS 負責盤、原典、知識與稽核；ChatGPT 負責最後解局／解卦。**
