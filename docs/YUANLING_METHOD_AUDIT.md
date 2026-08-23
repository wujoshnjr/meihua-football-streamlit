# 《奇門遁甲元靈經》方法審查

## 工程結論

JARVIS 不建立一個混合的「日奇門・演數七要盤」。目前拆成兩個獨立元件：

1. `yuanling.yanshu_qiyao` — 演數七要。
2. `yuanling.riqimen` — 日奇門。

只有 `RIQIMEN_QIYAO_EXPERIMENT` 可以把兩份資料並列送入同一研究 packet，而且 packet 必須明示這是 **project experiment**，不是《元靈經》原文明文規定。

## 為什麼必須拆開

卷一目錄依次列「演數七要」「數主吉凶歌訣」「日奇門」為不同條目。正文亦先定七要：

- 數宮
- 數主
- 飛星
- 入門
- 直日星
- 日干
- 時支

再另起日奇門規則。現有文本沒有足夠證據把「演數七要必須建立在日奇門盤上」當作固定古法。

## 星系審查

《元靈經》同書至少出現兩套不可混名的九星語彙。

### 時家奇門九星

`天蓬 / 天芮 / 天沖 / 天輔 / 天禽 / 天心 / 天柱 / 天任 / 天英`

這一層留在 `qimen/`。

### 元靈數術九星

卷一伏身訣與卷三值日歌訣使用：

`一白 / 二黑 / 三碧 / 四綠 / 五黃 / 六白 / 七赤 / 八白 / 九紫`

卷三又保留太乙、攝提、軒轅、招搖、天符、青龍、咸池、太陰、天乙，以及貪狼、巨門、祿存、文曲、廉貞、武曲、破軍、左輔、右弼等別名層。

所以 `yuanling.stars.NUMERIC_STARS` 是獨立 registry，禁止直接 reuse `qimen.constants.STAR_BY_HOME`。

### 「黑星為主」提供的重要證據

《數主吉凶歌訣》舉乾宮、黑星為例，並稱黑星落離為生、落震巽為難、落艮坤為和。若把黑星按二黑土的洛書五行正規化，三個方向完全吻合：

- 離火生土 → 生
- 震巽木克土 → 難
- 艮坤土同類 → 和

因此目前可高置信度判斷：**演數數主至少不能預設成時家天蓬/天芮九星。**

但完整「遁至本時之星」如何起飛、如何定飛星，仍需 source reconstruction；JARVIS 不用相似術數算法補空白。

## 日奇門目前可重建部分

正文逐三日列出六十日的「某宮起休」表。JARVIS 已將其精確機器化為 60 個干支日對應起休宮。

正文也明示：

- 以本節三元定局作地盤；
- 本甲旬頭加本日干；
- 本甲旬頭即值符；
- 陰遁奇直皆逆，星門皆順。

所以 `build_riqimen_base()` 可以可靠輸出：

- 節氣
- 三元
- 陰陽遁
- 局數
- 地盤奇儀
- 日旬頭
- 六十日起休宮

但「值符之上星加本日干穿宮數去」的完整機械步驟尚未 source-lock；因此目前 status 是：

`PARTIAL_SOURCE_GROUNDED__HEAVEN_PLATE_PENDING`

而不是假裝完整排盤。

## 演數七要目前輸出策略

`build_qiyao_review()` 固定輸出七個 factor slot。能由曆法確定的 `日干`、`時支` 直接填入；尚未完成古法算法 reconstruction 的項目保留：

`UNRESOLVED_BY_SOURCE_AUDIT`

研究者可以人工填入已由原典重建的 raw facts，但這些輸入必須保持 raw/audit 性質。

## Packet

`YUANLING_YANSHU_PACKET_V1` 包含：

- event local datetime / IANA timezone
- 模式 A/B
- 七要 slots
- 數主落宮 source-song state（若已有研究輸入）
- numeric-star registry audit
- optional Ri-Qimen base
- uncertainty
- deterministic SHA-256
- AI interpretation contract

第一階段硬性禁止：

- `數宮3 -> 3球`
- 宮數直接轉比分
- 自動勝率
- 賽後回填規則
- 把天蓬/天芮系靜默當作數主星系

`score_synthesis` 明確為 `DEFERRED_UNTIL_BLIND_TEST_PROTOCOL`。

## 下一個 source-reconstruction 工作

優先解決兩個文本技術問題：

1. 演數：「遁至本時之星」的起點、順逆、星序與數宮算法。
2. 日奇門：「值符之上星加本日干穿宮數去」的逐步機械算法與可核對例盤。

只有這兩項取得可重建 golden examples 後，才應把 raw numeric candidates 自動化；足球總進球的實驗規則必須再另開盲測層。
