# GitHub Actions 工作流程

工作流程位於 `.github/workflows/tests.yml`，在以下情況執行：

- 向 `main` push。
- 以 `main` 為目標的 pull request。

## 測試矩陣

- Python 3.12。
- Python 3.13。

## 步驟

1. Checkout。
2. 安裝對應 Python 並啟用 pip cache。
3. 安裝 `requirements-dev.txt`。
4. `pip check` 驗證相依性。
5. `python -m compileall -q .`。
6. `ruff check --select E9,F63,F7,F82 .`。
7. `pytest -q`，包含 Streamlit AppTest。

測試不應使用正式 Token、網路 AI 或 GitHub 寫入。所有外部服務測試都應以 mock 或離線資料完成。

