# 操作手冊

## Streamlit Community Cloud

- 新部署請在 Advanced settings 選擇 Python 3.12。既有部署無法原地更換 Python；若不是 3.12，需先記下網址、GitHub 設定與 Secrets，再刪除並以 3.12 重新部署。
- `requirements.txt` 固定使用 Streamlit 1.56.0，避免新版 Starlette／Uvicorn 啟動路徑在託管環境發生原生程序崩潰。
- pandas、NumPy 與 PyArrow 固定為具有 CPython 3.12／3.13 manylinux wheel 的相容版本；應用本身以標準庫 CSV 儲存，不在啟動時匯入這些原生資料套件。
- `.streamlit/config.toml` 停用 Streamlit 內建檔案監看；GitHub 更新仍由 Community Cloud 平台拉取。
- 依賴版本變更後，請從 App settings 執行 Reboot app，讓平台重建環境。

## 日常排卦

1. 填寫事件名稱、體方、用方。
2. 貼上體方段落、用方段落及完整中性段落。
3. 按「完整排卦（不解卦）」。
4. 核對台北國曆／農曆起卦時間、三段計數、餘數與六爻動爻標記。
5. 視需要下載 JSON／Markdown 或儲存到後台。

## GitHub Contents

設定 `.streamlit/secrets.toml` 後，排卦紀錄寫入 `data/meihua_castings.csv`，報告寫入 `casting_reports/`。Token 只需要指定儲存位置的 Contents 讀寫權限；v5 不需要 GitHub Models 權限。

## 經文維護

正常執行不連網。需要更新經文時，使用 `tools/build_complete_knowledge.py` 從經人工確認的繁體來源重建，之後必須執行完整測試並檢查代表性經文差異。

## 故障隔離

- GitHub 儲存失敗不影響當次本地排卦與下載。
- 知識庫不完整時應用會明確報錯，不用空字串替代。
- 舊版比分 CSV 不應改名為新排卦 CSV，也不應直接合併欄位。
