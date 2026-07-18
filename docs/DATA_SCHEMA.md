# v5.7 資料結構

## `data/meihua_castings.csv`

每列是一份排卦紀錄，主要欄位分為：

- 識別：資料結構版本、系統版本、排卦 ID、指紋。
- 起卦時間：台北國曆時間與 ISO 時間、完整農曆時間、干支年、日辰、月令、旬名、旬空及干支時辰。
- 輸入：標題、類別、體／用名稱、輸入規格版本，以及「體方自述（起象）」、「用方自述（起象）」、「賽前中性介紹（動爻）」三段原文。舊版三段欄名讀取時自動遷移；「補充資料」欄位僅為歷史資料相容而保留，新紀錄固定留空。
- 取數：三段字數、除八／除六餘數。
- 八卦：體卦、用卦、先天數、五行。
- 六爻：本卦、互卦、動爻、變卦及各自六爻字串；另存本卦宮位、世應、動爻納甲、六親與旬空。
- 條件式卦義：體／用卦線摘要、優先義項與命中規則數。
- 轉象：體卦轉象、用卦轉象、本卦與變卦五行關係。
- 稽核：完整排盤 JSON、報告路徑、計算版本。完整排盤 JSON 保留既有排盤欄位，並新增 `jiaoshi_yilin` 對應林辭物件。

同一次排卦結果重複儲存只確認既有列。重新按下排卦會取得新的時間快照，因此即使文字相同，也會形成可獨立追溯的新排卦紀錄。起卦時間不參與卦象取數。

## `knowledge/hexagrams.json`

以完整卦名為 key。每卦必須包含：

- 文王卦序、Unicode 卦符、短名、上下卦。
- 六爻自下而上的二進位結構與陰陽陣列。
- 卦義提要、關鍵字。
- 卦辭、彖傳、大象。
- 六筆爻位、爻名、爻辭、小象。
- 乾坤的特殊用爻與文言。
- 互卦、錯卦、綜卦索引。
- 來源與範圍。

## `knowledge/classics/jiaoshi_yilin.json`

- `hexagram_order`：與周易知識庫一致的 64 卦短名順序。
- `hexagrams`：短卦名對應卦序、完整卦名、卦符與六爻二進位結構。
- `entries[本卦短名][之卦短名]`：對應完整標點林辭，共 64×64＝4,096 條。
- `punctuated_entry_count`：通過標點完整性驗證的林辭數，固定為 4,096。
- `source`：維基文庫標點本、固定鏡像 commit、CC BY-SA 4.0 授權、範圍與來源網址。
- `base_source`：Kanripo 四庫本校勘快照、固定 commit 與 CC0 1.0 授權。
- `source_label_corrections`：來源標題與固定六十四變次序不一致時的可稽核校正；只校正索引標題，不改林辭原文。
- `source_completion_notes`：維基文庫標示原缺、由四庫本補足並加入句讀的三筆紀錄。

應用啟動時要求 4,096 個本卦／之卦組合全部存在、非空、含標點且以句末標點結束，並要求卦序與 `hexagrams.json` 一致。

## 排卦下載 HTML 表

使用者下載為獨立 UTF-8 HTML 文件，以完整表格呈現時間、旬空、本互變納甲、世應、雙軌六親、沖合、條件式卦義、經傳、六十四卦義、足球應用參考及焦氏易林，不顯示 JSON 程式資料。後台 `完整排盤JSON` 仍保留以下結構供稽核。

## 後台完整排盤 JSON

後台物件包含 `input`、`input_protocol`、`casting`、`hexagram_classics`、`hexagram_meanings`、`moving_line_classics`、`moving_line_dynamics`、`seasonal_strength`、`najia_analysis`、`conditional_meanings` 與 `jiaoshi_yilin`。

### `input_protocol`

- `version`：固定為 `team-self-narrative-v3`。
- `sections.body`、`sections.use`：第一人稱十一行固定結構、目標 180～220 數、實際計數、逐行固定開頭／順序、空欄、結果導向詞及品質提醒。
- `sections.neutral`：第三人稱、目標 300～450 數、實際計數及雙方名稱檢查結果。
- 頂層另存控制詞彙、五條硬規則、賽前凍結政策、原始版本政策及研究用途邊界。
- 三段只使用賽前資訊，判斷範圍為九十分鐘；此規格只降低文字噪音並控制起象一致性，不改變固定排卦公式，也不宣稱提高預測準確率。

### `conditional_meanings`

- `body_path`、`use_path`：體用雙方的變前卦、變後卦、旺衰、生克、空破、沖合與破門訊號。
- `stages[].possible_meanings`：該經卦全部八個可能義項及足球含義。
- `stages[].matched_rules`：本次真正命中的條件、證據、優先義項與降低權重義項。
- `stages[].prioritized_meanings`：依透明規則排序的前三義；`rule_score` 只供排序，不是機率或比分。

### `najia_analysis`

- `day_cycle`：日辰天干地支、日干五行、月令與月令五行。
- `xun_void`：六甲旬名、兩個旬空地支與計算說明。
- `main_hexagram`、`mutual_hexagram`、`changed_hexagram`：各自六爻納甲、世應、雙軌六親、旬空及沖合。
- 日干六親是本專案指定主欄；卦宮六親另列為常見文王卦參考，兩者不互相覆寫。

### `hexagram_classics`

主卦與變卦各固定包含 `gua_ci`、`tuan_text`、`da_xiang_text`，並附卦名、短名、卦序與卦符。

### `moving_line_classics`

固定從主卦取出本次動爻的爻位、爻名、爻辭及《小象》。動爻變後的陰陽已保留在 `casting`，不以變卦同爻文本取代主卦動爻文本。

### `moving_line_dynamics`

- 奇數爻位為陽位，偶數爻位為陰位；陰陽與位置相符為得位。
- 二、五爻為得中。
- 初四、二五、三上配對，陰陽相異為相應。
- 相鄰爻固定列出動爻所乘、所承及相比關係；另標記剛柔位序為順、逆或同類。
- 這些欄位只描述結構，不直接產生吉凶或比分。

### `seasonal_strength`

- 農曆一至十二月依寅至丑月建取五行，閏月沿用原月份月建。
- 以月令五行為基準固定計算：同月令為旺、月令所生為相、生月令者為休、克月令者為囚、月令所克為死。
- 體用動爻前後分別輸出五行、旺衰及轉強／轉弱／持平。
- 時辰五行只取時支並獨立列出，不覆寫月令旺衰。

完整公式與欄位界線見 `docs/STRUCTURED_CASTING_RULES.md`。

### `jiaoshi_yilin`

其中 `jiaoshi_yilin` 只收錄本次排卦對應的一條林辭，包含：

- `entry_key`：例如 `乾之坤`。
- `main_hexagram`、`changed_hexagram`：完整卦名、短名、卦序、卦符與六爻結構。
- `text`、`text_style`：完整標點林辭與文字樣式。
- `source`、`base_source`、`source_completion_note`：版本、授權及必要的補足紀錄。

## 歷史資料

`data/meihua_cases.csv` 是 v1–v4 的比分預測歷史檔案。v5 不載入、不遷移、不更新，以避免新舊語意混用。
