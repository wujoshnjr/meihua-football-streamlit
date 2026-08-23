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

《數主吉凶歌訣》在目前《元靈經》公開轉錄舉「乾宮、黑星為主」，並稱黑星落離為生、落震巽為難、落艮坤為和。若把黑星按二黑土的洛書五行正規化，三個方向吻合：

- 離火生土 → 生
- 震巽木克土 → 難
- 艮坤土同類 → 和

因此目前可高置信度判斷：**演數數主至少不能預設成時家天蓬/天芮九星。**

但完整「遁至本時之星」如何起飛、如何定飛星，仍不能只靠這一例完成；JARVIS 不用現有時家引擎類推補空白。

## 旁證 reconstruction：能前進，但不能升格成《元靈經》明文

新的 `knowledge/yuanling_collateral_reconstruction.json` 把旁證獨立成 authority tier：

`COLLATERAL_QIMEN_TEXT_RECONSTRUCTION`

### 1. 《金函玉鏡》日遁九星

《諸葛武侯行兵遁甲金函玉鏡卷一・九星落局法》明列：

`太乙 → 攝提 → 軒轅 → 招搖 → 天符 → 青龍 → 咸池 → 太陰 → 天乙`

並給出甲子日完整 anchor：

- 冬至後陽遁：太乙在艮八，九星順行九宮。
- 夏至後陰遁：太乙在坤二，九星逆行九宮。

這與《元靈經》附圖附近「甲子旬頭起艮……太乙臨之」及其同系星名高度相合，所以 JARVIS 新增：

`collateral_daily_nine_star_chart(day_ganzhi, dun)`

它可以 deterministic 重建一份 **日遁九星候選盤**，並以甲子陽/陰兩個完整盤作 tests。

但是：

- 數宮上的該星只標成 `飛星候選`；
- 中宮該星只標成 `直日星候選`；
- 不自動等同數主；
- 不自動寫回演數七要 primary slots。

### 2. 《奇門寶鑑》洞庭老人捷徑占法

《奇門寶鑑》在「演數七要」之前保存一段洞庭老人捷徑占法：

- 中宮起六甲日；
- 陽遁按乙乾、丙兌、丁艮、戊離、己坎、庚坤、辛震、壬巽、癸中順行；
- 陰遁反向；
- 在本日宮起子時，同方向遁至本時；
- 酉、戌、亥重在子、丑、寅三宮；
- 再布日遁九星；
- 再移八門，看數宮何門。

這提供了一條很強的 **數宮候選 reconstruction**。JARVIS 已新增：

`collateral_number_palace(day_ganzhi, hour_branch, dun)`

但結果仍標成：

`CANDIDATES_ONLY__NOT_PRIMARY_YUANLING_FACTS`

也就是它可以讓研究工作從「完全不知道怎麼算」前進到「有可重建旁證候選」，卻不會被程式寫成《元靈經》已明文確定。

## 必須保留的跨文本差異

旁證同時證明不能把不同文本靜默拼成一篇。現在正式記錄至少兩個差異：

1. 七要第四項：
   - 《元靈經》公開本：`四曰入門`
   - 《奇門寶鑑》旁證：`四曰八門`

2. 黑星例的數宮：
   - 《元靈經》公開本：`假如數在乾宮`
   - 《奇門寶鑑》旁證：`假如數在坤宮`

這兩者目前都是 `UNRESOLVED`。JARVIS 不因為旁證看起來更完整就擅自改《元靈經》正文。

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

`build_qiyao_review()` 固定輸出七個 primary factor slots。能由曆法確定的 `日干`、`時支` 直接填入；尚未完成《元靈經》本法 reconstruction 的項目保留：

`UNRESOLVED_BY_SOURCE_AUDIT`

同一物件另帶：

`collateral_reconstruction`

其中可以看到：

- 候選數宮；
- 候選日遁九星盤；
- 數宮上的日遁星候選；
- 中宮日遁星候選；
- 每一項的 non-equivalence rule 與 source IDs。

**旁證候選存在，不代表 primary slot 已解決。**

## Packet

`YUANLING_YANSHU_PACKET_V1` 包含：

- event local datetime / IANA timezone
- 模式 A/B
- 七要 primary slots
- 數主落宮 source-song state（若已有研究輸入）
- numeric-star registry audit
- collateral reconstruction block
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
- 把旁證候選靜默升格成《元靈經》原文明文

`score_synthesis` 明確為 `DEFERRED_UNTIL_BLIND_TEST_PROTOCOL`。

## 下一個 source-reconstruction 工作

現在最重要的未決問題已縮小為：

1. **數主**：確認《元靈經》「遁至本時之星」究竟如何從數宮/日遁星層形成數主，以及數主與飛星是否確為不同 star facts。
2. **直日星**：確認卷三值日九星與旁證日遁中宮星的精確關係，不能只因名稱相近就合併。
3. **入門**：重建其門盤機械法，並處理《元靈經》「入門」與《奇門寶鑑》「八門」差異。
4. **日奇門穿宮**：把「值符之上星加本日干穿宮數去」做成逐步、可核對的 golden examples。

只有這些關係取得足夠 source lock 後，才應啟用任何自動 `raw_numeric_candidates`。足球總進球的實驗規則仍必須在這之後另開盲測層。
