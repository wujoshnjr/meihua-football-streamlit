# JARVIS 足球模型

JARVIS 是本專案的可稽核預測與評估計畫，不代表「超智能」或保證命中。它的目標是把統計足球基準、盤前資料鎖定、奇門結構化特徵與賽後評分分開，讓每一次改良都必須用未來不可見的資料證明。

## Phase 2.1 已實作

Champion：`jarvis-independent-poisson-v0.3.0`  
Challenger：`jarvis-dixon-coles-challenger-v0.2.0`

1. 輸入雙方盤前樣本場次、場均進失球、可選 xG／xGA、聯盟主客場進球均值、資料來源與 `data_as_of`。
2. 進球與 xG 依指定權重混合；缺少 xG 時只用進失球並發出警告。
3. 攻防率依樣本量向聯盟平均收縮，避免兩三場的極端數字主導結果。
4. Champion 以主、客兩個獨立 Poisson 分布建立 0–10 球比分矩陣；challenger 可對 0–0、0–1、1–0、1–1 套用 Dixon–Coles 校正。
5. Dixon–Coles `rho` 只能由 TRAIN-only 時間衰減擬合器產生，並以 `dc-rho-fit:<SHA-256>` 引用；不提供 artifact、超界或造成校正係數非正時直接拒絕。
6. 盤面以 `jarvis-qimen-features-v0.2.0` 轉成可訓練欄位，但保持 `SHADOW_ONLY`，對機率的權重固定為零。
7. 每筆預測先註冊 `EARLY` 或 `LINEUP`；前者資料與預測最晚 T−6h，後者最晚 T−30m 且必須有雙方官方先發來源。
8. 來源必須符合 `published_at <= retrieved_at <= data_as_of <= locked_at < event_at`。來源清單、資料快照、足球特徵、奇門特徵與模型規格各自建立 SHA-256，並記錄部署 Git commit。
9. 歷史資料先建立不可變四層 manifest；rho 只讀 TRAIN、模型選擇只讀 VALIDATION、temperature 只讀 CALIBRATION、最終宣稱只讀一次 TEST_UNTOUCHED。
10. Temperature scaling 只改 1X2 類別機率，輸出同時保存 raw／calibrated 1X2；精確比分候選仍是 raw score grid，不偽稱已校準比分。
11. `qimen.features` 用同一 cutoff 自動選取同聯賽最近 N 場，以固定 half-life 加權進失球／xG，保存有效樣本權重、xG 覆蓋與來源指紋；只有 `available_at <= cutoff` 的已知結果可用，尚未取得或未來比賽一律排除。
7. 機率明示為 `UNCALIBRATED_V0`，不把最高機率比分說成固定比分，也不作投注建議。

目前 champion 仍是獨立 Poisson。Dixon–Coles 已完成可測試的低比分校正介面，但在相同資料、相同切分下勝過 champion 前，只是 challenger，不因模型較複雜就宣稱更準。

## 計算摘要

若有 xG，觀察攻防率為：

```text
observed_rate = (1 - xg_weight) × goals_rate + xg_weight × xg_rate
```

以 `n` 場樣本及 `m` 場先驗等效場次收縮：

```text
shrunk_rate = (observed_rate × n + league_rate × m) / (n + m)
strength_index = shrunk_rate / league_rate
```

再估計：

```text
home_lambda = league_home_mean × home_attack × away_defence_weakness
away_lambda = league_away_mean × away_attack × home_defence_weakness
```

兩個期望值限制在 0.15–4.50，只是數值安全護欄；觸發時報告會保存警告。比分格的截尾質量另行輸出，不能悄悄丟失。

## 正式評估

`qimen.evaluation` 對賽前鎖定預測計算：

- 1X2 top-1 accuracy；
- multiclass log loss；
- multiclass Brier score；
- 按「主勝、和局、客勝」順序的 ranked probability score（RPS）；
- 正確比分 top-1／top-3 命中率。
- Macro-F1、和局召回率、資料 coverage；
- top-label ECE 與 classwise ECE；
- 以 `(competition, matchweek)` 為區塊的 paired bootstrap 差值與 95% 信賴區間。

Accuracy 只能回答最高機率類別是否命中；log loss、Brier 與 RPS 才會懲罰過度自信及整體機率分布。模型比較必須按比賽時間做 rolling／expanding-window 切分，不能隨機打散；校準器也只能使用與最終測試集分離的資料。

## 奇門特徵升級門檻

奇門特徵在以下條件全部成立前，不得改動機率：

