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
檢索本盤相關古典義理 + 深層結構 + 足球現代應用語義
   ↓
DIVINATION_PACKET_V1
   ↓
ChatGPT 最終解讀
```

## 9.1 Deep Reading

Operation STARK 9.1 不改變起局／起卦方法，而是把交給 ChatGPT 的內容加深。

### 奇門深讀順序

**整體局勢 → 主客用神 → 宮 → 門 → 星 → 神 → 天地盤干 → 格局／空馬 → 可觀察證據／反證**

每一宮現在都會建立 `qimen_palace_deep_profile`，包含：

- 宮位環境
- 八門的行動方式
- 九星的能力／過程
- 八神的調制方式
- 天盤干的外顯觸發
- 地盤干的底層條件
- 本宮實際命中的 306 關係矩陣條目
- 旬空、驛馬、伏吟、反吟、門迫、入墓、擊刑等有效修飾
- 足球可觀察訊號、反證問題與解讀檢查點

### 梅花深讀順序

**本卦 → 上下卦內外 → 體用 → 旺衰 → 互卦 → 變卦 → 動爻 → 外應 → 可觀察證據／反證**

每次起卦現在會建立 `meihua_deep_profile`，包含：

- 本卦：目前主體結構與開局劇本
- 互卦：中段內部機制與隱性發展
- 變卦：轉折後的後段走向
- 上卦／下卦的外部／內部角色
- 上下卦五行關係
- 體用五種關係的深層解析
- 體卦旺／平／衰的承受與發用能力
- 六個動爻位置的階段意義
- 8 個足球解讀維度與反證問題

## 網站只保留五個入口

- **JARVIS**：使用說明與知識庫覆蓋率。
- **奇門起局**：時家奇門・轉盤・拆補法；輸出九宮、天地盤、八門、九星、八神、值符值使、旬空、驛馬、格局、本盤關係與深層九宮解析。
- **梅花起卦**：年月日時起卦；輸出本卦、互卦、變卦、動爻、體用、生克、旺衰、上下卦內外與深層卦象結構。
- **知識庫**：搜尋奇門／梅花原義、結構化深層解析與足球衍生語義。
- **AI 解卦包**：顯示及下載最新 `DIVINATION_PACKET_V1`，交給 ChatGPT。

原 Football ML、M0–M3、Poisson、xG、calibration、promotion、Dashboard、Research Lab 與 StatsBomb 訓練流程已從 Operation STARK 產品與程式本體移除。

## 奇門遁甲知識庫

Operation STARK 的奇門「完整性」不是捏造一個有限卦表，而是採完整基礎語彙 + 組合關係 + 動態盤面：

- 9 九宮
- 8 八門
- 9 九星
- 8 八神
- 10 十天干／三奇六儀
- 陰陽遁、局數、值符值使、旬空、驛馬
- **306 個固定關係槽位**：81 天地盤干 + 72 星門 + 72 門宮 + 81 星宮
- **8 層深讀階層**：宮、門、星、神、天盤干、地盤干、格局、空／馬
- **8 八神深層調制**：每神附一般義、足球現代應用、可觀察與反證
- 三奇得使、三奇升殿、入墓、擊刑、門迫、伏吟、反吟、五不遇時、青龍返首、飛鳥跌穴、玉女守門、三遁等格局
- 每個關係／符號可附一般解析、足球衍生義、可觀察訊號與反證條件

每次起局只把該盤真正出現的門、星、神、干、宮、關係、空馬與格局送進 AI packet，避免把整庫無差別塞給模型。

足球含意是 **modern application**，不是古籍原文，也不被 JARVIS 直接換算成勝率。

## 梅花易數知識庫

Operation STARK 包含：

- 八卦完整 catalog：卦數、五行、方位、萬物類象、人物／身體／動物／器物／環境類別、旺衰、足球衍生義、可觀察訊號與反證
- 六十四卦完整 catalog：卦序、卦名、上下卦、主題、一般解析、足球衍生義
- 體用五種關係：生體、體生用、克體、體克用、比和
- 本卦、互卦、變卦
- 上卦／下卦的外部／內部角色與五行互動
- 六個動爻位置的解讀層次與足球觀察重點
- 旺／平／衰深層規則與固定合參順序
- 8 個足球解讀維度：開局、節奏、主動權、機會創造、防守、轉換、紀律、後段
- 年月日時 deterministic 起卦規則

實際解卦不是只讀一條六十四卦摘要，而是由 JARVIS 組合：**本卦 + 上下卦 + 體用 + 旺衰 + 互卦 + 變卦 + 動爻 + 相關八卦類象 + 足球證據／反證**，再交給 ChatGPT 做最後合參。

## JARVIS / ChatGPT 分工

### JARVIS

- 計算盤／卦
- 保存方法版本
- 保存事件所在地時間與 IANA 時區
- 檢索相關知識
- 建立深層結構化上下文
- 分清古典原義與現代足球類比
- 建立不可隨意改寫的 packet SHA-256

### ChatGPT

收到 packet 後：

1. 不重新起局／起卦。
2. 先說明客觀盤象。
3. 再引用 JARVIS 提供的知識上下文與 deep profile。
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
pages/1_Qimen_Cast.py          奇門起局 + 深層九宮
pages/2_Meihua_Cast.py         梅花起卦 + 深層本互變
pages/3_Knowledge_Vault.py     知識庫搜尋
pages/4_AI_Packet.py           AI handoff packet
qimen/                         deterministic 奇門引擎
meihua/                        deterministic 梅花引擎
jarvis/qimen_relations.py      奇門 306 關係矩陣
jarvis/stark_vault.py          術數知識檢索與 deep profile 組裝
jarvis/divination_packet.py    DIVINATION_PACKET_V1
knowledge/qimen_deep_layers.json
                               奇門深讀階層、八神調制、狀態修飾
knowledge/meihua_deep_layers.json
                               梅花本互變、上下卦、體用旺衰、動爻深讀
knowledge/*.json               其他奇門／梅花知識庫與足球現代應用語義
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

Operation STARK v9.1.0 的原則仍只有一句：**JARVIS 負責盤與知識，ChatGPT 負責解。**
