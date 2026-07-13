# 操作手冊

## 日常排卦

1. 填寫事件名稱、體方、用方。
2. 貼上體方段落、用方段落及完整中性段落。
3. 補充資料若要保存，可放入第四格；此格不取數。
4. 按「完整排卦（不解卦）」。
5. 核對三段計數、餘數與六爻動爻標記。
6. 視需要下載 JSON／Markdown 或儲存到後台。

## GitHub Contents

設定 `.streamlit/secrets.toml` 後，排卦紀錄寫入 `data/meihua_castings.csv`，報告寫入 `casting_reports/`。Token 只需要指定儲存位置的 Contents 讀寫權限；v5 不需要 GitHub Models 權限。

## 經文維護

正常執行不連網。需要更新經文時，使用 `tools/build_complete_knowledge.py` 從經人工確認的繁體來源重建，之後必須執行完整測試並檢查代表性經文差異。

## 故障隔離

- GitHub 儲存失敗不影響當次本地排卦與下載。
- 知識庫不完整時應用會明確報錯，不用空字串替代。
- 舊版比分 CSV 不應改名為新排卦 CSV，也不應直接合併欄位。
