# Operation STARK 術數知識庫

本目錄只服務 JARVIS 起局／起卦與 AI handoff。所有內容分成：**古籍數位轉錄／傳統義理、JARVIS 專案結構化解析、足球 modern application**；不得互相冒充。

## 奇門遁甲

- `entities.json`：九宮、八門、九星、八神、十天干。
- `calendar.json`：節氣、十八局、地支、驛馬、五行。
- `patterns.json`：奇儀格、三遁、三詐、五假、庚格、伏吟反吟、刑墓迫等。
- `methods.json`：流派差異；只有明示 `implemented` 的固定版本進入引擎。
- `qimen_deep_layers.json` / `interpretation.json`：深層閱讀與稽核規約。
- `football_ontology.json`：足球候選情境、observable、counter-signal。

`jarvis/qimen_relations.py` 的 **Core 306 Matrix** = 81 天地盤干 + 72 星門 + 72 門宮 + 81 星宮。它是四類核心矩陣，不宣稱等於奇門所有可能組合。

## 梅花易數

- `meihua_trigrams.json`：八卦數、五行、方位、萬物類象與足球現代應用。
- `meihua_hexagrams.json`：64 卦 catalog 與專案摘要。
- `meihua_rules.json`：年月日時起卦、體用五關係。
- `meihua_line_roles.json`：六個爻位階段。
- `meihua_deep_layers.json`：本／互／變、上下卦、旺衰與足球深讀。

## 《周易》原典審查

`zhouyi/` 是 JARVIS 10.1 新增的固定來源層：

- `entries/01..08.json`：8 個 shard，共 **64/64 卦、384/384 標準爻**。
- 每卦保存卦辭、彖、大象、六爻爻辭、來源 file/page/commit/SHA。
- 可直接映射的小象逐爻保存；乾卦此底本的六小象與大象集中於同一 block，保留來源結構與 review status，不強行猜切。
- `manifest.json`：固定來源與 completeness contract。
- `zhouyi_review_policy.json`：文本真實性、卦體、動爻、體用旺衰、本互變、易林一致／矛盾與足球轉譯的審查順序。

固定底本：`kanripo/KR1a0001 @ 8284adbf9e3435d713180e24f05bf75f8b7d1d96`。這是數位轉錄與結構化來源層，不等於所有歷代版本校勘完成。

## 《焦氏易林》

`yilin/entries/01..64.json` 保存完整 **4096/4096** 本卦→之卦 base transcription，並保留 raw text、校語、gaiji、來源標籤 anomaly 與 pinned provenance。

`yilin/image_ontology.json` 是 JARVIS 的 project heuristic；只把具體意象召回成候選現代情境，不能冒充焦氏原註。

梅花 bridge 只查：

```text
本卦 → 最終變卦
```

不把互卦冒充焦林原始占法，也不重起一套卦。

## AI handoff

`DIVINATION_PACKET_V2` 的梅花包固定包含：

```text
梅花 deterministic snapshot
+ 周易 source audit
+ 本／互／變卦辭、彖、大象
+ 真正動爻爻辭／可用小象
+ 體用、旺衰與深層結構
+ 唯一焦氏易林本→變
+ project heuristic / football observable / counter-signal
```

JARVIS 到此為止；最後判讀交給 ChatGPT。

足球欄位一律是 `modern application`，禁止自動轉成主勝／和局／客勝、統計勝率或固定比分。