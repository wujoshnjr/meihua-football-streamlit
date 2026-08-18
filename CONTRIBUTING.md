# 貢獻指南

## 原則

1. 排盤／起卦規則的任何修改都要提升方法版本，並附固定情境測試。
2. 新格局須寫明成立條件、例外、來源與傳承差異；`knowledge_only` 未鎖定前不得自動命中。
3. 古籍數位轉錄、後世 commentary、JARVIS project heuristic、足球 modern application 必須分層。
4. 原典不得用 AI 補字、改字或在沒有 provenance 的情況下「修正」。來源疑點應保存 anomaly / review status。
5. 修改《周易》corpus parser 時，必須維持 64/64 卦、384/384 標準爻、來源 page/commit/SHA 與 Xiaoxiang mapping contract。
6. 修改《焦氏易林》corpus 時，必須維持 4096/4096 pair、來源定位與重建 zero-diff。
7. 足球應用不得偽稱古籍原文，也不得把吉凶、索引或 heuristic 分數改稱勝率。
8. 新增足球義必須同時提供 source basis／抽象義、可能表現、observable、counter-signal 與不確定性。
9. 賽後資料不得回灌至賽前占測 packet。
10. `DIVINATION_PACKET_V2` schema 改動必須提升 packet schema，並保留 deterministic SHA 與舊 packet 不被回寫的原則。

## 開發檢查

```bash
pip install -r requirements-dev.txt
python tools/import_zhouyi_kanripo.py --check
python tools/validate_zhouyi.py
python tools/import_yilin_kanripo.py
ruff check .
python -m pytest -q
python tools/validate_knowledge.py
python tools/validate_yilin.py
```

提交前同步更新 `CHANGELOG.md`、來源登錄、coverage 文件與相關 schema／方法版本。