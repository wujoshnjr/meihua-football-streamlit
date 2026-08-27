# JARVIS 六爻納甲子系統 — System Design

Status: 10.5.0-alpha.1 candidate  
Core method ID: `JARVIS_LIUYAO_NAJIA_V1`  
Packet: `LIUYAO_PACKET_V1`

## 1. 目標

本子系統在既有 JARVIS 內提供一套獨立、可稽核、source-aware 的六爻／文王卦／納甲工作流。

它的責任是：

1. 接收真實六次起卦結果；
2. 正確排出本卦與變卦；
3. 裝納甲、八宮、世應、六親、六神；
4. 固定月建、日辰、旬空與動變直接關係；
5. 將用神、旺衰、空破、暗動、伏神、進退、沖合等拆成可追蹤 review；
6. 保留古籍規則、現代師承與 JARVIS adaptation 的 authority 差別；
7. 打包給 ChatGPT 做最後斷卦，而不是在 engine 內以符號投票自動下吉凶。

它不是「看到卦名就給答案」的程式。

## 2. Authority order

### A. Primary / classical anchors

- 《增刪卜易》
- 《卜筮正宗》
- 《火珠林》
- 《黃金策》

其中：

- 《增刪卜易》作主要實作基準：納甲、六親、動變、用神、元忌仇、日月、暗動、空破、伏神、進退等；
- 《卜筮正宗》交叉核對世應、六神與裝卦；
- 《火珠林》保留較早的六親／飛伏／征戰脈絡；
- 《黃金策》提供月建日辰、世應、用神等綱領交叉核對。

### B. Modern teaching

現代影片與課程只用於：

- 發現常見斷卦流程；
- 找候選技巧；
- 找可能漏掉的章節。

它們不單獨覆蓋古籍 deterministic rule。

### C. 使用者指定影片

影片：

`https://youtu.be/-qgDHCHaDpo`

目前搜尋／抓取介面未返回可核對的標題、字幕或逐字稿，因此狀態固定：

`PENDING_TRANSCRIPT__NOT_SOURCE_LOCKED`

在取得實際 transcript 前：

- 不猜作者說了什麼；
- 不把任何推測寫進 core；
- 不聲稱影片支持某條規則。

來源狀態存於 `knowledge/liuyao_sources.json`。

## 3. 起卦輸入

### V1 accepted input

六次爻值，固定順序：

`初爻 → 二爻 → 三爻 → 四爻 → 五爻 → 上爻`

數值：

- 6 = 老陰，動，變陽；
- 7 = 少陽，靜；
- 8 = 少陰，靜；
- 9 = 老陽，動，變陰。

JARVIS 直接收 6/7/8/9，而不是要求「字／背／正／反」。

原因：不同錢幣與現代教學對正反面的命名可能不同；六爻真正需要的是已確定的老少陰陽值。這能避免 UI 語義造成的換算錯誤。

### 不做的事

- 不提供會偷偷改變分布的隨機起卦；
- 不按時間自動生成六爻並冒充擲錢；
- 不看題目內容 hash 出六爻並稱古法。

若未來新增電子 random cast，必須另立 method ID、明示 RNG 與分布，不與 physical coin input 混名。

## 4. Calendar convention

六爻需要月建、日辰、旬空與六神日干。

V1 共用 JARVIS 已經驗證的 event-local time infrastructure：

- IANA timezone；
- 秒級時間；
- DST nonexistent time 拒絕；
- DST ambiguous time 必須選 fold；
- 月柱依節氣；
- 日柱依目前 JARVIS event-local civil convention；
- 旬空由六十甲子計算。

這是明示的 project calendar convention，不宣稱所有六爻流派的子初／子正換日都已統一。

若日界 convention 要比較，必須提升 method version。

## 5. Deterministic core

檔案：

- `liuyao/constants.py`
- `liuyao/models.py`
- `liuyao/engine.py`

### 5.1 本卦／變卦

先由 6/7/8/9 轉成六條陰陽。

只有 6、9 變。

### 5.2 八宮

64 卦完整映射到：

- 乾
- 震
- 坎
- 艮
- 坤
- 巽
- 離
- 兌

每宮八卦固定：

`本宮 → 一世 → 二世 → 三世 → 四世 → 五世 → 遊魂 → 歸魂`

### 5.3 世應

世位：

`6, 1, 2, 3, 4, 5, 4, 3`

對應上述八個階段。

應位與世相隔三爻。

