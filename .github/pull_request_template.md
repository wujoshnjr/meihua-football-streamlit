## 變更摘要

請說明本 PR 改了什麼，以及是否改變 deterministic 排盤／起卦方法。

## Source / method boundary

- [ ] 古籍原文、數位轉錄、後世 commentary、JARVIS heuristic、足球 modern application 已分層
- [ ] 若修改 deterministic 方法，已提升 method/schema version 並加入 golden fixture
- [ ] 未使用賽後資訊回填或選規則

## Release gate

- [ ] `source-reproducibility` = success
- [ ] `test` = success
- [ ] `release-gate` = success
- [ ] **不在任何 required check 為 pending / failure / cancelled 時合併**

> Repository setting：`main` 應要求 `release-gate` 通過後才能 merge。
