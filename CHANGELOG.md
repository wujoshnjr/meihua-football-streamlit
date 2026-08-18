# Changelog

## 8.0.0 — JARVIS v8 Web Integration 與 Release Status

### 新增

- Streamlit 新增 `JARVIS v8 Dashboard` 與更新後的 `Research Lab`，把 Dynamic Football、xG tuning、fixture context、M0–M3、calibration、untouched stability 與 market incremental-value stack 真正輸出到部署網頁。
- 新增 `jarvis.release.runtime_release_status()`，把 **Web App**、**Live Predictor** 與 **Research Stack** 三層版本拆開管理。
- Web App 正式升為 `8.0.0`；目前 Live Predictor compatibility path 仍保留 `qimen.prediction.CODE_VERSION = 7.2.0` 與 Independent Poisson champion，不因 UI 升版自動換模。
- Runtime contract 明示 `automatic_promotion=False` 與 `FROZEN_CHRONOLOGICAL_ARTIFACT_REQUIRED`，避免未驗證 research challenger 被誤當成 production champion。
- Dashboard / Research Lab / README 統一顯示 Web 與 Live 版本，並加入 smoke / consistency test 防止 release drift。

### 邊界

- 8.0.0 是**部署與研究介面版本**，不是「v8 challenger 已證明更準」的宣告。
- Live Predictor 的數學路徑沒有在本 release 被偷偷替換；真正 promotion 仍需 frozen TRAIN → VALIDATION → CALIBRATION → TEST_UNTOUCHED evidence 與人工 review。

## 7.2.0 — JARVIS 時序訓練與獨立校準

### 新增

- 四層 chronological manifest：TRAIN、VALIDATION、CALIBRATION、TEST_UNTOUCHED；拒絕反向界線、重複 match ID 與任何空層。
- TRAIN-only Dixon–Coles rho 擬合器，含時間半衰期、profile likelihood 95% 區間、邊界警告及 artifact SHA-256。
- CALIBRATION-only temperature scaling，保存校準前後 log loss、模型規格指紋與資料指紋。
- 預測端只接受 `dc-rho-fit:<SHA-256>`／`temperature-fit:<SHA-256>`，不接受手動文字冒充訓練來源。
- 同時輸出 raw 與 calibrated 1X2；比分矩陣維持 raw，避免把類別校準誤套成精確比分校準。
- provenance 新增部署 `git_commit`；奇門解禁 gate 要求 champion／challenger 使用相同且正式的 40–64 位 commit。
- cutoff-only TeamForm builder：固定同聯賽最近 N 場、`available_at <= cutoff`、時間半衰期、有效樣本權重、xG 覆蓋門檻、聯盟基準與來源指紋。
- `experiment-manifest.schema.json` 及完整訓練／校準測試。

### 邊界

- 已知的邁阿密 3–2、法國 0–2、挪威 1–1 沒有進入 TRAIN、VALIDATION 或 CALIBRATION，也沒有用來選 rho 或 temperature。
- 新元件建立的是可驗證的準確率改善路徑；沒有真實歷史資料 rolling backtest 前，仍不宣稱準確率已提高。

## 7.1.0 — JARVIS 時序與增量驗證核心

### 新增

- `EARLY`（T−6h）及 `LINEUP`（T−30m）雙封盤；LINEUP 必須確認並連結雙方官方先發來源。
- `published_at <= retrieved_at <= data_as_of <= locked_at < event_at` 完整時間鏈驗證。
- 來源清單、資料快照、足球特徵、奇門特徵及模型規格的獨立 SHA-256 指紋，並保存實際 tzdb 版本。
- Dixon–Coles 低比分 challenger；rho 必須附歷史訓練窗來源，無效校正係數會被拒絕。
- Macro-F1、和局召回、coverage、top-label／classwise ECE，以及 competition／matchweek 配對區塊 bootstrap。
- 5,000 場 untouched blind sample、95% CI、多聯賽、多時窗與校準條件組成的奇門解禁閘門；只輸出人工審查資格，永不自動啟用。
- StatsBomb Open Data 本地快照 provider 與 Draft 2020-12 預測鎖 JSON Schema。

### 邊界

- 本版沒有用邁阿密 3–2 或任何已知賽果估計 rho、模型權重或奇門方向。
- Dixon–Coles 尚未成為 champion；在完整時序回測與獨立校準前仍標為 `CHALLENGER_UNVALIDATED`。

## 7.0.0 — JARVIS 可稽核預測基準

### 新增

