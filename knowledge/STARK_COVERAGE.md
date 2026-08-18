# Operation STARK knowledge coverage

## 「完整」的定義

Operation STARK 不把「有一個 catalog」誇大成「所有歷代術數研究都完成」。每一層只在可驗證的範圍內宣稱完整。

### 奇門遁甲

奇門盤是事件時間、陰陽遁、局數、九宮、天地盤、門、星、神、空馬與格局的動態組合，因此不存在一個像《周易》64 卦那樣有限的「全部奇門卦象清單」。目前完整性分成：

1. **基礎語彙**：9 九宮、8 八門、9 九星、8 八神、10 天干與核心曆法／局法。
2. **Core 306 Matrix**：81 天地盤干 + 72 星門 + 72 門宮 + 81 星宮，四類共 306 槽位；每格都有關係、一般解析、足球 modern application、observable 與 counter-signal。
3. **動態盤面**：每次只把實際命中的宮、門、星、神、干、Core 306 子集、空馬與格局交給 ChatGPT。

**Core 306 不等於所有奇門組合。** 神×門、神×星、神×宮、干×門等屬 Extended Relations 後續工程；未完成前不宣稱全矩陣。

### 梅花易數

固定結構目前覆蓋：

- 8 / 8 八卦。
- 64 / 64 六十四卦 catalog，1–64 無缺號，8×8 上下卦恰好覆蓋一次。
- 5 / 5 體用關係。
- 旺／平／衰。
- 6 / 6 爻位階段。
- 本卦／互卦／變卦與上下卦內外、五行互動。
- 正式引擎目前只實作**年月日時起卦**；其他梅花起卦法不是「已實作」。

### 《周易》原典來源層

JARVIS 10.1 以 pinned `kanripo/KR1a0001` 作一個固定、可重建的數位底本：

- **64 / 64 卦**。
- **384 / 384 標準爻**。
- 卦辭、彖、大象。
- 逐爻爻辭。
- 可直接映射的小象逐爻保存；乾卦底本把大象與六小象集中在一個 block，因此保留 grouped-source exception，不假裝無爭議切分。
- 乾／坤的用九／用六另存。
- 每筆有 source file、page、pinned commit、source SHA。

「64/384 完整」只代表**固定底本資料槽位與來源鏈完整**；不代表所有異文、版本、標點、十翼研究或歷代注家全部校勘完成。

### 《焦氏易林》

固定 WYG base transcription 覆蓋：

- 64 / 64 本卦 blocks。
- 4096 / 4096 本卦→之卦 pair。
- 每條林辭有來源卷／頁、raw transcription、校語、gaiji、source-label anomaly 與 pinned commit。

4096 完整同樣只代表 pair matrix / base transcription / source locator 完整。多版本異文、句讀、後世注解另層處理。

## 「完整解析」的組合方式

梅花不把固定判語複製 384 次，而由 JARVIS 組合：

```text
周易本卦卦辭 / 彖 / 大象
→ 上下卦內外
→ 體用 / 旺衰
→ 互卦原典與中段機制
→ 真正動爻爻辭 / 可用小象 / 爻位階段
→ 變卦原典與後段結構
→ 焦氏易林本卦→變卦
→ 足球候選情境 / observable / counter-signal
→ ChatGPT 合參
```

原典若與 project heuristic 不一致，以來源分層明示，不把矛盾刪掉。

## 足球語義邊界

足球含意是現代應用，不是古籍足球公式，也不是統計模型。資料庫禁止：

- 生門 = 主勝 X%
- 克體 = 客勝 X%
- 某卦／某爻 = 固定賽果
- 某林辭 = 固定比分
- 吉／凶 = 統計機率

只保存候選情境、來源依據、observable、counter-signal 與不確定性。最後判讀由 `DIVINATION_PACKET_V2` 交給 ChatGPT。