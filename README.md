# JARVIS 足球賽前研究系統

這是原「梅花易數足球資訊專案」的完整重構版。正式應用版本仍以 v7.2.0 的可重現**時家奇門・轉盤・拆補法**排盤核心、起局／解盤助手、奇門知識庫與 JARVIS 足球機率框架為基礎；v8 研究線則重新加入一個**全新、極簡、確定性的梅花易數 challenger**，並建立通用 residual 與動態足球實力模組。這不是把舊版梅花人工勝負／比分邏輯復活。

> 奇門遁甲與梅花易數都是傳統術數。兩者的盤／卦特徵都不是統計機率，也不得由人工規則直接轉成固定比分或 1X2。Production 的 1X2 與期望進球目前仍由足球統計模型產生；奇門、梅花與 v8 動態攻防模型在通過時序盲測與治理門檻前都只屬 research challenger。本專案只供研究與教育，不是投注建議。

## 已完成的範圍

- 事件所在地 IANA 時區與夏令時間檢查。
- `lunar_python==1.4.8` 四柱與精確節氣接口。
- 二十四節氣、陰陽遁、拆補三元與十八局。
- 依月支與《遁甲演義》九星專用表計算旺、相、廢、休、囚，並保存規則版本。
- 地盤三奇六儀、天盤九星、人盤八門、神盤八神。
- 六旬旬首、值符、值使、旬空、時馬、中五寄坤二、天禽隨天芮。
- 可測試的奇儀組合、三奇升殿／入墓、六儀擊刑、門宮迫、伏吟反吟、五不遇時。
- 462 筆結構化搜尋索引：九宮、門星神干支、節氣局表、常用格局、方法流派、起局／解盤規約、足球事件分類與來源。
- 10 項盤前稽核、10 層判讀順序與 12 個足球觀察焦點；問題與焦點在建立盤面時封存。
- 306 組解盤關係完整可查：81 組天地盤可見干、72 組星門、72 組門宮、81 組星宮。
- 古籍固定格名、五行組合推導與足球應用分級，不替未命名組合杜撰古訣。
- 108 個完整足球語義單元，逐筆保存可能表現、可觀察訊號與反證條件。
- 20 個足球分析維度，可用「高位逼搶、VAR、傷停、門將、定位球、反擊」反向搜尋奇門符號。
- 全組合解讀器覆蓋 5,184 個宮門星神核心組合；加入天地盤可見干後覆蓋 419,904 個基礎結構。
- 足球應用層固定「主隊日干、客隊時干，甲取值符宮」，只做候選情境排序。
- 賽前 `freeze_at`、對稱更新、90 分鐘口徑、JSON／Markdown／HTML 稽核匯出。
- JARVIS Phase 2.1：獨立 Poisson champion 與 Dixon–Coles challenger、攻防率收縮、可選 xG、期望進球、1X2 及比分候選。
- `EARLY`（T−6h）與 `LINEUP`（T−30m、雙方官方先發）雙封盤；資料截止與預測鎖都不得越過註冊界線。
- 來源清單、資料快照、足球特徵、奇門特徵與模型規格的分離 SHA-256 指紋；保存實際 tzdb 版本。
- Macro-F1、和局召回、ECE、coverage、配對 competition／matchweek block bootstrap 與奇門解禁治理閘門。
- Hudl StatsBomb Open Data 本地快照 provider；不猜測賽事時區、不在執行時靜默下載資料。
- 四層不可變時序 manifest：`TRAIN → VALIDATION → CALIBRATION → TEST_UNTOUCHED`，每層都必須有資料且禁止隨機重排。
- Dixon–Coles `rho` 的 TRAIN-only 時間衰減擬合、profile likelihood 區間與 artifact 指紋。
- CALIBRATION-only temperature scaling；預測端只接受 `temperature-fit:<SHA-256>`，並同時保存校準前後 1X2。
- 正式奇門解禁另要求 40–64 位部署 Git commit；本機沒有 commit 時仍可探索，但不能過 gate。
- 同一 cutoff、同聯賽的自動 TeamForm snapshot：固定最近 N 場、時間半衰期、xG 覆蓋門檻、聯盟基準與來源指紋，取代主觀挑選場次。
- 真正比較 `data_as_of <= locked_at < event_at` 的盤前預測鎖、SHA-256 指紋與回溯模式隔離。
- log loss、Brier、RPS、1X2 accuracy 及正確比分 top-1／top-3 評估接口。
- 奇門盤完整轉為版本化 shadow features；在時間序列盲測證明增量前不調整足球機率。
- JARVIS v8 research foundation：新增確定性的梅花「年月日時」起卦 engine、體用／互卦／變卦 raw features；不寫入人工足球方向權重。
- 通用 TRAIN-only residual lambda fitter：`log(mu) = log(football_baseline_lambda) + X beta`，L2 正則化且無 intercept；可分別承接 Qimen／Meihua feature family。
- 動態對手調整 Football challenger：以時間衰減的聯合 Poisson 估計各隊 attack 與 defence-weakness effects，並保留明示場地 baseline 與 cold-start 回退。
- v8 模型家族預先定義：`M0=Football`、`M1=Football+Qimen`、`M2=Football+Meihua`、`M3=Football+Qimen+Meihua`；interaction 只在 M3 有穩定增量後研究。

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
4. 在「起局／解盤助手」先檢查 10 項盤前稽核，再依 10 層順序讀全局、用神宮與關係矩陣。
5. 足球頁只顯示盤內候選情境；外部資料用來驗證或反證，不改寫排盤。
6. 在「JARVIS 模型」輸入同一截止時間的雙方進失球／xG 與聯盟基準，確認資料為盤前資訊後建立預測鎖。
7. 匯出含固定問題、焦點、方法版本、模型輸入、機率、鎖定資格、資料完整性與 SHA-256 指紋的研究檔。

