# JARVIS 起局／起卦／演數方法總覽

本文件說明 JARVIS 目前真正實作或正在 source-reconstruct 的四種方法。名稱必須分清：

- 奇門是**起局／排盤**。
- 梅花是**起卦**。
- 《元靈經》演數七要是**演數審查**。
- 《元靈經》日奇門是**另起日盤的研究型排盤**。

JARVIS deterministic 計算盤與卦；ChatGPT 做最後解讀。任何古籍數字、宮數、星號都不能在程式內直接換成足球勝率或比分。

## 共通事件輸入

對足球，三套事件型模組都以同一個事件身份為基礎：

1. 主隊、客隊。
2. 賽事／階段（若有）。
3. 球場、城市、國家（若有）。
4. **事件所在地 local civil datetime**。
5. **IANA timezone**，例如 `Europe/London`、`America/New_York`。
6. DST 重複時間需明確使用 `fold=0/1`；不存在的 local time 直接拒絕。
7. scheduled/revised/actual kickoff 應分開保存；真正送入起局引擎的是明確選定的 event time basis。

同一個足球 Case 中，奇門與梅花必須使用完全相同的 aware event datetime 與 timezone。

---

# 一、時家奇門・轉盤・拆補法

Method ID：`QIMEN_SHIJIA_ZHUANPAN_CHAIBU`

Engine：`shijia-zhuanpan-chaibu-v1.0.0`

Status：`PRODUCTION`

## 必要輸入

- 占問問題
- 主隊
- 客隊
- event-local aware datetime
- IANA timezone

## JARVIS 固定方法

- 時家奇門
- 轉盤
- 拆補法
- 事件所在地民用時
- 晚子時換日：lunar-python `sect=1`
- 中五寄坤二，天禽隨天芮
- 八神同名制；陰陽遁依 method config 順逆
- 足球主隊用神：日干
- 足球客隊用神：時干
- 若干為甲：取值符宮

## 起局順序

1. 把事件所在地 local datetime 轉成帶 IANA timezone 的 aware datetime。
2. 取得年、月、日、時四柱，以及當前節氣。
3. 依節氣判陰遁／陽遁。
4. 由符頭判上元／中元／下元。
5. 依二十四節氣三元局表取得局數。
6. 按局數與陰陽遁布地盤三奇六儀。
7. 由時柱判時旬與旬首儀。
8. 定值符星、值使門及其落宮。
9. 轉布天盤干、九星、八門、八神。
10. 標記旬空、驛馬、伏吟／反吟、門迫、入墓、擊刑與其他盤面 modifiers。
11. 依足球用神規則定位主隊、客隊宮。
12. 從完整盤面取出 Core 306、Extended Relations 與 source-aware knowledge context，交給 ChatGPT。

## 輸出內容

- 陰遁／陽遁、元、局數
- 四柱、旬空
- 九宮
- 地盤干、天盤干
- 八門
- 九星
- 八神
- 值符／值使
- 驛馬
- 格局與動態 modifiers
- 主客用神宮位

## 足球占問模板

`［主隊］對［客隊］，在正規時間90分鐘及傷停補時結束後，最終勝負為主勝、和局或客勝？請依奇門主客用神及全局綜合判斷最可能的比分候選，並列支持與反證盤象。`

注意：JARVIS 不自動產生這個勝負／比分；這是交給 ChatGPT 的解局任務。

---

# 二、梅花易數・年月日時先天數法

Method ID：`MEIHUA_YEAR_MONTH_DAY_HOUR`

Engine：`jarvis-meihua-year-month-day-hour-v0.3.0`

Status：`PRODUCTION`

## 必要輸入

- 占問問題
- event-local aware datetime
- IANA timezone

## 數表

八卦數：

- 乾 1
- 兌 2
- 離 3
- 震 4
- 巽 5
- 坎 6
- 艮 7
- 坤 8

地支數：

`子1、丑2、寅3、卯4、辰5、巳6、午7、未8、申9、酉10、戌11、亥12`

## 起卦公式

令：

- `Y` = 農曆年支數
- `M` = 農曆月數
- `D` = 農曆日數
- `H` = 時支數

則：

1. `A = Y + M + D`
2. `A mod 8` 定上卦；餘 0 作 8。
3. `B = Y + M + D + H`
4. `B mod 8` 定下卦；餘 0 作 8。
5. `B mod 6` 定動爻；餘 0 作 6。

傳世《梅花易數》卷一的年月日時起例就是「年月日為上卦；年月日加時為下卦；總數除六取動爻」。

## 體用

- 動爻在下三爻：下卦為用、上卦為體。
- 動爻在上三爻：上卦為用、下卦為體。

即動者為用、靜者為體。

## 互卦與變卦

- 本卦六爻由下往上編 1–6。
- 取 2–4 爻成一互卦單卦。
- 取 3–5 爻成另一互卦單卦。
- 依體在上或下，再明確標成 `body_mutual / use_mutual`。
- 將真正動爻陰陽翻轉，得到變卦。

## 解讀資料層

JARVIS 將下列內容一併打包：

1. 本卦。
2. 體／用。
3. 體卦旺衰。
4. 本用對體生克。
5. 體互／用互。
6. 變用對體。
7. 真正動爻的《周易》卦爻原文與 conditional meaning review。
8. 本卦 → 最終變卦的《焦氏易林》唯一條目。
9. 足球 wall-clock temporal audit。