- 獨立於奇門語義的 JARVIS Poisson 足球基準：攻防率收縮、可選 xG／xGA、主客場聯盟均值、期望進球、1X2 與前五比分候選。
- `data_as_of`、資料來源、盤前聲明、`locked_at < event_at` 驗證及預測 SHA-256 指紋。
- 奇門盤轉為版本化 shadow features；本版權重固定為零，不以單場賽果回填權重。
- 賽後 log loss、Brier、RPS、1X2 top-1 與正確比分 top-1／top-3 評估接口及彙總函式。
- JARVIS Streamlit 操作頁、模型輸入快照、資料警告、鎖定狀態與 JSON／Markdown／HTML 匯出。
- `docs/JARVIS_MODEL.md` 模型卡與 `data/jarvis_prediction_template.csv` 批次資料模板。
- Dixon–Coles、時間序列切分、機率校準與 StatsBomb 開放資料方法來源。

### 修正

- 九星旺衰不再用一般四季五行粗分，改按《遁甲演義》卷三的月支旺、相、廢、休、囚表，規則版本為 `qimen-nine-star-month-branch-v1.0.0`。
- 盤前稽核不再接受硬編碼布林值冒充鎖定；改為實際比較帶時區的鎖定時間與開賽時間。
- 歷史／盤後建立的指南與預測明確標為回溯探索，不納入正式準確率。

### 邊界

- JARVIS v0.1 尚未校準，只是建立後續 Dixon–Coles、情境資料與奇門增量實驗的可比較基準。
- 機率最高比分只是候選，不是固定比分；所有輸出仍非投注建議。

## 6.2.0 — 起局與解盤助手

### 新增

- 起局前固定問題、事件時點、IANA 時區、方法、主客、焦點、口徑、資料截止、反證與鎖定指紋共 10 項稽核。
- 10 層解盤順序與 12 個足球觀察焦點；焦點只作第二層鏡頭，不取代主隊日干／客隊時干。
- 306 組完整關係矩陣：81 組天地盤可見干、72 組星門、72 組門宮、81 組星宮。
- 古籍固定格名、古籍合參概念＋五行推導、現代足球應用三種權威層級。
- 本盤逐宮關係、全矩陣搜尋、應期候選、時間基準與常見錯誤頁面。
- 問題、焦點、盤前稽核、逐層指南與鎖定時間寫入 JSON／Markdown／HTML 匯出。
- IANA tzdb、Python zoneinfo、NOAA 太陽時公式及《奇門遁甲秘笈大全》十干／星門／主客／門宮專頁來源。

### 邊界強化

- 沒有固定古名的關係只標為五行組合推導，不杜撰古訣。
- 真太陽時的天文計算與是否採其排奇門分開；本版仍只執行事件所在地民用時。
- 應期不自動指定日期或比賽分鐘；未在賽前登記的賽後對時只算探索觀察。
- 306 組代表目前 schema 的全覆蓋，不宣稱窮盡所有奇門流派。

## 6.1.0 — 足球語義全覆蓋

### 新增

- 20 個足球分析維度與 StatsBomb／FIFA／IFAB 事件語彙。
- 108 個奇門基礎足球義：9 宮、8 門、9 星、8 神、10 干、12 支、5 旺衰、8 結構狀態與 39 格局。
- 每個足球義均含可能表現、可觀察訊號與反證條件。
- 可按足球詞彙反查奇門符號的「足球義理庫」。
- 全組合解讀器與五行層間關係；覆蓋 5,184 個核心組合及 419,904 個含天地盤干基礎結構。
- 足球義隨主客用神寫入稽核匯出。

### 邊界強化

- 明示古典原義、足球事件語彙與專案類比規約三層來源。
- 「完整」限於目前 schema 的全覆蓋，不宣稱窮盡所有奇門流派。
- 組合器只產生待驗證假說，不輸出勝負、比分、進球數、機率或投注建議。

## 6.0.0 — 奇門遁甲重構

### 重大變更

- 專案領域由梅花易數全面改為奇門遁甲。
- 移除數字／文字起卦、互卦、變卦、體用卦、納甲、六十四卦、三百八十四爻與焦氏易林資料。
- 舊梅花紀錄不自動轉成奇門盤；兩者輸入、符號與推演規則不相容。

### 新增

- 時家奇門轉盤拆補排盤核心。
- IANA 時區、精確節氣、四柱、十八局、旬首、值符值使、九宮四盤。
- 奇儀格、刑墓迫、空馬、伏吟反吟等可測試判定。
- 結構化奇門知識庫與全文搜尋。
- 足球主客映射、賽前資料凍結、對稱更新及候選情境排序。
- 含方法版本與 SHA-256 指紋的 JSON、Markdown、HTML 匯出。

### 安全邊界

- 盤內索引不是機率、期望進球或投注信心。
- 不自動輸出固定比分或勝負。
- 有流派差異的條件只放知識層，不混入自動排盤。
