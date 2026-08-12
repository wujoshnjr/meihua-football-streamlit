# 獨立盲測預測評估規格 v1

## 目的與邊界

這個工具用來判斷「哪一版解卦規則在未見資料上真的較準」，不改寫梅花排卦公式，也不被 `app.py`、`meihua_engine.py` 或知識庫載入。

- 排卦層：只處理賽前文字、`event_at` 時間環境與完整卦盤。
- 預測層：在另一份 CSV 鎖定 1X2 機率、比分、進球區間及 BTTS。
- 賽果層：比賽後在另一份 CSV 登錄九十分鐘賽果。
- 評估層：只讀前兩份已鎖定資料，按 `event_at` 先後計分。

這項改動不等於已證明梅花易數具有預測效力，也不保證立即提高命中率；它建立的是能排除賽後污染、比較版本與停止無效調參的實證閉環。

## 為何不能只看命中率

只輸出「主／和／客」會隱藏信心差異。將 51% 與 95% 的預測都算成同一次命中，無法懲罰過度自信，也難以校準規則。因此 v1 要求每場固定輸出：

- `p_body`：體方九十分鐘獲勝機率。
- `p_draw`：九十分鐘和局機率。
- `p_use`：用方九十分鐘獲勝機率。
- 三者各自嚴格介於 0 與 1，合計必須為 1。

主要指標：

- 1X2 Brier：`sum((p_k - o_k)^2)`，範圍 0～2，越低越好。
- 1X2 log loss：`-ln(p_observed)`，越低越好。
- 類別校準：同一機率區間的平均預測與實際發生率比較。
- Top-1 命中率：只作易讀輔助，不作唯一優化目標。
- 精確比分 Top 1、進球區間及 BTTS：只在該欄有預測時納入各自分母。

Gneiting 與 Raftery 說明 proper scoring rules 會鼓勵誠實的機率預測；Wheatcroft 針對足球 1X2 的研究則支持同時重視 log score，而不是只依賴 RPS。

## 時間與樣本分類

每筆預測必須保存：

- `event_at`：官方排定開球時間，須含 UTC 位移。
- `freeze_at`：固定由系統計算為 `event_at − 6 小時`。
- `locked_at`：預測真正鎖定的時間，須含 UTC 位移。
- `sample_class`：`CLEAN_BLIND`、`EXPOSED_BLIND` 或 `POSTMATCH_ANALYSIS`。

主要準確率報告只使用 `CLEAN_BLIND`，且程式強制 `locked_at <= freeze_at`。`EXPOSED_BLIND` 與 `POSTMATCH_ANALYSIS` 可個別產生探索性報告，但不可混入主要成績。

Nosek 等人的預註冊研究指出，在得知結果前固定假設與分析方式，有助區分 prediction 與 postdiction。scikit-learn 的技術文件也說明：若使用預測時不可能取得的資訊，就會造成過度樂觀的驗證結果；時間相關資料應以未來觀測作測試，不應隨機打散。

## 鎖定指紋

`lock` 會驗證欄位並對預測內容產生 SHA-256：

```bash
python tools/evaluate_forecasts.py lock \
  --input data/forecast_drafts.example.csv \
  --output /tmp/forecasts_locked.csv
```

鎖定後若修改球隊、時間、機率、比分、版本、來源或樣本分類，後續讀取會因 `forecast_sha256` 不符而停止。

賽果使用另一個指紋與檔案：

```bash
python tools/evaluate_forecasts.py lock-results \
  --input data/result_drafts.example.csv \
  --output /tmp/results_locked.csv
```

預測檔不得加入實際賽果；賽果檔不得加入或覆寫預測機率。

## 評估

```bash
python tools/evaluate_forecasts.py evaluate \
  --forecasts /tmp/forecasts_locked.csv \
  --results /tmp/results_locked.csv \
  --sample-class CLEAN_BLIND \
  --minimum-samples 100 \
  --output /tmp/evaluation.json
```

程式會：

