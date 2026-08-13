# 貢獻指南

## 原則

1. 排盤規則的任何修改都要提升方法版本，並附至少一個固定曆法情境測試。
2. 新格局須寫明天盤／地盤順序、成立條件、例外、來源與傳承差異。
3. `knowledge_only` 條目在條件未鎖定前不得加入自動判定。
4. 足球應用規約不得偽稱古籍原文，也不得把排序索引改稱勝率。
5. 賽後資料不得回灌至賽前輸入。

## 開發檢查

```bash
ruff check .
pytest -q
python tools/validate_knowledge.py
```

提交前請同步更新 `CHANGELOG.md`、相關文件與 schema／方法版本。
