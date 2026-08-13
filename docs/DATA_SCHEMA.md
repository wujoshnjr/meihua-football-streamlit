# 資料結構

## 研究匯出包

根 schema：`qimen-football-bundle-v1.1.0`

| 區塊 | 內容 |
|---|---|
| `match` | 賽事身份、事件時間、時區、場地、freeze_at、證據與完整性 |
| `board` | 方法、曆法、遁局、旬首、值符值使、九宮、格局與警告 |
| `football_reading` | 固定主客用神、盤內訊號、完整足球義、反證與候選情境 |
| `locked_at` | 可選的賽前鎖定時間 |
| `boundaries` | 不自動預測、不宣稱機率及比賽口徑 |
| `fingerprint_sha256` | 除指紋本身外全部核心資料的標準 JSON 雜湊 |

## 九宮欄位

每宮保存：宮數、宮名、卦象、方位、五行、地盤干、寄宮干、天盤干、九星、八門、八神、旬空、驛馬與註記。中五無八門與八神；本版寄坤二的資訊同時保留在中五與坤二註記，避免資料遺失。

## 格局欄位

| 欄位 | 說明 |
|---|---|
| `name` | 格局或狀態名稱 |
| `category` | 吉格、凶格、庚格、盤勢、宮門關係等 |
| `palace` | 成立宮位；全盤或時格可為 `null` |
| `condition` | 本次盤面實際成立條件 |
| `reading` | 節制的功能性解讀 |
| `caution` | 不能從此條件外推的事項 |
| `source_id` | 對應來源索引 |

## 知識庫

知識 JSON 都有獨立 `schema_version`。`automation` 為 `implemented` 才代表引擎已有固定條件；`knowledge_only` 只供搜尋與比較。載入器不會用知識文案動態改寫演算法，避免改一段說明就讓歷史盤失去可重現性。

### 足球語義本體

`knowledge/football_ontology.json` 使用 `qimen-football-ontology-v2.0.0`：

| 區塊 | 內容 |
|---|---|
| `dimensions` | 20 個足球分析維度、別名、事件標籤與一手來源 |
| `event_taxonomy` | StatsBomb 事件、比賽階段、射門結果與 IFAB 規則語境摘要 |
| `mappings` | 108 個宮門星神干支、旺衰、狀態及格局的足球義 |
| `interaction_rules` | 五行同氣、生剋所形成的層間修飾 |
| `coverage_contract` | 條目數、組合數公式及宣稱邊界 |

每筆 mapping 必須包含 `dimensions`、`possible_meanings`、`observable_signals` 與 `counter_signals`。缺少任何欄位時，知識驗證會失敗。

## 時間格式

所有外部資料時間使用 ISO 8601 並含 UTC 偏移。事件同時保存 IANA 時區名稱，因為單一偏移無法描述歷史夏令時間規則。
