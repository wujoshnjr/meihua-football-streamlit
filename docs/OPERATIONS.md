# 操作與部署

## 本機

建議 Python 3.11 或 3.12：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

應用程式沒有必要的 API 金鑰。每次研究可直接下載 JSON、Markdown 或 HTML；Streamlit 執行環境的本機磁碟通常不應視為永久資料庫。

## Streamlit Community Cloud

1. 選擇此 GitHub 儲存庫與要部署的分支。
2. 入口檔指定 `app.py`。
3. Python 依賴由 `requirements.txt` 安裝。
4. 不需要設定舊版 GitHub casting secrets。

## 版本升級

- 曆法套件升級前，先以固定日期核對四柱與節氣交接情境。
- 排盤條件、寄宮、子時、八神或足球用神有任何改動，必須提升方法／映射版本。
- 知識文案可獨立補充，但 `knowledge_only` 轉為 `implemented` 必須新增測試。
- 歷史匯出包保留原版本，不批次改寫。
- JARVIS 模型、特徵或校準方式改動時提升各自版本；同一評估表不可混算未標版本的輸出。
- 奇門 shadow features 轉為啟用特徵前，必須先完成預先登記的時間序列盲測與基準消融。

## 故障排查

| 現象 | 檢查 |
|---|---|
| 找不到時區 | 使用 IANA 名稱，如 `Asia/Taipei`；確認系統 tzdata |
| 夏令時間不存在 | 改用官方事件時刻；不要手動補一小時掩蓋錯誤 |
| 無法取得節氣 | 確認 `lunar_python==1.4.8` 已安裝 |
| 證據驗證失敗 | 檢查 ISO 時間偏移、開賽／freeze_at 與重大更新類別 |
| JARVIS 無法取得盤前鎖 | 檢查 `data_as_of` 是否含時區、早於鎖定，鎖定是否早於開賽，以及盤前資料聲明是否勾選 |
| JARVIS 顯示 `UNCALIBRATED_V0` | 這是 Phase 2 的正常研究狀態；累積足夠鎖定樣本並以獨立時窗校準前不得移除此標記 |
| `rho_source` 被拒絕 | 必須使用 `qimen.training.fit_dixon_coles_rho` 產生的 `dc-rho-fit:<SHA-256>` |
| `calibration_source` 被拒絕 | 必須使用 `fit_temperature_scaler` 產生的 `temperature-fit:<SHA-256>` |
| gate 顯示 `all_git_commits_formal = false` | 部署需提供完整 `GITHUB_SHA`／等價 commit；本機探索輸出不能升級奇門 |
| 同一事件重建結果不同 | 比對事件時刻、時區、方法版本及依賴版本 |
