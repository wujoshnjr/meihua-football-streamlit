# v5 資料結構

## `data/meihua_castings.csv`

每列是一份排卦紀錄，主要欄位分為：

- 識別：資料結構版本、系統版本、排卦 ID、指紋。
- 起卦時間：台北國曆時間與 ISO 時間、完整農曆時間、干支年、閏月、農曆日及干支時辰。
- 輸入：標題、類別、體／用名稱與三段原文。舊版「補充資料」欄位僅為歷史資料相容而保留，新紀錄固定留空。
- 取數：三段字數、除八／除六餘數。
- 八卦：體卦、用卦、先天數、五行。
- 六爻：本卦、互卦、動爻、變卦及各自六爻字串。
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

## 排卦下載 JSON

下載檔頂層包含 `schema_version`、`system_version`、`knowledge_version`、`input`、`casting` 與 `jiaoshi_yilin`。其中 `jiaoshi_yilin` 只收錄本次排卦對應的一條林辭，包含：

- `entry_key`：例如 `乾之坤`。
- `main_hexagram`、`changed_hexagram`：完整卦名、短名、卦序、卦符與六爻結構。
- `text`、`text_style`：完整標點林辭與文字樣式。
- `source`、`base_source`、`source_completion_note`：版本、授權及必要的補足紀錄。

## 歷史資料

`data/meihua_cases.csv` 是 v1–v4 的比分預測歷史檔案。v5 不載入、不遷移、不更新，以避免新舊語意混用。