1. 特徵名稱、盤法、主客映射、九星旺衰版本及方向性假說在測試前登記。
2. 每場都有開賽前鎖定時間、資料截止時間、輸入快照及不可變指紋。
3. 以相同足球資料、相同時間切分比較「足球基準」與「足球基準＋奇門」，只改一個因素。
4. 最終紀錄須預先標為 `dataset_role=TEST_UNTOUCHED` 並共用非空 `experiment_id`；至少 5,000 場，涵蓋至少兩項賽事與五個 rolling blocks。
5. 相對足球基準的 log loss 至少改善 0.5%，paired block-bootstrap 95% CI 上界小於 0，Brier 同方向，classwise ECE 惡化不超過 0.005。
6. 至少 80% rolling blocks 的 log loss 同方向改善；測試集只使用一次，依結果改特徵後必須另建 untouched set。
7. 全部條件通過只得到 `ELIGIBLE_FOR_REVIEW`；每筆還必須有有效預測鎖、非空來源 manifest、forecast horizon、校準狀態、五類 provenance 指紋與相同正式 Git commit，之後仍需人工審查。程式永不自動解除 `SHADOW_ONLY`。
8. 保存失敗結果與負增量。沒有穩定增量時，維持 `SHADOW_ONLY`。

這個門檻是防止把像「邁阿密 3–2」這種已知結果倒推成新規則。盤後能敘述事件，不等於盤前能提高機率品質。

## 已加入的資料介面

`qimen.providers.StatsBombOpenDataProvider` 讀取本地 Hudl StatsBomb Open Data 快照，正規化 competitions／matches 身份並保存原檔 SHA-256。資料中的開球時間不被假設為 UTC，也不按國家猜時區；呼叫端必須明示 IANA 時區。events 與 lineups 路徑已固定，後續特徵工程可在相同 provider contract 上擴充。

## 建立 artifacts

```bash
python tools/fit_jarvis_artifacts.py split \
  --input data/experiment_split_template.csv \
  --output artifacts/experiment.json \
  --experiment-id EXP-001 \
  --train-end 2022-12-31T23:59:59+00:00 \
  --validation-end 2023-12-31T23:59:59+00:00 \
  --calibration-end 2024-12-31T23:59:59+00:00

python tools/fit_jarvis_artifacts.py fit-rho \
  --input data/dixon_coles_training_template.csv \
  --output artifacts/rho.json

python tools/fit_jarvis_artifacts.py fit-temperature \
  --input data/calibration_template.csv \
  --output artifacts/temperature.json

python tools/fit_jarvis_artifacts.py build-features \
  --input data/historical_matches_template.csv \
  --output artifacts/features.json \
  --competition "Example League" \
  --home-team-id TEAM-A \
  --away-team-id TEAM-B \
  --cutoff 2026-01-01T12:00:00+00:00
```

模板只有 schema 示意，不足最低樣本數，因此不能直接產生正式 artifact。正式輸入的 dataset role 必須來自同一份已封存 manifest。

## 後續路線

### Phase 2.2：真實歷史訓練執行

- 匯入可重現的比賽、事件、先發與 xG 資料；先支援官方允許再利用的公開資料。
- 依聯賽、賽季與日期估計完整動態 attack／defence strength；本版已能在給定盤前 lambda 上擬合每個訓練窗的 rho。
- 加入升降級、新帥、小樣本與跨聯賽冷啟動規則。

### Phase 3：盤前情境

- 以同一截止時間加入先發、傷停、休息天數、旅行、主客場、天氣與賽程密度。
- 每項資料保存來源、發布時間、擷取時間與兩隊對稱刷新狀態。
- 使用獨立驗證資料做校準，輸出 reliability diagram 與分箱樣本數。

### Phase 4：奇門盲測與消融

- 只用版本化 shadow features；不把中文解盤文字直接當答案。
- 分別測試局、值符值使、主客宮、星門神、空馬迫墓刑與月支旺衰。
- 做 feature ablation、置換檢驗與跨賽季穩定性檢查，移除不穩定或只在單一資料切片有效的特徵。

### Phase 5：上線監控

- 保存每一版模型、資料版本、校準狀態與效能漂移。
- 當資料缺漏、校準失效或分布漂移時自動降級到基準，不輸出假精度。
- 報告永遠同時顯示模型限制、鎖定資格與歷史評估樣本數。

## 主要方法來源

- [Dixon & Coles (1997), Modelling Association Football Scores](https://doi.org/10.1111/1467-9876.00065)
- [scikit-learn TimeSeriesSplit](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html)
- [scikit-learn Probability calibration](https://scikit-learn.org/stable/modules/calibration.html)
- [Guo et al. (2017), On Calibration of Modern Neural Networks](https://proceedings.mlr.press/v70/guo17a.html)
- [Hudl StatsBomb Open Data](https://github.com/hudl/open-data)
- [《遁甲演義》卷三・九星旺相休囚](https://zh.wikisource.org/wiki/%E9%81%81%E7%94%B2%E6%BC%94%E7%BE%A9_%28%E5%9B%9B%E5%BA%AB%E5%85%A8%E6%9B%B8%E6%9C%AC%29/%E5%8D%B73)
