# JARVIS 足球賽前研究系統

JARVIS 是一個可重現、可稽核的足球賽前研究系統，結合足球統計 baseline、奇門遁甲 shadow features、梅花易數 research features，以及嚴格的 chronological experiment contract。

## 目前版本狀態

- **Web App v8.0.0**：Streamlit 已提供 JARVIS v8 Dashboard 與 Research Lab。
- **Live Predictor v7.2.0**：主頁即時預測仍使用已存在的 frozen Football champion compatibility path；目前核心是 Independent Poisson，可選擇未驗證的 Dixon–Coles challenger。
- **Research generation：JARVIS v8**：Dynamic Football、xG tuning、fixture context、M0–M3、calibration、rolling stability、paired block bootstrap 與 market incremental-value test 已在程式與網頁可見。
- **模型不會自動升級**：Web App 升版不代表 live predictor 已換模。任何 v8 challenger 都必須先產生 frozen chronological artifact，完成 TRAIN → VALIDATION → CALIBRATION → TEST_UNTOUCHED，再經 promotion review 才能替換 live predictor。

上述狀態由 `jarvis.release.runtime_release_status()` 統一輸出，避免 UI、文件與 live model 版本再次漂移。

> 奇門遁甲與梅花易數都是傳統術數。盤／卦特徵不是統計機率，也不得由人工規則直接轉成固定比分或 1X2。任何 Qimen／Meihua 增量只能由盤前鎖定資料學習並以 untouched out-of-sample evidence 驗證。本專案只供研究與教育，不是投注建議。

## 已完成的範圍

- 事件所在地 IANA 時區、夏令時間、四柱與精確節氣接口。
- 時家奇門・轉盤・拆補法排盤：陰陽遁、拆補三元、十八局、天地人神四盤、值符值使、旬空、時馬、中五寄坤二、天禽隨天芮。
- 可測試的三奇升殿／入墓、六儀擊刑、門宮迫、伏吟反吟、五不遇時等結構。
- 結構化奇門知識庫、足球語義庫、完整關係矩陣與盤前解讀流程。
- 賽前 `freeze_at`、對稱更新、90 分鐘口徑、JSON／Markdown／HTML 稽核匯出。
- Live Football baseline：攻防率收縮、可選 xG、Independent Poisson、Dixon–Coles challenger、1X2 與比分候選。
- `EARLY`（T−6h）與 `LINEUP`（T−30m、雙方官方先發）雙封盤。
- 來源清單、資料快照、Football/Qimen feature 與模型規格的 SHA-256 provenance。
- StatsBomb Open Data 本地快照 provider；不猜測賽事時區、不在執行時靜默下載資料。
- 四層不可變時序 manifest：`TRAIN → VALIDATION → CALIBRATION → TEST_UNTOUCHED`。
- TRAIN-only Dixon–Coles rho、CALIBRATION-only temperature scaling 與 artifact fingerprint。
- cutoff-only TeamForm snapshot：最近 N 場、時間半衰期、xG coverage、聯盟 baseline 與來源指紋。
- log loss、Brier、RPS、1X2 accuracy、exact-score NLL / top-k 評估。
- 奇門完整 shadow features；未通過盲測前不調整 live probability。
- v8 梅花年月日時 deterministic engine 與 raw outcome feature encoder。
- 通用 TRAIN-only residual lambda fitter：`log(mu) = log(football_baseline_lambda) + X beta`，L2 且無 hidden intercept。
- Dynamic Football：opponent-adjusted attack / defence、時間衰減、optional xG、cold-start fallback。
- VALIDATION-only dynamic tuning：half-life / L2 / xG weight，且強制包含 goals-only fallback。
- Fixture context：盤前 recovery、rest、7/14 天 workload、96h congestion，並有 cutoff/availability leakage guard。
- Fixture context TRAIN fit + VALIDATION L2/alpha tuning，且 `alpha=0` 可精確退回 baseline。
- M0–M3 common runner：`M0=Football`、`M1=Football+Qimen`、`M2=Football+Meihua`、`M3=Football+Qimen+Meihua`。
- VALIDATION-only residual shrinkage tuning、CALIBRATION-only 1X2 calibration。
- TEST_UNTOUCHED-only rolling-block stability 與 paired block bootstrap confidence intervals。
- VALIDATION-only market incremental-value test，用於檢查模型是否提供去水位賽前市場之外的資訊。