### 5.4 納甲

八卦內外卦干支分開保存。

例如乾：

- 內：甲子、甲寅、甲辰
- 外：壬午、壬申、壬戌

完整八卦表已寫入 constants 並有 64 卦 coverage test。

### 5.5 六親

以**正卦所屬卦宮五行**為「我」。

推：

- 父母
- 兄弟
- 官鬼
- 妻財
- 子孫

重要 hard rule：

> 動爻變出的爻，其六親仍照正卦卦宮五行推，不因變卦另屬他宮而重算。

這一點用《增刪卜易》「水天需→天水訟」例作 golden fixture。

### 5.6 六神

依日干起初爻：

- 甲乙：青龍
- 丙丁：朱雀
- 戊：勾陳
- 己：螣蛇
- 庚辛：白虎
- 壬癸：玄武

由初爻順排至上爻。

六神是附合象意，不是獨立吉凶投票器。

### 5.7 旬空

由日柱所在旬直接取得兩空支。

空亡只作結構事實；空、動、沖、填實等必須合參。

### 5.8 月建／日辰 direct relations

逐爻記錄：

- 臨月建
- 月破
- 月合
- 臨日辰
- 日沖
- 日合
- 五行生克方向

不把它們壓成任意數字分數。

### 5.9 動變

每一明動爻保存：

- 原爻納甲／六親；
- 變爻納甲／六親；
- 回頭生；
- 回頭克；
- 原爻生變；
- 原爻克變；
- 化合；
- 回頭沖；
- 化進神；
- 化退神。

### 5.10 伏神候選

若本卦六爻沒有所需六親，回到該卦所屬八宮的純卦，取同位六親作伏神候選。

「候選」不是「必然有用」。

飛神生克、日月扶抑、空破、得出不得出仍須 review。

## 6. Source-aware review layer

檔案：

`liuyao/review.py`

### 6.1 Question role

已 source-reviewed 的基本題型：

- SELF → 世爻
- OTHER_PERSON → 應爻
- WEALTH → 妻財
- CAREER_OFFICE → 官鬼
- DOCUMENT_CONTRACT → 父母
- CHILDREN_MEDICINE_RELIEF → 子孫
- SIBLINGS_PEERS → 兄弟

題型超出 catalog 時：

`QUESTION_CATEGORY_UNMAPPED`

而不是靠 AI 關鍵字硬猜。

### 6.2 多重用神

同一六親若多現：

`MULTIPLE_USE_CANDIDATES__DO_NOT_PICK_BY_OUTCOME`

不能因知道結果才選其中一爻。

後續應按：

- 月建／日辰
- 旺相休囚
- 動靜
- 空破
- 生扶克制
- 題意

再判。

### 6.3 元神／忌神／仇神

對指定用神五行：

- 元神 = 生用神者；
- 忌神 = 克用神者；
- 仇神 = 克元神且生忌神者。

JARVIS 會列出現卦中符合的爻位。

但「存在」不等於「有力」。

### 6.4 暗動 firewall

日沖靜爻只標：

`暗動／日破待旺衰判別`

不允許：

`日沖靜爻 = 一律暗動`

因為《增刪卜易》本身依旺相有氣／休囚無氣區別。

### 6.5 月破／旬空／動爻 coexistence

若同一爻：

- 月破又動；
- 旬空又動；
- 日沖又得月生；

這些訊號全部保存。

不採「一個凶符號抵消整爻」的簡化法。

## 7. Advanced classical topics — coverage matrix

