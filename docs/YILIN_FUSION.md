# JARVIS 10.1 — ZHOUYI REVIEW × YILIN FUSION

## 核心原則

> **周易核文本 × 梅花定結構 × 易林補劇情 × ChatGPT 合參**

JARVIS 的梅花易數仍然是 deterministic 起卦權威。本卦、互卦、變卦、動爻、體用與旺衰不能被《周易》文本層或《焦氏易林》改寫。

現在的完整順序：

```text
梅花 deterministic snapshot
  ↓
核對《周易》本卦 / 互卦 / 變卦
  ↓
卦辭 + 彖 + 大象 + 真正動爻爻辭 + 可用小象
  ↓
體用 / 旺衰 / 本互變 / 爻位階段
  ↓
查《焦氏易林》本卦 H0 → 最終變卦 H1
  ↓
林辭 + provenance + source apparatus
  ↓
周易 / 易林 project semantic heuristic
  ↓
足球 modern application + observable + counter-signal
  ↓
DIVINATION_PACKET_V2
  ↓
ChatGPT 最後合參
```

## 《周易》source-aware review

固定底本：

```text
repository: kanripo/KR1a0001
pinned commit: 8284adbf9e3435d713180e24f05bf75f8b7d1d96
corpus: 64 / 64 卦
standard lines: 384 / 384
shards: 8 / 8
```

每卦保存：

- 卦序／卦名／卦符／上下卦
- 卦辭
- 彖
- 大象
- 六條標準爻辭
- source file / page / commit / source SHA-256
- 乾、坤的用九／用六

可直接映射的小象逐爻保存。此底本的乾卦把大象與六小象集中在同一個象傳 block，因此 JARVIS 保留六條 `GROUPED_IN_QIAN_XIANG_BLOCK` source exception，不為了追求表面完整而擅自切分假定原文。其餘 378 條小象直接映射。

`knowledge/zhouyi_review_policy.json` 固定八個審查維度：

1. 文本真實性
2. 卦體核心
3. 動爻審查
4. 體用與旺衰
5. 本／互／變時間層
6. 易林一致與矛盾
7. 足球含意轉譯
8. 矛盾與不確定性

## 《周易》語義 ontology

`knowledge/zhouyi_semantic_ontology.json` 只根據實際爻辭／可映射小象中的命中字詞召回候選語義。

它包含兩種專案層：

- judgment markers：吉、利、亨、无咎、凶／厲、悔、吝等，但只作經文字詞審查。
- semantic atoms：前進、等待、渡涉、車馬、阻滯、屏障、領導、協作、離散、爭鬥、紀律、傷損、資源、得失、恢復、過度、節制、孚信、溝通、隱伏、震動、顯現、水險、剝損、增益等。

每個 atom 固定提供：

```text
actual matched terms
→ project abstraction
→ football hypotheses
→ observable signals
→ counter signals
```

其 authority 永遠是：

`PROJECT_HEURISTIC__NOT_CLASSICAL_COMMENTARY`

未命中 ontology 的爻辭仍完整交給 ChatGPT 直接閱讀；JARVIS 不會為了提高 coverage 而捏造古義。

## 《焦氏易林》的歷史方法聲明

`MEIHUA_YILIN_BRIDGE` 是 Operation STARK 的跨系統合參層：

- 不宣稱等同焦林直日法。
- 不宣稱完整復原《焦氏易林》原始占筮程序。
- 不拿互卦再查一套焦林並冒充原法。
- 不重新起卦。
- 不把林辭直接換成吉凶、勝率或固定比分。

## 4096 / 4096 Yilin corpus

JARVIS 10 的本地易林 base corpus：

- 64 個本卦
- 每個本卦 64 個之卦
- **4096 / 4096 unique pair**
- **64 / 64 source blocks**
- 每條非空林辭
- 每條 source page locator / raw transcription
- 括號校語分離
- gaiji token 原樣保存
- source label anomaly 明示

主要 base transcription：

```text
repository: kanripo/KR3g0029
edition: WYG / 文淵閣四庫全書
pinned commit: 764e995ce74aa249081918ca1b0c23bbca62bec8
source files: KR3g0029_001.txt ... KR3g0029_004.txt
```

## 「完整」的精確定義

JARVIS 現在可以宣稱：

- 《周易》固定底本 64/64 卦、384/384 標準爻來源槽位完整
- 378 條小象直接映射 + 乾卦 6 條 grouped-source exception 明示
- 《焦氏易林》64×64 pair matrix 完整
- WYG 易林 base digital transcription 完整
- 周易／易林 source provenance 可重建

JARVIS **不宣稱**：

- 所有歷代版本異文已校勘完畢
- 所有句讀／現代標點已校定
- 所有歷代注解已收完
- project heuristic 等於經傳／焦氏原註
- 足球類比已被證明具有預測準確率

## AI 權威順序

1. `MEIHUA_DETERMINISTIC_CHART`
2. `ZHOUYI_PINNED_CLASSICAL_TEXT`
3. `MEIHUA_BODY_USE_STRENGTH_MUTUAL_CHANGED_MOVING_LINE`
4. `JIAOSHI_YILIN_FROM_TO_CLASSICAL_TEXT`
5. `COMMENTARIAL_INTERPRETATION_WHEN_SEPARATELY_SOURCED`
6. `PROJECT_SEMANTIC_HEURISTIC`
7. `FOOTBALL_MODERN_APPLICATION`
8. `CHATGPT_FINAL_SYNTHESIS`

下層不能靜默改寫上層。

## 足球解讀協議

任何經文／林辭進入足球問題時，都必須經過：

```text
來源原文
↓
結構位置（本互變 / 動爻 / 體用）
↓
候選抽象語義
↓
football modern application
↓
場上 observable
↓
counter-signal
↓
與其他層的支持 / 抵銷 / 矛盾
↓
ChatGPT final synthesis
```

禁止：

- 某卦 = 主勝
- 某爻 = 客勝
- 林辭 A = 固定比分
- 吉／凶字樣 = 統計勝率
- heuristic 冒充古籍原註
- 賽後事件回寫成賽前卦義

## Reproducible importers

```text
tools/import_zhouyi_kanripo.py
tools/validate_zhouyi.py
tools/validate_zhouyi_semantics.py

tools/import_yilin_kanripo.py
tools/validate_yilin.py
```

正式 CI 會重新生成兩套 pinned corpus，要求 committed files zero-diff，再跑 textual、semantic、packet schema 與知識庫 tests。

最終產品邊界不變：**JARVIS 負責起卦、核原典、查庫、保存來源與打包；ChatGPT 負責最後解卦。**