## 快速開始

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Windows PowerShell：

```powershell
.venv\Scripts\Activate.ps1
```

## 使用流程

1. 在主頁輸入比賽所在地日期、時間與 IANA 時區。
2. 在「資料協議」加入盤前來源；時間需含 UTC offset。
3. 建立／重建奇門盤並完成盤前稽核。
4. 在「JARVIS 模型」建立 live predictor 輸出與盤前鎖定。
5. 在 **JARVIS v8 Dashboard** 檢查 Web App / Live Predictor / Research Stack 三層版本與 promotion gate。
6. 在 **JARVIS v8 Research Lab** 檢視 Qimen／Meihua raw features 與 v8 research stack；沒有 frozen artifact 時不會覆蓋主頁 live prediction。
7. 匯出包含方法、模型輸入、機率、鎖定資格、資料完整性與 SHA-256 的研究檔。

## 專案結構

```text
app.py                          Streamlit 主入口 / live predictor UI
pages/0_JARVIS_v8_Dashboard.py  v8 runtime / promotion 狀態
pages/1_Research_Lab.py         v8 multi-signal research UI
jarvis/release.py               Web / Live / Research 單一 release-status contract
qimen/prediction.py             Live Football predictor compatibility path
qimen/training.py               時序切分、rho 與 temperature artifacts
qimen/features.py               cutoff-only TeamForm snapshots
qimen/providers/                StatsBomb Open Data 本地 provider
meihua/                         v8 deterministic Meihua research engine/features
jarvis/football/                Dynamic strength、xG、fixture context、tuning
jarvis/research/                M0–M3、residual、calibration、stability、market benchmark
knowledge/*.json                奇門結構化知識庫
docs/                           方法、架構、資料與研究規約
tests/                          演算法不變量、leakage guard 與 Streamlit smoke tests
schemas/                        正式預測鎖 JSON Schema
```

## 方法邊界

奇門 live path 仍只執行明示方法：時家、轉盤、拆補、事件所在地民用時、晚子時換日、中五寄坤二。飛盤、置閏、茅山、真太陽時、陰盤等內容可存在於知識庫，但不混入同一計算。

梅花 v8 research engine 只執行可重現的年月日時 convention，不把體用生剋人工指定成足球勝負或比分。

Web App 與 Live Predictor 的版本必須分開理解：**Web App v8.0.0 已上線，但 Live Predictor v7.2.0 仍是 frozen champion compatibility path**。這是刻意的 promotion safety boundary，而不是部署失敗。

## 測試

```bash
pip install -r requirements-dev.txt
ruff check .
pytest -q
python tools/validate_knowledge.py
```

## 下一個主要里程碑

目前最大的實證缺口不是再增加研究 feature，而是取得足夠大的、真正盤前可得的 chronological historical dataset，凍結 M0–M3 後完成第一次 `TEST_UNTOUCHED` 實驗。只有在 Log Loss、Brier、RPS、exact-score NLL、rolling stability 與 paired block-bootstrap CI 都支持改善後，v8 challenger 才有資格進入 live promotion review。

詳見 [JARVIS v8](docs/JARVIS_V8.md)、[JARVIS 模型](docs/JARVIS_MODEL.md)、[動態足球實力](docs/DYNAMIC_STRENGTH.md)、[排盤方法](docs/QIMEN_METHOD.md)、[資料協議](docs/FOOTBALL_PROTOCOL.md)、[架構](docs/ARCHITECTURE.md)、[部署操作](docs/OPERATIONS.md) 與 [CHANGELOG.md](CHANGELOG.md)。
