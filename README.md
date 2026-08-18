# JARVIS 術數 AI — Operation STARK

JARVIS 現在只做三件事：**保存術數知識、deterministic 起局／起卦、把完整盤象與相關知識整理成 AI 解讀包**。最後的綜合解局／解卦交給 ChatGPT，不由 JARVIS 自動寫死吉凶、勝率或固定比分。

## 核心流程

```text
使用者問題
   ↓
JARVIS 固定時間 / 時區 / 方法
   ↓
奇門起局 或 梅花起卦
   ↓
檢索本盤相關古典義理 + 足球現代應用語義
   ↓
DIVINATION_PACKET_V1
   ↓
ChatGPT 最終解讀
```

## 網站只保留五個入口

- **JARVIS**：使用說明與知識庫覆蓋率。
- **奇門起局**：時家奇門・轉盤・拆補法；輸出九宮、天地盤、八門、九星、八神、值符值使、旬空、驛馬與格局。
- **梅花起卦**：年月日時起卦；輸出本卦、互卦、變卦、動爻、體用、生克與旺衰。
- **知識庫**：搜尋奇門／梅花原義、結構化摘要與足球衍生語義。
- **AI 解卦包**：顯示及下載最新 `DIVINATION_PACKET_V1`，交給 ChatGPT。

原 Football ML、M0–M3、Poisson、xG、calibration、promotion、Dashboard、Research Lab 與 StatsBomb 訓練流程已從 Operation STARK 產品與程式本體移除。

## 奇門遁甲知識庫

保留並整理現有結構化資料：

- 九宮
- 八門
- 九星
- 八神
- 十天干／三奇六儀
- 陰陽遁、局數、值符值使、旬空、驛馬
- 天地盤干、門宮、星宮、星門等關係與解盤規約
- 三奇得使、三奇升殿、入墓、擊刑、門迫、伏吟、反吟、五不遇時、青龍返首、飛鳥跌穴、玉女守門、三遁等格局
- 對應足球情境、可觀察訊號與反證條件

足球含意是 **modern application**，不是古籍原文，也不被 JARVIS 直接換算成勝率。

## 梅花易數知識庫

Operation STARK 新增：

- 八卦完整 catalog：卦數、五行、方位、基本類象、足球衍生義
- 六十四卦完整 catalog：卦序、卦名、上下卦、主題、一般解析、足球衍生義
- 體用五種關係：生體、體生用、克體、體克用、比和
- 本卦、互卦、變卦
- 六個動爻位置的解讀層次與足球觀察重點
- 旺衰與固定合參順序
- 年月日時 deterministic 起卦規則

## JARVIS / ChatGPT 分工

### JARVIS

- 計算盤／卦
- 保存方法版本
- 保存事件所在地時間與 IANA 時區
- 檢索相關知識
- 分清古典原義與現代足球類比
- 建立不可隨意改寫的 packet SHA-256

### ChatGPT

收到 packet 後：

1. 不重新起局／起卦。
2. 先說明客觀盤象。
3. 再引用 JARVIS 提供的知識上下文。
4. 分開標示古典義理與足球現代類比。
5. 同時列支持訊號、反證訊號與矛盾。
6. 最後才做綜合判讀與不確定性說明。

## 方法

### 奇門

目前鎖定：**時家奇門・轉盤・拆補法・事件所在地民用時・晚子時換日・中五寄坤二・天禽隨天芮**。不同流派不在同一張盤臨時混用。

### 梅花

目前鎖定：**年月日時起卦**。年支數 + 農曆月 + 農曆日取上卦，再加時支數取下卦與動爻；餘八取卦、餘六取爻。其他起卦法未經獨立版本化前不混入此方法。

## 主要來源

- 《遁甲演義》
- 《奇門遁甲秘笈大全》及相關奇門古籍條目
- 《梅花易數》
- 《周易》六十四卦
- Chinese Text Project 作古籍交叉核對
- lunar-python 1.4.8、IANA tzdb / Python zoneinfo 作曆法與時區實作依據
- FIFA / IFAB / StatsBomb 等只提供現代足球可觀察語彙，不證成術數結論

完整來源登錄見 `knowledge/sources.json`。

## 專案結構

```text
app.py                         Operation STARK Streamlit 入口
pages/00_Home.py               首頁
pages/1_Qimen_Cast.py          奇門起局
pages/2_Meihua_Cast.py         梅花起卦
pages/3_Knowledge_Vault.py     知識庫搜尋
pages/4_AI_Packet.py           AI handoff packet
qimen/                         deterministic 奇門引擎
meihua/                        deterministic 梅花引擎
jarvis/stark_vault.py          術數知識檢索
jarvis/divination_packet.py    DIVINATION_PACKET_V1
knowledge/*.json               奇門／梅花知識庫與足球現代應用語義
schemas/divination-packet.schema.json
                               AI packet schema
tools/validate_knowledge.py    知識庫完整性檢查
tests/                         核心引擎、知識庫、packet、Streamlit smoke tests
```

## 啟動

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

## 驗證

```bash
pip install -r requirements-dev.txt
ruff check .
pytest -q
python tools/validate_knowledge.py
```

Operation STARK v9.0.0 的原則只有一句：**JARVIS 負責盤與知識，ChatGPT 負責解。**
