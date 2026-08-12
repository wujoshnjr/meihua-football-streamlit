# 操作手冊

## Streamlit Community Cloud

- 新部署請在 Advanced settings 選擇 Python 3.12。既有部署無法原地更換 Python；若不是 3.12，需先記下網址、GitHub 設定與 Secrets，再刪除並以 3.12 重新部署。
- `requirements.txt` 固定使用 Streamlit 1.56.0，避免新版 Starlette／Uvicorn 啟動路徑在託管環境發生原生程序崩潰。
- pandas、NumPy 與 PyArrow 固定為具有 CPython 3.12／3.13 manylinux wheel 的相容版本；應用本身以標準庫 CSV 儲存，不在啟動時匯入這些原生資料套件。
- `.streamlit/config.toml` 停用 Streamlit 內建檔案監看；GitHub 更新仍由 Community Cloud 平台拉取。
- 依賴版本變更後，請從 App settings 執行 Reboot app，讓平台重建環境。

## 日常排卦

1. 填寫體方與用方名稱，事件名稱由系統自動組合。
2. 填寫官方 `event_at`（含 UTC 位移）、事件 IANA 時區（如需）、開球時間來源等級與來源網址，並選擇樣本分類。
3. 核對系統規則 `freeze_at = event_at − 6h`；主要盲測只可把在 freeze_at 前鎖定的資料標記為 `CLEAN_BLIND`。
4. 貼上「體方自述（起象）」與「用方自述（起象）」；兩段皆使用同一套第一人稱十一行固定結構，每項各自成為一個非空行，依系統計數各 180～220 數。
5. 貼上「賽前中性介紹（動爻）」；使用第三人稱平衡介紹雙方，依系統計數 300～450 數。
6. 三段只能使用賽前資訊，範圍固定為九十分鐘，不含延長賽與 PK。
7. 可先按「只檢查格式與計數」；此動作不會起卦或儲存，只列出三段實際計數與需修正項目。
8. 要換新內容時，可用每格下方的獨立清除按鈕；只清除指定文字框，並移除畫面上的上一筆排卦結果。
9. 按「完整排卦」。若人稱、十一行順序、固定開頭、實質內容、名稱或字數不合規格，畫面會列出需修正項目；泛用詞會另列品質提醒。
10. 核對 `event_at` 卦理時間、`freeze_at`、`cast_at` 稽核時間、三段計數、餘數與六爻動爻標記。
11. 視需要下載完整 HTML 排卦表或儲存到後台。

建議在開賽前六小時凍結三段內容；之後只有重大傷停或先發變化才重新建立版本，且體用雙方必須一起更新。起卦後不得因卦象不合直覺而替換同義詞、補句或重新計數。系統保存三段原文、規格版本與排卦指紋供回溯。

## 獨立盲測評估

排卦主程式不讀取賽果。預測鎖定、賽果登錄與評估均使用 `tools/evaluate_forecasts.py`，操作命令與欄位見 `docs/FORECAST_EVALUATION.md`。正式比較版本時只看 `CLEAN_BLIND`，並保留每個 `method_version` 的全部歷史列，不覆寫舊預測。

## GitHub Contents

設定 `.streamlit/secrets.toml` 後，排卦紀錄寫入 `data/meihua_castings.csv`，報告寫入 `casting_reports/`。Token 只需要指定儲存位置的 Contents 讀寫權限；v5 不需要 GitHub Models 權限。

## 經文維護

正常執行不連網。需要更新經文時，使用 `tools/build_complete_knowledge.py` 從經人工確認的繁體來源重建，之後必須執行完整測試並檢查代表性經文差異。

## 故障隔離

- GitHub 儲存失敗不影響當次本地排卦與下載。
- 知識庫不完整時應用會明確報錯，不用空字串替代。
- 舊版比分 CSV 不應改名為新排卦 CSV，也不應直接合併欄位。
