# 奇門遁甲足球賽前研究系統

這是原「梅花易數足球資訊專案」的完整重構版。版本 6.0.0 已移除梅花起卦、互卦、變卦、納甲、爻辭與易林資料，改為可重現的**時家奇門・轉盤・拆補法**排盤核心，以及與足球研究明確分層的奇門知識庫。

> 奇門遁甲是傳統術數。本專案只供研究與教育，不把盤內排序索引宣稱為統計機率，也不自動產生勝負、固定比分、期望進球或投注建議。

## 已完成的範圍

- 事件所在地 IANA 時區與夏令時間檢查。
- `lunar_python==1.4.8` 四柱與精確節氣接口。
- 二十四節氣、陰陽遁、拆補三元與十八局。
- 地盤三奇六儀、天盤九星、人盤八門、神盤八神。
- 六旬旬首、值符、值使、旬空、時馬、中五寄坤二、天禽隨天芮。
- 可測試的奇儀組合、三奇升殿／入墓、六儀擊刑、門宮迫、伏吟反吟、五不遇時。
- 196 筆結構化知識索引：九宮、門星神干支、節氣局表、常用格局、方法流派與來源。
- 足球應用層固定「主隊日干、客隊時干，甲取值符宮」，只做候選情境排序。
- 賽前 `freeze_at`、對稱更新、90 分鐘口徑、JSON／Markdown／HTML 稽核匯出。

## 快速開始

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Windows PowerShell 啟用虛擬環境：

```powershell
.venv\Scripts\Activate.ps1
```

## 使用流程

1. 在左側輸入比賽所在地的日期、時間與 IANA 時區。
2. 在「資料協議」加入賽前來源；時間需含 UTC 偏移。
3. 按「建立／重建奇門盤」。
4. 先檢查方法、四柱、節氣、遁局、旬首、值符值使，再讀九宮。
5. 足球頁只顯示盤內候選情境；外部資料用來驗證或反證，不改寫排盤。
6. 匯出含方法版本、資料完整性與 SHA-256 指紋的研究檔。

## 專案結構

```text
app.py                     Streamlit 入口
qimen/calendar.py          時區、四柱、節氣、六旬
qimen/engine.py            轉盤拆補排盤引擎
qimen/football.py          足球用神與候選情境層
qimen/protocol.py          賽前資料凍結與對稱更新規約
qimen/reporting.py         JSON／Markdown／HTML 稽核匯出
qimen/evaluation.py        賽前鎖定後的定性評估
knowledge/*.json           奇門結構化知識庫
docs/                      方法、架構、資料結構與來源
tests/                     演算法不變量與規約測試
```

## 方法邊界

本版只執行一套明示方法：時家、轉盤、拆補、事件所在地民用時、晚子時換日、中五寄坤二。飛盤、置閏、茅山、真太陽時、陰盤等內容收錄於知識庫，但不混入計算。這是為了讓每張盤都可重建、可測試、可比較，而不是宣稱其他傳承無效。

詳見 [排盤方法](docs/QIMEN_METHOD.md)、[資料協議](docs/FOOTBALL_PROTOCOL.md)、[架構](docs/ARCHITECTURE.md)、[部署操作](docs/OPERATIONS.md) 與 [來源](docs/SOURCES.md)。

## 測試

```bash
pip install -r requirements-dev.txt
pytest -q
python tools/validate_knowledge.py
```

## 版本

目前版本：`6.0.0`。重大轉換內容見 [CHANGELOG.md](CHANGELOG.md) 與 [MIGRATION.md](docs/MIGRATION.md)。