目前 Streamlit production UI 仍以 v7.2 奇門＋Football 流程為主；v8 的梅花、通用 residual 與動態攻防元件目前是 research API，尚未冒充正式 production 輸出。

## 專案結構

```text
app.py                          Streamlit production 入口
qimen/calendar.py               時區、四柱、節氣、六旬
qimen/engine.py                 轉盤拆補排盤引擎
qimen/football.py               足球用神與候選情境層
qimen/prediction.py             既有 JARVIS Poisson 基準與奇門 shadow features
qimen/training.py               四層時序切分、rho 擬合與 temperature calibration artifacts
qimen/features.py               cutoff-only 時間衰減 TeamForm／聯盟基準 snapshots
qimen/providers/                StatsBomb Open Data 本地快照正規化介面
qimen/hybrid_prediction.py      Football vs fitted-Qimen paired research comparison
meihua/engine.py                v8 確定性年月日時梅花起卦 research engine
meihua/outcome_features.py      v8 梅花 raw outcome feature encoder
jarvis/research/residual.py     通用無 intercept Poisson-offset residual fitter
jarvis/football/strength.py     動態、對手調整 attack／defence research challenger
knowledge/*.json                奇門結構化知識庫
docs/JARVIS_V8.md               v8 多訊號研究架構
docs/DYNAMIC_STRENGTH.md        動態攻防 challenger 方法與邊界
docs/                           其他方法、架構、資料結構與來源
tests/                          演算法不變量與規約測試
schemas/                        正式預測鎖 JSON Schema
```

## 方法邊界

奇門 production 仍只執行一套明示方法：時家、轉盤、拆補、事件所在地民用時、晚子時換日、中五寄坤二。飛盤、置閏、茅山、真太陽時、陰盤等內容收錄於知識庫，但不混入計算。

梅花 v8 research engine 只執行可重現的「年月日時」起例，事件所在地民用時是 JARVIS 為實驗一致性採用的 convention；不把其他傳統起卦法混入同一實驗，也不把體用生剋人工指定成足球勝負或比分。

詳見 [JARVIS 模型](docs/JARVIS_MODEL.md)、[JARVIS v8](docs/JARVIS_V8.md)、[動態足球實力](docs/DYNAMIC_STRENGTH.md)、[排盤方法](docs/QIMEN_METHOD.md)、[起局與解盤指南](docs/READING_GUIDE.md)、[足球語義庫](docs/FOOTBALL_MEANINGS.md)、[資料協議](docs/FOOTBALL_PROTOCOL.md)、[架構](docs/ARCHITECTURE.md)、[部署操作](docs/OPERATIONS.md) 與 [來源](docs/SOURCES.md)。

## 測試

```bash
pip install -r requirements-dev.txt
pytest -q
python tools/validate_knowledge.py
```

## 版本

Production app 版本仍為 `7.2.0`。JARVIS v8 multi-signal research foundation 已進入 `main`，但在 chronological paired evaluation 通過前不取代 production champion。重大轉換內容見 [CHANGELOG.md](CHANGELOG.md)、[MIGRATION.md](docs/MIGRATION.md) 與 [JARVIS_V8.md](docs/JARVIS_V8.md)。