傳世文本又明確說「用最緊、互次之、變又次之」，並區分體互與用互，因此 JARVIS 不把互卦兩層視為完全同權。

## 時間精準規則

開賽事件起出的卦是 `ANCHOR_CAST`，不因比賽途中時辰一換就自動被另一卦取代。

JARVIS 另外掃描：

- 時支變化
- civil date change
- lunar date input change
- UTC offset / DST change

交界重算只標為 `SECONDARY_DIAGNOSTIC_ONLY`。

因此「跨時辰」只能形成時間 checkpoint，不能自動解成逆轉。

## 足球占問模板

`以［主隊］為體、［客隊］為用，不判比分與進球，請判體方在比賽初段、中段、末段分別是得助、耗力、受制還是制用；體旺衰能否承受生克；是否存在明顯轉勢；最後形成的是控制、受壓、守成、失守或僵持，並列出對奇門結果的支持與反證。`

這樣梅花不和奇門重複報第二套比分，而是作 structure/stress test。

---

# 三、《元靈經》演數七要・QIYAO_RAW

Method ID：`YUANLING_YANSHU_QIYAO_RAW`

Status：`RESEARCH_ALPHA`

## 原典七要

固定順序：

1. 數宮
2. 數主
3. 飛星
4. 入門
5. 直日星
6. 日干
7. 時支

卷一並說「遁至本時之星即為數主」，最重數主落在何宮，同時再看本宮星、門宮、值日星、日干、時支。

## 目前可 deterministic 的部分

- event-local calendar
- 節氣
- 日干支
- 時干支
- 陰陽遁
- 日干
- 時支
- independent 一白～九紫 registry
- collateral 候選數宮與日遁九星盤

## 尚未 source-lock 的 primary 部分

- 數宮的完整《元靈經》原法
- 數主「遁至本時之星」的起點、順逆與飛遁序列
- 飛星與數主的確切機械關係
- 入門的完整步驟
- 直日星與卷三中宮值日九星的確切接口

這些欄位如果沒有 source-locked 算法，就保持 `UNRESOLVED_BY_SOURCE_AUDIT`。

## 數主落宮

若研究者已由可靠原典重建取得數主與落宮，JARVIS 可保存：

- 數主是哪顆數術星
- 落宮
- 數主／宮五行 project-normalized 關係
- 依《數主吉凶歌訣》例所能辨識的生／難／和

但 project normalization 不能冒充古籍原文。

## 卷三新增資料層

資料庫另保存：

- 一白～九紫的中宮值日九星歌訣語義。
- 一白～九紫在射覆條中的古典數目關聯。

這些資料只供數術語義研究。禁止：

`射覆數目 3 -> 3 球`

也禁止：

`數宮 3 -> 總進球 3`

## 足球研究問題

`依《元靈經》演數七要整理此場足球事件的數術原始資料；只輸出數宮、數主、飛星、入門、直日星、日干、時支及 source/uncertainty，不直接將宮數或星數換算為比分。`

---

# 四、《元靈經》日奇門・Source-grounded Base

Method ID：`YUANLING_RI_QIMEN`

Status：`PARTIAL_RESEARCH_ALPHA`

## 已 source-lock 的起盤部分

1. 由事件時刻取得節氣。
2. 由三元符頭取得上／中／下元。
3. 依本節三元定局作地盤。
4. 由日干支判本日所屬旬與本甲旬頭。
5. 依卷一六十日表取得「某宮起休」。
6. 保存「本甲旬頭即值符」。
7. 保存「陰遁奇直皆逆，星門皆順」的方向規則。

## 尚未 source-lock

關鍵句「值符之上星加本日干穿宮數去」仍缺可重建的逐步機械算法與足夠 golden example。

所以現在輸出的是：

`PARTIAL_SOURCE_GROUNDED__HEAVEN_PLATE_PENDING`

而不是假裝完整日奇門天盤。

## 和七要的關係

工程上兩者保持獨立：

- `QIYAO_RAW`：只有七要 review。
- `RIQIMEN_QIYAO_EXPERIMENT`：packet 最上層同時保存 `qiyao_review` 與 `riqimen_base` 兩個 sibling。

沒有原典明文證據前，不宣稱「演數七要必須以日奇門盤為底」。

---

# 五、足球實際使用建議

目前正式主流程仍是：

`同一比賽事件 → 時家奇門 + 梅花年月日時 → Case Bundle → ChatGPT`

角色：

- 奇門：`RESULT_ENGINE_INPUT`
- 梅花：`STRUCTURE_STRESS_TEST`
- ChatGPT：`FINAL_SYNTHESIS`

元靈目前另行：

`同一事件 → YUANLING_YANSHU_PACKET_V1_2 → ChatGPT / research audit`

在數主／飛星／直日星與日奇門穿宮算法真正 source-lock，並完成事前盲測協議以前，不把它自動併入足球比分合成。

## 歷史回測防污染

若是已完成賽事：

- 不搜尋比分、勝負、進球、紅牌、賽後統計。
- 不用賽後事件補三要十應或元靈 raw fields。
- 不因已知結果挑選 scheduled / actual kickoff。
- 不因命中或失敗改寫古法規則。

方法的改動必須先版本化，再對未見結果的樣本測試。
