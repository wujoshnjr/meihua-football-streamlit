# 梅花易數足球 AI 自主推理系統 v3.1

這一版把原本單一 `app.py` 拆成多個模組，目標是：

1. 固定起卦由 Python 精確計算，AI 不得改卦。
2. 不再要求歷史卦象完全相同，先做「結構相似度＋TF-IDF 文字相似度」。
3. GitHub Models 只負責比較相似案例、歸納校準原因與重新排序比分。
4. AI 無法使用或免費額度用完時，自動退回固定規則引擎。
5. 本場預測永遠只看賽前資料與 90 分鐘結果，不含延長賽與 PK。
6. AI 賽後建議必須經人工確認，才會存成正式校準內容。

---

## 檔案結構

```text
app.py                         Streamlit 前台
config.py                      Secrets 與設定
models.py                      資料結構
meihua_engine.py               字數、體用、本互動變、五行
score_engine.py                固定比分規則引擎
case_memory.py                 結構相似度＋TF-IDF 案例檢索
ai_reasoner.py                 GitHub Models AI 推理與賽後校準
storage.py                     GitHub CSV／Markdown 後台
report_builder.py              Markdown 完整報告
evaluation.py                  比分命中與校準摘要
knowledge_loader.py            讀取知識庫
knowledge/trigrams.json        八卦完整資料
knowledge/hexagrams.json       六十四卦完整資料
knowledge/calibration_rules.json 已驗證／待驗證校準規則
requirements.txt               Python 套件
.streamlit/secrets.toml.example Secrets 範例
tests/                         基本測試
```

---

## 升級方式

### 重要：先備份舊案例庫

先下載目前 GitHub 裡的：

```text
data/meihua_cases.csv
```

不要刪除它。新版會讀取舊欄位並自動補上新欄位。

### 上傳新版檔案

把本資料夾內的檔案上傳到 repository 根目錄，保留：

```text
knowledge/
.streamlit/
data/
reports/
tests/
```

你現有的 `data/meihua_cases.csv` 應保留，不要用空白範本覆蓋。

### requirements.txt

新版需要：

```text
streamlit
pandas
requests
openpyxl
scikit-learn
```

`scikit-learn` 用於本地 TF-IDF 與餘弦相似度；即使 GitHub Models 不可用，案例聯想仍能運作。

---

## Streamlit Secrets

在 Streamlit Community Cloud：

```text
Manage app → Settings → Secrets
```

貼入：

```toml
GITHUB_TOKEN = "你的 GitHub Contents 讀寫 Token"
GITHUB_REPO = "wujoshnjr/meihua-football-streamlit"
GITHUB_BRANCH = "main"
GITHUB_CASES_PATH = "data/meihua_cases.csv"
GITHUB_REPORTS_DIR = "reports"

GITHUB_MODELS_TOKEN = "你的 GitHub Models 唯讀 Token"
AI_ENABLED = true
AI_PROVIDER = "github_models"
AI_MODEL = "openai/gpt-4.1-mini"
AI_TOP_K_CASES = 5
AI_MAX_OUTPUT_TOKENS = 1600
AI_TEMPERATURE = 0.2
AI_REQUIRE_CONFIRMATION = true
```

兩把 Token 分開：

- `GITHUB_TOKEN`：repository `Contents = Read and write`
- `GITHUB_MODELS_TOKEN`：account `Models = Read-only`

不要把真正的 `secrets.toml` 上傳到 GitHub。

---

## 免費 AI 行為

GitHub Models 免費 API 有速率與每日額度限制。程式設計為：

- 只有按下「讓 GitHub Models AI 綜合推理」才呼叫一次。
- 頁面重新整理不會自動呼叫。
- 每個瀏覽工作階段設 20 次防誤觸上限。
- 403、404、429、逾時或服務錯誤時，自動退回固定規則結果。
- 程式不會替你開啟付費使用，也不會自動修改 GitHub 程式碼。

模型 ID 可能隨 GitHub Models catalog 調整。App 左側有「測試 AI 連線與模型」按鈕；如果預設模型不存在，可從 GitHub Models catalog 換成可用模型 ID。

---

## 預測流程

```text
賽前文字
  ↓
固定字數計算
  ↓
體卦／用卦／本卦／互卦／動爻／變卦
  ↓
固定比分規則引擎
  ↓
案例庫結構相似度
  ↓
TF-IDF 校準文字相似度
  ↓
最相似 5 場歷史案例
  ↓
GitHub Models AI 比較共同點與差異
  ↓
AI 三個比分＋風險提醒
```

AI 不會直接把舊比分複製到新比賽；Prompt 明確要求指出哪些教訓可引用、哪些差異禁止硬套。

---

## 案例庫學習方式

新版新增的重要欄位：

```text
案例ID
體用代碼
體方轉卦
用方轉卦
結構標籤
規則三個比分
AI三個比分
AI推理摘要
AI風險提醒
相似案例IDs
校準摘要
人工確認AI校準
```

賽後建議填寫：

```text
原判：
實際：
偏差：
卦象原因：
下次修正：
```

AI 可產生賽後校準建議，但只有勾選「我已閱讀並確認採用 AI 的校準摘要」後，才會把建議存入正式案例。

---

## 防止賽果倒灌

程式採取三層保護：

1. AI 賽前 Prompt 不包含本場實際比分欄位。
2. 相似案例搜尋會排除與本場同名的案例。
3. 實際比分只在「賽後校準」按鈕中傳入 AI。

因此同一場比賽即使已經存過賽後結果，也不會被當成自己的歷史參考案例。

---

## 本機測試

```bash
python -m venv .venv
source .venv/bin/activate   # Windows 使用 .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

執行基本測試：

```bash
pytest -q
```

---

## 官方技術參考

- GitHub Models：`https://docs.github.com/en/github-models/use-github-models/prototyping-with-ai-models`
- GitHub Models inference API：`https://docs.github.com/en/rest/models/inference`
- GitHub Models catalog API：`https://docs.github.com/en/rest/models/catalog`
- Streamlit Secrets：`https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management`
- scikit-learn TF-IDF：`https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.TfidfVectorizer.html`
- scikit-learn cosine similarity：`https://scikit-learn.org/stable/modules/generated/sklearn.metrics.pairwise.cosine_similarity.html`

六十四卦與八卦內容採公開古典架構作基礎，足球解讀、比分折算與校準規則為本系統自定義研究模型，不應宣稱為傳統經典的固定比分對應。
