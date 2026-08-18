# Operation STARK 術數知識庫

本目錄保存 JARVIS 起局／起卦後交給 ChatGPT 的知識上下文。資料明確分成：**古典／傳統義理、專案結構化摘要、足球現代應用**；三者不得混稱。

## 奇門遁甲

- `entities.json`：九宮、八門、九星、八神、十天干與基礎術語。
- `calendar.json`：二十四節氣、陰陽遁十八局、十二地支、驛馬與五行。
- `patterns.json`：奇儀格、三遁、三詐、五假、庚格、伏吟反吟、刑墓迫等盤勢狀態。
- `methods.json`：時家／日家、轉盤／飛盤、拆補／置閏、時間與寄宮差異；實際引擎只採鎖定版本。
- `interpretation.json`：問題鎖定、逐層判讀、主客版本、關係矩陣、應期邊界與錯誤防護。
- `football_ontology.json`：奇門符號／狀態的足球衍生義、可觀察訊號、反證條件與組合順序。

`automation=implemented` 表示引擎有固定且可測試的成立條件；`knowledge_only` 表示傳承差異大，只保留知識，不擅自混入盤面。

## 梅花易數

- `meihua_trigrams.json`：八卦數、五行、方位、基本類象與足球衍生義。
- `meihua_hexagrams.json`：六十四卦完整 catalog；每卦含卦序、卦名、上下卦、主題、一般解析與足球衍生義。
- `meihua_rules.json`：年月日時起卦、體用五種關係及固定解讀順序。
- `meihua_line_roles.json`：初、二、三、四、五、上六個動爻位置的階段含意與足球觀察重點。

JARVIS 在實際起卦後會同時檢索本卦、互卦、變卦、動爻、體用與旺衰，不需要把 64×所有變化組合人工寫死。

## 共同來源

- `sources.json`：奇門／梅花古籍、曆法／時區來源與現代足球語彙來源。

足球欄位一律是 `modern application`：它可以提供「場上可能看見什麼／什麼現象會反證」的語義，但**不能由 JARVIS 自動轉成主勝、和局、客勝、固定比分或統計勝率**。最後的盤面綜合由 ChatGPT 依 `DIVINATION_PACKET_V1` 完成。
