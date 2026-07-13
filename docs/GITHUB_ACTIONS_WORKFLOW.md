# GitHub Actions

`.github/workflows/tests.yml` 在 pull request 與 `main` push 時，使用 Python 3.12、3.13 執行：

1. 安裝依賴並執行 `pip check`。
2. 編譯所有 Python 檔案。
3. 執行 Ruff 致命錯誤檢查。
4. 執行 pytest。

知識庫測試會檢查八卦、六十四卦、三百八十四爻、經文必填欄位、相關卦索引與禁止的預測欄位。
