# Third-party notices

Operation STARK 的直接 runtime dependencies：

| 套件 | 用途 | 授權 |
|---|---|---|
| Streamlit | Web 介面 | Apache-2.0 |
| 6tail/lunar-python | 干支、農曆與節氣 API | MIT |

完整套件來源與版本見 `requirements.txt` / `requirements-dev.txt`。

## 內嵌古籍數位轉錄

本 repository **不只保存摘要與連結**；為了可重建與 source-aware 審查，亦提交了固定上游版本衍生的古籍數位轉錄資料：

- 《周易》：Kanripo `KR1a0001`，pinned commit `8284adbf9e3435d713180e24f05bf75f8b7d1d96`。JARVIS 只 materialize 結構化的 64 卦／384 標準爻、卦辭／彖／象與 provenance。
- 《焦氏易林》：Kanripo `KR3g0029`，pinned commit `764e995ce74aa249081918ca1b0c23bbca62bec8`，作 4096 本卦→之卦 base transcription。

這些資料的來源、用途與 pinned commit 均登錄於 `knowledge/sources.json`。本 notice 的目的在於如實揭露 provenance；它**不是**對古籍版本、數位轉錄或上游資料的著作權／授權狀態作新的法律結論。部署或再散布前，維護者仍應依實際使用地區與上游條款自行審查相關權利。

## 專案新增內容

JARVIS 的結構化摘要、source-review policy、football modern application、observable / counter-signal 與 semantic heuristic 是 Operation STARK 專案層；不得冒充《周易》《梅花易數》《焦氏易林》或奇門古籍原文，也不代表術數或足球預測準確率。