1. 驗證兩份檔案的指紋與唯一 `forecast_id`。
2. 只連接相同 `forecast_id` 的預測和賽果。
3. 依 `event_at` 排序。
4. 為每場建立只使用更早賽果的 expanding base-rate benchmark；同時開球的比賽不互相偷看結果。
5. 用 Laplace `+1` 平滑避免早期零機率。
6. 產生整體和各 `method_version` 的命中率、Brier、log loss、skill、校準及附加市場命中率。

`skill = 1 - model_loss / baseline_loss`；只有大於 0 才代表優於只使用過去賽果頻率的簡單基準。

預設 promotion gate 要求：

- 至少 100 場符合資格的盲測；以及
- Brier skill 與 log-loss skill 同時大於 0。

100 場是保守的專案版本晉升門檻，不是普遍適用的統計定理。可調整門檻，但必須先寫進方法版本，不能看到成績後才更換。

## 欄位

### 預測檔

| 欄位 | 規則 |
|---|---|
| `forecast_id` | 全域唯一 |
| `casting_id` | 對應排卦紀錄，不得空白 |
| `method_version` | 解卦規則版本；規則改動必須升版 |
| `sample_class` | 三種固定分類之一 |
| `event_at` | 含時區 ISO 8601 |
| `freeze_at` | 可留空，由程式填入 `event_at − 6h` |
| `locked_at` | 真正鎖定時間；不可由賽後回填 |
| `body_name`、`use_name` | 與排卦一致 |
| `p_body`、`p_draw`、`p_use` | 合計 1，且各自大於 0、小於 1 |
| `top1_score` | 選填，格式 `體方進球-用方進球` |
| `goal_band` | 選填：`0-1`、`2-3`、`4+` |
| `btts` | 選填：`YES` 或 `NO` |
| `signal_key` | 建議保存 `本卦|動爻|變卦`，只作分組診斷 |
| `source_grade` | A、B、C |
| `source_urls` | A／B 必填；多個網址可用空格分隔 |
| `forecast_sha256` | 由 `lock` 產生 |

### 賽果檔

| 欄位 | 規則 |
|---|---|
| `forecast_id` | 對應預測 |
| `result_recorded_at` | 含時區 ISO 8601 |
| `body_goals`、`use_goals` | 九十分鐘加補時，不含延長賽或 PK |
| `result_source_url` | 官方或可靠賽果來源 |
| `result_sha256` | 由 `lock-results` 產生 |

## 如何用數據改進規則

每次只改一個已命名的 `method_version`，新舊版本保留，不覆寫歷史預測。先看主要 `CLEAN_BLIND` 報告：

1. 若 Top-1 命中提高、log loss 反而惡化，代表新規則可能更過度自信，不應晉升。
2. 若整體改善但某一類來源或賽事惡化，先檢查資料定義與來源對稱性，不要直接改卦義。
3. 若新規則未同時優於 prequential baseline，就保留為探索版本。
4. 若日後加入 Dixon–Coles、Elo、賠率或其他足球先驗，只能作獨立 benchmark／ensemble，不能回寫起卦文字或改動已鎖定的卦盤。

Dixon 與 Coles 的原始研究以 Poisson regression 處理動態球隊表現和低比分依存，是足球統計基準的合理候選；但本 v1 沒有偷偷加入該模型或賽果特徵。

## 研究與技術來源

- Gneiting, T. & Raftery, A. E. (2007), [Strictly Proper Scoring Rules, Prediction, and Estimation](https://doi.org/10.1198/016214506000001437).
- Wheatcroft, E. (2021), [Evaluating probabilistic forecasts of football matches: the case against the ranked probability score](https://doi.org/10.1515/jqas-2019-0089).
- Dixon, M. J. & Coles, S. G. (1997), [Modelling Association Football Scores and Inefficiencies in the Football Betting Market](https://doi.org/10.1111/1467-9876.00065).
- Nosek, B. A. et al. (2018), [The preregistration revolution](https://doi.org/10.1073/pnas.1708274114).
- scikit-learn developers, [Common pitfalls: data leakage](https://scikit-learn.org/stable/common_pitfalls.html#data-leakage).
- scikit-learn developers, [Cross validation of time series data](https://scikit-learn.org/stable/modules/cross_validation.html#cross-validation-of-time-series-data).
- scikit-learn developers, [Probability calibration](https://scikit-learn.org/stable/modules/calibration.html).
