# JARVIS 10 — YILIN FUSION

## 核心原則

> **梅花定結構 × 易林補劇情 × ChatGPT 合參**

JARVIS 的梅花易數仍然是 deterministic 起卦權威。本卦、互卦、變卦、動爻、體用與旺衰不能被《焦氏易林》改寫。

《焦氏易林》只增加 transformation lens：

```text
梅花本卦 H0
  ↓
最終變卦 H1
  ↓
查《焦氏易林》H0 之 H1
  ↓
林辭 + provenance + source apparatus
  ↓
project semantic profile / image ontology
  ↓
DIVINATION_PACKET_V1
  ↓
ChatGPT 最後合參
```

## 歷史方法聲明

`MEIHUA_YILIN_BRIDGE` 是 Operation STARK 的跨系統合參層：

- 不宣稱等同焦林直日法。
- 不宣稱完整復原《焦氏易林》原始占筮程序。
- 不拿互卦再查一套焦林並冒充原法。
- 不重新起卦。
- 不把林辭直接換成吉凶、勝率或固定比分。

## 4096 / 4096 corpus

JARVIS 10 的本地易林 base corpus 現在是：

- 64 個本卦
- 每個本卦 64 個之卦
- **4096 / 4096 unique pair**
- **64 / 64 source blocks**
- 每條非空林辭
- 每條保存 source page locator
- 每條保存 raw transcription
- 括號校語分離保存
- gaiji token 原樣保存，不擅自猜字
- source label 與預期位置不一致時登錄 anomaly，不靜默改寫

主要 base transcription：

```text
repository: kanripo/KR3g0029
edition: WYG / 文淵閣四庫全書
pinned commit: 764e995ce74aa249081918ca1b0c23bbca62bec8
source files: KR3g0029_001.txt ... KR3g0029_004.txt
```

來源 snapshot 與 SHA-256 固定在：

- `knowledge/yilin/source_snapshot.json`
- `knowledge/yilin/manifest.json`

完整 64 blocks 存於：

- `knowledge/yilin/entries/01.json` … `64.json`

## 「完整」的精確定義

JARVIS 10 可以宣稱：

- 64×64 pair matrix 完整
- WYG base digital transcription 完整
- source-page provenance 完整
- raw transcription preservation 完整
- 現有 WYG source-label anomaly registry 完整

JARVIS 10 **不宣稱**：

- 所有版本異文都已校勘完畢
- 所有句讀／現代標點都已校定
- 所有歷代注解都已收完
- project heuristic 等於焦氏原註
- 足球類比已被證明具有預測準確率

這些維度記錄在 `knowledge/yilin/collation_status.json`。

## Source order 與卦名異體

傳世數位轉錄的每一個 source block 採：

```text
本卦自身
→
其餘六十三卦依文王卦序
```

因此 runtime lookup 用 **King Wen number pair** 做權威鍵，不依賴來源字形。

例如來源可能使用：

- 无 / 無
- 恒 / 恆
- 兊 / 兑 / 兌
- 㢲 / 巽
- 暌 / 睽

這些原 source label 仍保存。

目前 pinned WYG transcription 檢出 1 個 source-target label anomaly：艮 block 的 target #9 位置標成「小過」。JARVIS 保存原標籤與 anomaly flag，但 lookup pair 仍依 source order 對應 `艮之小畜`，避免靜默篡改原文，也避免 matrix 錯位。

## 每條 record

每條至少保存：

```text
id
from_number / from_name / from_symbol
to_number / to_name / to_symbol
classical_text
transcription_raw
editorial_notes
gaiji_tokens
source_target_label
source_label_order_anomaly
source_page_start
source_id
source_section
source_edition
source_repo / source_commit
source_volume_file
verification_status
variant_status
semantic_status
```

## 易林意象 ontology

`knowledge/yilin/image_ontology.json` 是 **專案 heuristic**，不是古籍原註。

目前覆蓋移動、渡涉、車馬、阻滯、延遲、開啟、門戶、防守、爭鬥、刑法、隱伏、資訊、協作、離散、婚合、權位、財貨、得失、供給、生長、傷病、康復、轉折、崩解、升進、水火、風雨、幽暗、猛獸、飛鳥、士氣、悲憂、時令、家室、群體等情境領域。

每個 atom 固定保存：

```text
source match terms
→
project classical abstraction
→
football hypotheses
→
observable signals
→
counter signals
```

authority 永遠是：

`PROJECT_HEURISTIC__NOT_CLASSICAL_COMMENTARY`

`jarvis.yilin.yilin_semantic_profile()` 只做候選語義聚合；未命中 ontology 的林辭仍由 ChatGPT 直接閱讀，不能視為「無意義」。

## AI 權威順序

1. `MEIHUA_DETERMINISTIC_CHART`
2. `MEIHUA_BODY_USE_STRENGTH_MUTUAL_CHANGED_MOVING_LINE`
3. `JIAOSHI_YILIN_FROM_TO_CLASSICAL_TEXT`
4. `COMMENTARIAL_INTERPRETATION_WHEN_SEPARATELY_SOURCED`
5. `PROJECT_SEMANTIC_HEURISTIC`
6. `FOOTBALL_MODERN_APPLICATION`
7. `CHATGPT_FINAL_SYNTHESIS`

下層不能靜默改寫上層。

## 足球解讀協議

林辭進入足球問題時，必須經過：

```text
林辭原文
↓
候選古典抽象語義
↓
足球 modern application
↓
場上可觀察證據
↓
反證
↓
與梅花核心合參
```

禁止：

- 林辭 A = 主勝
- 意象 B = 客勝
- 某字 = 固定比分
- 用單一林辭產生統計勝率
- 把 heuristic 當古籍原註

## 多版本校勘與 commentary

WYG base 完整後，下一個文本工作是逐條 crosscheck：

- Wikisource《易林（四庫全書本）》
- Chinese Text Project《焦氏易林》
- 後續可合法、可驗證取得的其他底本

異文必須以 alternate reading / source note 方式保存，不能覆蓋 base transcription。

後世注解另建 commentary layer；作者、版本、來源與權利狀態必須明確，不與焦氏林辭混寫。

## Reproducible importer

`tools/import_yilin_kanripo.py` 可從 pinned upstream commit 重新 materialize 4096 corpus。Importer 會拒絕：

- 不是 64 個 source blocks
- block 不是完整 64 target
- 空白林辭
- 缺 source page

它不使用 AI 生成或補寫任何古籍文字。

## 驗證

正式 CI：

```bash
ruff check .
python -m pytest -q
python tools/validate_knowledge.py
python tools/validate_yilin.py
```

`validate_yilin.py` 嚴格驗證：

- exact 64×64 numeric matrix
- 4096 unique name/numeric pair
- 64/64 source blocks
- non-empty classical text
- full provenance / pinned upstream commit
- source snapshot / SHA-256
- raw transcription / editorial notes / gaiji preservation
- anomaly registry consistency
- ontology fields / unique IDs
- semantic audit accounting
- 無 probability / fixed-score 污染

最終產品邊界不變：**JARVIS 負責起卦、查庫、保存來源與打包；ChatGPT 負責最後解卦。**
