# JARVIS 10.3 — 《元靈經》資料庫與起局／演數指南

## 名稱先分清

- **時家奇門**：起局／排盤。
- **梅花易數**：起卦。
- **《元靈經》演數七要**：演數審查，不是六爻起卦。
- **《元靈經》日奇門**：另起日奇門研究盤。
- **《元靈經》卷一奇門起例**：原典起局參考，用來校核方法，不另開第二套 production 時家引擎。

任何模組都不得把單一宮數、星數、門、干直接換成足球比分或機率。

## 擴充後資料庫

### Core source catalog：18 條

既有 `knowledge/yuanling_source_catalog.json` 保留卷一核心方法與卷三數術資料，包括：

- 奇門起例、陰陽遁、二十四節氣三元局表、三元符頭；
- 三奇、六儀、一般奇門九星、奇儀順逆、值符、值使；
- 定用神、伏身、先天定六親；
- 演數七要、數主吉凶歌訣、日奇門；
- 卷三中宮值日九星、射覆數目關聯。

### Extended source catalog：9 條

`knowledge/yuanling_extended_source_catalog.json` 新增：

1. 卷一截路空亡；
2. 卷一八卦源流；
3. 卷二八門值事；
4. 卷二九宮值符值使；
5. 卷二十干吉凶宜忌；
6. 卷二九遁與詐假；
7. 卷二天盤加地盤吉凶章節索引；
8. 卷三奇門捷徑秘法；
9. 卷三九星克應訣。

Core 18 + Extended 9 = **27 個結構化 source sections**。

其中卷二「天盤加地盤吉凶」目前只做到章節索引與少量 source anchors；不得把既有 Qimen Core 306 的 81 干對關係冒充這一章的完整逐條古文 corpus。

### 二十四卷工作索引

`knowledge/yuanling_work_index.json` 把傳世目錄卷一至卷二十四全部索引。

- 卷一至卷三：方法與數術優先結構化。
- 卷二十三：射覆數目已有部分數術關聯使用。
- 卷二十四：含「占勝敗」，標成競爭／勝負研究的高優先 future source review。
- 其餘章目只標 `INDEXED_NOT_MATERIALIZED`，不能因為已列章名就宣稱規則已入庫。

## 一、Production 時家奇門怎麼起局

Method：`QIMEN_SHIJIA_ZHUANPAN_CHAIBU`

必要輸入：

- 比賽所在地 aware local datetime；
- IANA timezone；
- 主隊、客隊；
- 占問問題。

JARVIS 流程：

1. 由事件所在地時間取得節氣與四柱；
2. 判陰遁／陽遁；
3. 由符頭判上、中、下元；
4. 依二十四節氣三元表定局；
5. 布地盤三奇六儀；
6. 判時旬與旬首儀；
7. 定值符、值使與落宮；
8. 轉布天盤干、九星、八門、八神；
9. 疊加旬空、驛馬、伏吟、反吟、門迫、入墓、擊刑等；
10. 足球主隊取日干、客隊取時干；甲取值符宮；
11. JARVIS 打包全盤，ChatGPT 才做最後結果判讀。

《元靈經》卷一「奇門起例」另作 source crosscheck：先分陰陽、詳節氣、察符頭、布儀奇得地盤，再以符頭加用時干、定值符與值使而成天盤。原文有陽遁九局與陰遁八局兩個例盤。

## 二、梅花年月日時先天數法怎麼起卦

Method：`MEIHUA_YEAR_MONTH_DAY_HOUR`

令：

- `Y` = 農曆年支數；
- `M` = 農曆月數；
- `D` = 農曆日數；
- `H` = 時支數。

公式：

1. `A = Y + M + D`；`A mod 8` 定上卦，餘 0 作 8；
2. `B = Y + M + D + H`；`B mod 8` 定下卦，餘 0 作 8；
3. `B mod 6` 定動爻，餘 0 作 6；
4. 動爻所在的單卦為用，另一單卦為體；
5. 2–4 爻、3–5 爻取互卦，並依體的位置標 `body_mutual / use_mutual`；
6. 翻動真正動爻得變卦；
7. 再看體旺衰、本用、體互、用互、變用；
8. 年月日時屬先天數法，因此《周易》動爻文本為 supporting review；
9. 《焦氏易林》只查本卦 → 最終變卦作 transformation lens；
10. 足球跨時辰只作 secondary temporal checkpoint，不替換 kickoff anchor cast。

## 三、《元靈經》演數七要怎麼做

Method：`YUANLING_YANSHU_QIYAO_RAW`

原典固定七要：

`數宮 → 數主 → 飛星 → 入門 → 直日星 → 日干 → 時支`

原文重點是先看「遁至本時之星」的數主，尤其數主落宮，再合看本宮所臨之星、門宮、直日星、日干、時支。

### 現在能 deterministic 的 primary facts

- event-local calendar；
- 節氣；
- 日干支、時干支；
- 陰陽遁；
- 日干；
- 時支；
- 一白至九紫獨立數術星 registry。

### 還不能假裝已解的 primary facts

- 數宮完整原法；
- 數主「遁至本時之星」完整飛遁起點、順逆、序列；
- 飛星與數主的機械關係；
- 入門完整算法；
- 直日星與卷三值日星系統的精確接口。

所以沒有可靠 source-lock 時，這些欄位維持 `UNRESOLVED_BY_SOURCE_AUDIT`。

### 新增 source context 怎麼用

- 卷二八門值事：補「門」的條件式古典語境；
- 卷二十干宜忌：補日干／時干的 source context；
- 卷三奇門捷徑秘法：補數術星與門同見時的條件；
- 卷三九星克應：補太乙至天乙在相生相剋情境下的語義；
- 同一顆數術星在不同章節可能有不同語境，不壓成單一 good/bad label。

旁證《奇門寶鑑》《金函玉鏡》仍只產 candidate，不自動寫回 primary 七要。

## 四、《元靈經》日奇門怎麼起

Method：`YUANLING_RI_QIMEN`

目前 source-lock：

1. 依節氣三元定局作地盤；
2. 由本日干支取日旬與本甲旬頭；
3. 按六十日表取得「某宮起休」；
4. 本甲旬頭即值符；
5. 保存「陰遁奇直皆逆，星門皆順」；
6. 卷一截路空亡另作獨立 source context：甲己申酉、乙庚午未、丙辛辰巳、丁壬寅卯、戊癸子丑。

尚未 source-lock：

`值符之上星加本日干穿宮數去`

所以 current output 仍是 partial base，不是假裝完整天盤。

## 五、三個元靈方法的關係

```text
卷一一般奇門起例
        │
        └─ source method crosscheck

演數七要 QIYAO_RAW ──────────┐
                              ├─ RIQIMEN_QIYAO_EXPERIMENT
日奇門 Source-grounded Base ──┘
```

上圖的實驗橋只表示 packet 可以 sibling 並列兩份資料，**不表示古籍明文規定七要必須建立在日奇門盤上**。

## 足球使用邊界

- Qimen production packet：可交給 ChatGPT 作 RESULT ENGINE。
- Meihua packet：作 STRUCTURE / STRESS TEST，不再另報第二套比分。
- Yuanling packet：只補數術原始資料與 source context。
- `數宮 3`、`三碧`、射覆數目 3 都不能自動解成「3 球」。
- 在 primary 算法未 source-lock、且沒有預先註冊的 blind-test protocol 前，`score_synthesis` 維持 deferred。
