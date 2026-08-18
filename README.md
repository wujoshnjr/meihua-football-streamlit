# JARVIS 足球賽前研究系統

JARVIS 是一個可重現、可稽核的足球賽前研究系統，結合足球統計 baseline、奇門遁甲 shadow features、梅花易數 live/research features，以及嚴格的 chronological experiment contract。

## 目前版本狀態

- **Web App v8.1.0**：Streamlit 已提供新的 JARVIS 首頁、Football + 梅花 Live Predictor、Audit Workbench、v8 Dashboard 與 Research Lab。
- **Live Predictor v7.2.0 Football base**：數值 base 仍使用既有 frozen Football champion compatibility path；目前核心是 Independent Poisson。
- **Meihua live bridge**：梅花年月日時卦象、體用／互卦／變卦、raw features 與 SHA-256 fingerprint 已正式進入每場 Live computation。
- **M2 probability weight 受 artifact gate 控制**：只有 M2 完成 TRAIN fit、VALIDATION shrinkage、M2 專屬 CALIBRATION、TEST_UNTOUCHED promotion review 與人工批准後，`artifacts/live_meihua.json` 才能改動 Football λ 與 1X2。
- **Research generation：JARVIS v8**：Dynamic Football、xG tuning、fixture context、M0–M3、calibration、rolling stability、paired block bootstrap 與 market incremental-value test 已在程式與網頁可見。
- **模型不會自動升級**：Web App 升版不代表 research challenger 已自動取得數值權重；任何 promotion 都必須有 frozen chronological artifact。

上述 Web / Football base 狀態由 `jarvis.release.runtime_release_status()` 統一輸出。梅花 production gate 由 `jarvis.live_meihua` 驗證。

> 奇門遁甲與梅花易數都是傳統術數。盤／卦特徵不是統計機率，也不得由人工規則直接轉成固定比分或 1X2。任何 Qimen／Meihua 數值增量只能由盤前鎖定資料學習並以 untouched out-of-sample evidence 驗證。本專案只供研究與教育，不是投注建議。

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
- **Production Meihua live bridge**：每場正式建立梅花 snapshot / feature fingerprint；只接受完整 promotion-approved M2 deployment artifact。
- 通用 TRAIN-only residual lambda fitter：`log(mu) = log(football_baseline_lambda) + X beta`，L2 且無 hidden intercept。
- Dynamic Football：opponent-adjusted attack / defence、時間衰減、optional xG、cold-start fallback。
- VALIDATION-only dynamic tuning：half-life / L2 / xG weight，且強制包含 goals-only fallback。
- Fixture context：盤前 recovery、rest、7/14 天 workload、96h congestion，並有 cutoff/availability leakage guard。
- Fixture context TRAIN fit + VALIDATION L2/alpha tuning，且 `alpha=0` 可精確退回 baseline。
- M0–M3 common runner：`M0=Football`、`M1=Football+Qimen`、`M2=Football+Meihua`、`M3=Football+Qimen+Meihua`。
- VALIDATION-only residual shrinkage tuning、CALIBRATION-only 1X2 calibration。
- TEST_UNTOUCHED-only rolling-block stability 與 paired block bootstrap confidence intervals。
- VALIDATION-only market incremental-value test，用於檢查模型是否提供去水位賽前市場之外的資訊。
- preregistered generic promotion review：只輸出 `ELIGIBLE_FOR_HUMAN_REVIEW` / `KEEP_CHALLENGER`，永不自動 promotion。

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

1. 從首頁開啟 **Live Predictor**，輸入事件所在地日期、時間與盤前 Football snapshot。
2. 系統建立 frozen Football base，同時正式建立梅花年月日時 snapshot、raw features 與 SHA-256。
3. 若 repository 有合法 `artifacts/live_meihua.json`，M2 依 frozen residual / alpha / calibration 改動 λ 與 1X2；沒有 artifact 時機率精確維持 Football baseline。
4. 需要奇門九宮、來源證據、盤前鎖定與報告匯出時使用 **Audit Workbench**。
5. 在 **JARVIS v8 Dashboard** 檢查 Web / Live / Research 與 promotion gate。
6. 在 **Research Lab** 檢視 Qimen／Meihua raw features 與 M0–M3 research stack。

## 專案結構

```text
app.py                          Streamlit navigation shell
pages/00_Home.py                JARVIS product home
pages/3_Live_Meihua.py          Football + Meihua production live page
pages/2_Live_Predictor.py       完整奇門／來源／鎖定 Audit Workbench
pages/0_JARVIS_v8_Dashboard.py  v8 runtime / promotion 狀態
pages/1_Research_Lab.py         v8 multi-signal research UI
jarvis/live_meihua.py           production Meihua artifact gate + live M2 scorer
artifacts/README.md              M2 live deployment artifact contract
jarvis/release.py               Web / Football base / Research release contract
qimen/prediction.py             frozen Football predictor compatibility path
qimen/training.py               時序切分、rho 與 temperature artifacts
qimen/features.py               cutoff-only TeamForm snapshots
qimen/providers/                StatsBomb Open Data 本地 provider
meihua/                         deterministic Meihua engine/features
jarvis/football/                Dynamic strength、xG、fixture context、tuning
jarvis/research/                M0–M3、residual、calibration、stability、market、promotion
knowledge/*.json                奇門結構化知識庫
docs/                           方法、架構、資料與研究規約
tests/                          演算法不變量、leakage guard 與 Streamlit smoke tests
schemas/                        正式預測鎖 JSON Schema
```

## 梅花正式部署邊界

「正式接入」和「已證明提高準確率」是兩件事。JARVIS v8.1 現在每場 live prediction 都會計算梅花；但目前 repository 沒有真實 M2 promoted artifact，所以 production gate 不允許任意手寫術數權重改變機率。

未來 `artifacts/live_meihua.json` 必須同時綁定：M2 family、MEIHUA feature schema、TRAIN residual、VALIDATION-selected alpha、Football baseline / score-model config、M2 CALIBRATION artifact、TEST_UNTOUCHED promotion report、人工批准時間／批准者、source commit 與 canonical artifact SHA-256。任何一項不一致都會拒絕載入。

## 測試

```bash
pip install -r requirements-dev.txt
ruff check .
pytest -q
python tools/validate_knowledge.py
```

## 下一個主要里程碑

目前最大的實證缺口仍是足夠大的、真正盤前可得 chronological historical dataset。下一步應建立真實 M0/M2 experiment，凍結 TRAIN / VALIDATION / CALIBRATION 後才第一次讀取 `TEST_UNTOUCHED`。只有 Log Loss、Brier、RPS、exact-score NLL、rolling stability 與 paired block-bootstrap CI 支持改善，才可生成 live M2 deployment artifact。

詳見 [JARVIS v8](docs/JARVIS_V8.md)、[JARVIS 模型](docs/JARVIS_MODEL.md)、[Promotion Review](docs/PROMOTION_REVIEW.md)、[動態足球實力](docs/DYNAMIC_STRENGTH.md)、[資料協議](docs/FOOTBALL_PROTOCOL.md)、[架構](docs/ARCHITECTURE.md)、[部署操作](docs/OPERATIONS.md) 與 [CHANGELOG.md](CHANGELOG.md)。