| Topic | 10.5 alpha status | Rule |
|---|---|---|
| 納甲 | IMPLEMENTED | deterministic |
| 八宮 | IMPLEMENTED | deterministic |
| 世應 | IMPLEMENTED | deterministic |
| 六親 | IMPLEMENTED | deterministic |
| 六神 | IMPLEMENTED | deterministic accessory |
| 月建／日辰 | IMPLEMENTED | direct relations |
| 旬空 | IMPLEMENTED | structural fact |
| 動變 | IMPLEMENTED | deterministic |
| 回頭生克 | IMPLEMENTED | deterministic |
| 進退神 | IMPLEMENTED | transformation tag |
| 伏神 | IMPLEMENTED | candidate placement |
| 用神類別 | IMPLEMENTED_PARTIAL | reviewed categories only |
| 元神忌神仇神 | IMPLEMENTED | candidate relation |
| 六合／六沖卦 | IMPLEMENTED | chart flags |
| 爻六合／六沖 | IMPLEMENTED | day/month/change direct relation |
| 暗動 | CONDITIONAL | never auto from day clash alone |
| 三合局 | SOURCE_REVIEW_READY / NOT_AUTO_FORMED | formation conditions are contextual |
| 生旺墓絕 | SOURCE_REVIEW_READY | no standalone good/bad shortcut |
| 反吟伏吟 | SOURCE_REVIEW_PENDING_DETERMINISTIC_GOLDEN | do not guess |
| 三刑 | SOURCE_REVIEW_PENDING | do not auto-promote |
| 隨鬼入墓 | SOURCE_REVIEW_PENDING | requires use/god context |
| 獨發／兩現 | PARTLY_COVERED | motion/use candidates expose facts |
| 星煞 | NON_CORE | optional only |
| 應期 | REVIEW_ONLY | never automatic from one rule |
| 卦身 | NON_CORE / SCHOOL_DEPENDENT | future method-specific layer |

### Why some items remain conditional

《增刪卜易》自己 repeatedly warns against mechanical shortcuts.

Examples:

- 生旺墓絕：本書只取生、旺、墓、絕，且有「旺相時論生不論絕／得生時論生不論墓」等條件；
- 三合：動爻數量、暗動、空破、入墓、世爻是否在局、局生克世等都影響；
- 應期：靜逢值沖、動逢合值、太旺逢墓沖、衰絕逢生旺等只是 conditional patterns。

所以「把所有關鍵字都判成 yes/no」反而不正確。

## 8. Football research layer

六爻不直接進現有 football final synthesis 當第四個投票器。

先設 candidate protocols。

### L-F1_SHI_YING

- Home = 世
- Away = 應

Authority：

`PROJECT_ADAPTATION_FROM_CLASSICAL_SELF_OTHER`

### L-F2_ZISUN_GUANGUI

由《火珠林》征戰 lens 發現：

- 子孫 = 我軍
- 官鬼 = 敵

足球化後：

- Home = 子孫
- Away = 官鬼

Authority：

`PROJECT_ADAPTATION_FROM_HUOZHULIN_BATTLE_LENS`

### Hard rule

L-F1 / L-F2 必須：

- 同一批 fixture；
- 同一起卦 input；
- 平行運行；
- 比較 aggregate 1X2 accuracy；
- 不得逐場挑較像結果的一套。

只有 method comparator 證明某 protocol 穩定較好，才能升成 football default。

## 9. Packet / AI handoff

`LIUYAO_PACKET_V1` 保存：

- question
- event time / timezone
- method ID
- 六次輸入語義
- full chart
- question role
- use-god review
- strength review
- motion review
- source audit
- contradiction register
- uncertainty register
- deterministic SHA

ChatGPT 不可重排。

## 10. Anti-overfit / anti-backfill

禁止：

- 看結果後換用神；
- 看結果後把應爻改成主隊；
- 看結果後改日界；
- 看結果後把日沖從日破改稱暗動；
- 看結果後改起卦法；
- 把六神單獨轉成比分；
- 把六沖／六合單獨轉成必勝必敗；
- 把指定影片未知內容寫成古法。

## 11. Golden validation

CI 至少鎖：

1. 64 卦八宮完整覆蓋；
2. 乾為天納甲：
   `子寅辰午申戌`；
3. 乾為天世6／應3；
4. 天風姤為乾宮一世，世1／應4；
5. 《增刪卜易》水天需→天水訟：
   變爻六親仍按正卦坤宮（土）推；
6. packet SHA tamper detection；
7. pending user video 不得升格 core；
8. illegal line values reject。

CI entry：

`python tools/validate_liuyao.py`

## 12. Next source-lock priorities

順序：

1. 反吟／伏吟 exact mechanical definition + source golden；
2. 三合局 formation engine，先只做 candidate / condition audit；
3. 生旺墓絕 direct lifecycle review；
4. 隨鬼入墓；
5. 獨發／兩現；
6. 應期 rule catalog；
7. 類別化用神大全；
8. 若取得指定影片逐字稿，逐條建立：
   `VIDEO_CLAIM → CLASSICAL_SUPPORT / MODERN_LINEAGE / AUTHOR_HEURISTIC / REJECTED`。

完整性標準不是「功能越多越好」，而是：

> 每一條能算的規則，都知道它從哪裡來、什麼條件下成立、什麼時候不能用。
