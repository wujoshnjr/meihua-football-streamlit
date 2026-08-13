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

## 故障排查

| 現象 | 檢查 |
|---|---|
| 找不到時區 | 使用 IANA 名稱，如 `Asia/Taipei`；確認系統 tzdata |
| 夏令時間不存在 | 改用官方事件時刻；不要手動補一小時掩蓋錯誤 |
| 無法取得節氣 | 確認 `lunar_python==1.4.8` 已安裝 |
| 證據驗證失敗 | 檢查 ISO 時間偏移、開賽／freeze_at 與重大更新類別 |
| 同一事件重建結果不同 | 比對事件時刻、時區、方法版本及依賴版本 |
