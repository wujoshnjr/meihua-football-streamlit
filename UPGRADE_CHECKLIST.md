# v3.1 升級檢查表

## 上傳前

- [ ] 下載並備份舊的 `data/meihua_cases.csv`
- [ ] 不要刪除 Streamlit Secrets
- [ ] 不要把真正的 Token 放進 GitHub

## GitHub

- [ ] 上傳所有根目錄 `.py` 檔
- [ ] 上傳 `knowledge/` 三個 JSON 檔
- [ ] 更新 `requirements.txt`
- [ ] 保留現有 `data/meihua_cases.csv`
- [ ] 確認 `.streamlit/secrets.toml.example` 只是範例，不含真 Token

## Streamlit Secrets

- [ ] `GITHUB_TOKEN` 可寫入 repository Contents
- [ ] `GITHUB_MODELS_TOKEN` 只有 Models Read-only
- [ ] `AI_ENABLED = true`
- [ ] `AI_MODEL` 是 catalog 內存在的模型 ID

## 部署後

- [ ] 固定起卦可完成
- [ ] 顯示本卦、互卦、動爻、變卦
- [ ] 本地相似案例可以搜尋
- [ ] AI 連線測試成功
- [ ] AI 推理按鈕只呼叫一次
- [ ] 儲存後 GitHub `data/meihua_cases.csv` 有新增欄位
- [ ] GitHub `reports/` 有 Markdown 報告
- [ ] 賽後校準必須人工確認才採用 AI 建議
