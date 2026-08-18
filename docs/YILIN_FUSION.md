# JARVIS 10 — YILIN FUSION

## 產品定位

JARVIS 的梅花易數仍然負責 deterministic 起卦：本卦、互卦、變卦、動爻、體用與旺衰不可被《焦氏易林》改寫。

《焦氏易林》只提供一個額外 transformation lens：

```text
梅花本卦 H0
  ↓
最終變卦 H1
  ↓
查《焦氏易林》H0 之 H1
  ↓
原文 + provenance + project image atoms
  ↓
放入 DIVINATION_PACKET_V1
  ↓
ChatGPT 最後合參
```

## 歷史方法聲明

`MEIHUA_YILIN_BRIDGE` 是 Operation STARK 的跨系統合參層，不宣稱等同焦林直日法，也不宣稱已完整復原《焦氏易林》原始占筮程序。

互卦仍是梅花內部發展層，不會自動再查一次「本→互」或「互→變」並冒充焦林原法。

## 權威順序

1. `MEIHUA_DETERMINISTIC_CHART`
2. `MEIHUA_BODY_USE_STRENGTH_MUTUAL_CHANGED_MOVING_LINE`
3. `JIAOSHI_YILIN_FROM_TO_CLASSICAL_TEXT`
4. `COMMENTARIAL_INTERPRETATION_WHEN_SEPARATELY_SOURCED`
5. `FOOTBALL_MODERN_APPLICATION`
6. `CHATGPT_FINAL_SYNTHESIS`

任何下層都不能靜默改寫上層。

## 4096 catalog

完整目標：

- 64 個本卦
- 每個本卦 64 個之卦
- 總計 4096 unique pair

JARVIS 10 alpha 第一批只 materialize 《易林（四庫全書本）》卷一「乾之第一」64 條。

目前必須公開顯示：

```text
64 / 4096
PARTIAL_BUILD__DO_NOT_CLAIM_4096_COMPLETE
```

缺資料時只回：

```text
SOURCE_PENDING
```

不得讓 AI、程式或模板補寫不存在的林辭。

## 每條資料欄位

每一條原典 record 至少包含：

- `from_number / from_name / from_symbol`
- `to_number / to_name / to_symbol`
- `classical_text`
- `source_id / source_section / source_file`
- `verification_status`
- `variant_status`
- `semantic_status`

未完成版本異文交叉核對時，`variant_status` 必須保持 `PENDING_CROSSCHECK`。

## 易林意象 ontology

`knowledge/yilin/image_ontology.json` 是專案分析層，不是古籍原註。

目前先建立：

- 道路／行進
- 阻滯／不通
- 爭鬥／對抗
- 傷病／疲耗
- 得助／資源
- 失落／無功
- 相從／協作
- 言語／資訊
- 水勢／環境
- 權位／主導
- 回復／轉折
- 門戶／屏障

每個 atom 均保存：

```text
古典抽象語義
↓
足球可能情境
↓
可觀察訊號
↓
反證訊號
```

這一層的 authority 固定標成：

`PROJECT_HEURISTIC__NOT_CLASSICAL_COMMENTARY`

## 足球解讀邊界

JARVIS 可以把林辭意象轉成「可能的足球情境」，例如道路阻滯可對應出球／推進受阻，但不得直接變成：

- 主勝／客勝固定規則
- 勝率百分比
- 固定比分
- 單一林辭決定結果

ChatGPT 必須把它與梅花本卦、體用、旺衰、互卦、動爻、變卦一起合參，並列出支持與反證。

## 完整建構路線

### Phase A — catalog infrastructure

- manifest
- loader / exact lookup
- bridge
- CI validator
- partial-coverage truthfulness

### Phase B — 4096 原文 materialization

以完整 64-entry source block 為最小提交單位；每新增一個本卦就一次加入它的 64 個之卦。

### Phase C — 異文校勘

逐條建立：

- primary transcription
- alternate readings
- edition/source notes
- `CROSSCHECKED` / `VARIANT_RECORDED`

### Phase D — semantic atoms

把 4096 林辭拆成可重用意象原子，避免每條各自任意白話化。

### Phase E — commentary layer

加入後世注解時獨立保存為 `commentary`，不與焦氏易林原文混寫。

### Phase F — AI packet stabilization

等 4096 catalog、異文與 commentary contract 穩定後，再評估從 `DIVINATION_PACKET_V1` 升級為 `DIVINATION_PACKET_V2`。

## 驗證

CI 必須同時執行：

```bash
python -m pytest -q
python tools/validate_knowledge.py
python tools/validate_yilin.py
```

`validate_yilin.py` 會拒絕：

- 重複 pair
- manifest coverage 與實際檔案不一致
- 單一來源卦只匯入部分之卦
- 缺 classical text / provenance / verification status
- 4096 未完成卻宣稱 complete
- 任何把 model probability 或 fixed score 寫進易林古籍 record 的資料
