# 資料模板

本目錄只保存空白／示例 schema，不提交真實賽事研究或個人資料。

- `qimen_research_template.csv`：賽事、固定問題／焦點、鎖定時間與奇門方法版本欄位。
- `evidence_template.csv`：賽前證據與時間稽核欄位。
- `jarvis_prediction_template.csv`：足球模型輸入、TRAIN／CALIBRATION artifact、Git commit、資料截止、盤前鎖定、raw／calibrated 1X2 與賽後結果欄位；空白 xG 表示未提供。
- `experiment_split_template.csv`：建立四層 chronological manifest 的最小輸入。
- `dixon_coles_training_template.csv`：TRAIN-only rho 擬合輸入。
- `calibration_template.csv`：CALIBRATION-only temperature scaling 輸入。
- `historical_matches_template.csv`：同 cutoff 時間衰減 TeamForm snapshot 的歷史賽事輸入。

應用程式的完整匯出以 JSON 為準；CSV 只供批次整理。正式盲測還必須通過 forecast horizon、來源時間鏈、模型／資料指紋及 `data_as_of <= prediction_locked_at < event_at`。歷史梅花卦例不會被載入或自動轉換。
