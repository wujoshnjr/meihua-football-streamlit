# JARVIS 術數 AI — Operation STARK

JARVIS 只做三件事：**保存術數知識、deterministic 起局／起卦、把完整盤象與相關知識整理成 AI 解讀包**。最後的綜合解局／解卦交給 ChatGPT，不由 JARVIS 自動寫死吉凶、勝率或固定比分。

## JARVIS 10 — YILIN FUSION

核心原則：

> **梅花定結構 × 易林補劇情 × ChatGPT 合參**

《焦氏易林》目前已完成 **64×64＝4096/4096** 本卦→之卦 pair coverage，使用 pinned WYG／文淵閣四庫全書數位轉錄作 base corpus。這代表轉卦矩陣與 WYG base transcription 完整；**不代表所有版本異文、標點及歷代注解已全部校勘完成**。

每條易林 record 保存林辭、原轉錄、卷／頁、source section、pinned repository commit、校語、gaiji token 與來源 label anomaly。JARVIS 不使用 AI 補寫古籍文字，也不靜默改掉來源疑點。

## 核心流程

```text
使用者問題
   ↓
JARVIS 固定時間 / 時區 / 方法
   ↓
奇門起局 或 梅花起卦
   ↓
檢索本盤相關古典義理 + 深層結構
   ↓
梅花：唯一查本卦 → 最終變卦的《焦氏易林》林辭
   ↓
原文 / provenance / project semantic profile / football 支持與反證
   ↓
DIVINATION_PACKET_V1
   ↓
ChatGPT 最終解讀
```

## 網站入口

- **JARVIS**：使用說明與知識庫覆蓋率。
- **奇門起局**：時家奇門・轉盤・拆補法；九宮、天地盤、八門、九星、八神、值符值使、旬空、驛馬、格局與深層九宮解析。
- **梅花起卦**：年月日時起卦；本卦、互卦、變卦、動爻、體用、旺衰及完整《焦氏易林》本→變情境。
- **知識庫**：搜尋奇門、梅花與完整 4096 易林轉卦。
- **AI 解卦包**：顯示與下載最新 `DIVINATION_PACKET_V1`，交給 ChatGPT。

## 奇門遁甲知識庫

- 9 九宮
- 8 八門
- 9 九星
- 8 八神
- 10 十天干／三奇六儀
- 陰陽遁、局數、值符值使、旬空、驛馬
- **306 固定關係槽位**：81 天地盤干 + 72 星門 + 72 門宮 + 81 星宮
- **8 層深讀階層**：宮 → 門 → 星 → 神 → 天盤干 → 地盤干 → 格局 → 空／馬
- 8 八神深層調制
- 三奇得使、三奇升殿、入墓、擊刑、門迫、伏吟、反吟、五不遇時、青龍返首、飛鳥跌穴、玉女守門、三遁等格局

每次只把該盤真正出現的門、星、神、干、宮、關係、空馬與格局放進 AI packet。

## 梅花易數知識庫

- 8 八卦完整 catalog
- 64 六十四卦完整 catalog
- 本卦、互卦、變卦
- 5 種體用關係
- 旺／平／衰
- 上下卦內外角色與五行互動
- 6 個動爻階段
- 8 個足球解讀維度
- 年月日時 deterministic 起卦

固定解讀順序：

**本卦 → 上下卦內外 → 體用 → 旺衰 → 互卦 → 變卦 → 動爻 → 易林本之變 → 外應／證據／反證**。

## 《焦氏易林》4096 知識層

完整 base corpus：

```text
64 本卦 × 64 之卦 = 4096 / 4096
source blocks = 64 / 64
base edition = WYG / 文淵閣四庫全書
upstream = kanripo/KR3g0029
pinned commit = 764e995ce74aa249081918ca1b0c23bbca62bec8
```

### 每條保存

- canonical `from/to` King Wen number、卦名、卦符
- `classical_text`
- `transcription_raw`
- `editorial_notes`
- `gaiji_tokens`
- source target label / anomaly flag
- source volume / section / page
- upstream repo / pinned commit
- verification / variant / semantic status

### Textual truthfulness

「4096/4096 完整」只代表：

- pair matrix 完整
- WYG base transcription 完整
- source locator 完整

以下仍獨立標成 ongoing：

- 多版本異文校勘
- 現代標點／句讀
- 後世 commentary

詳細狀態：`knowledge/yilin/collation_status.json`。

### 易林意象 ontology

`knowledge/yilin/image_ontology.json` 將林辭中常見情境整理為 project heuristic，包括道路、渡涉、車馬、阻滯、延遲、門戶、對抗、刑法、隱伏、資訊、協作、離散、權位、財貨、得失、供給、傷病、康復、轉折、崩解、水火、天候、心理與群體等。

每個 atom 都保存：

```text
match terms
→ project classical abstraction
→ football hypotheses
→ observable signals
→ counter signals
```

它不是焦氏原註，也不代表預測準確率。

## JARVIS / ChatGPT 分工

### JARVIS

- deterministic 計算盤／卦
- 保存方法版本、事件時間與 IANA 時區
- 檢索相關知識
- 精確查唯一易林本卦→變卦 pair
- 保存原典 provenance 與文本異常
- 建立 deep profile / semantic profile
- 建立 deterministic packet SHA-256

### ChatGPT

1. 不重新起局／起卦。
2. 不修改 packet 盤象或易林 lookup。
3. 先說明客觀盤象。
4. 再讀古籍原文與來源層。
5. 分開 project heuristic、football modern application。
6. 同時列支持、反證與矛盾。
7. 最後才做綜合判讀與不確定性說明。

## 方法鎖定

### 奇門

**時家奇門・轉盤・拆補法・事件所在地民用時・晚子時換日・中五寄坤二・天禽隨天芮**。

### 梅花

**年月日時起卦**。年支數 + 農曆月 + 農曆日取上卦，再加時支數取下卦與動爻；餘八取卦、餘六取爻。

### 易林 Bridge

只查：

```text
梅花本卦 → 梅花最終變卦
```

`MEIHUA_YILIN_BRIDGE` 是專案跨系統合參，不宣稱等同焦林直日法或完整復原原始易林占筮程序。

## 主要來源

- 《遁甲演義》
- 《奇門遁甲秘笈大全》及相關奇門古籍
- 《梅花易數》
- 《周易》
- 《焦氏易林》WYG／文淵閣四庫全書數位轉錄：Kanripo `KR3g0029` pinned commit
- Wikisource《易林（四庫全書本）》作 crosscheck
- Chinese Text Project《焦氏易林》作 crosscheck，不把 OCR/e-text 當唯一底本
- lunar-python 1.4.8、IANA tzdb / Python zoneinfo
- FIFA / IFAB / StatsBomb 只提供現代足球可觀察語彙，不證成術數結論

完整登錄：`knowledge/sources.json`。

## 專案結構

```text
app.py                              Streamlit 入口
pages/00_Home.py                    首頁
pages/1_Qimen_Cast.py               奇門起局
pages/2_Meihua_Cast.py              梅花 × 易林起卦
pages/3_Knowledge_Vault.py          三庫搜尋
pages/4_AI_Packet.py                AI handoff
qimen/                              deterministic 奇門引擎
meihua/                             deterministic 梅花引擎
jarvis/qimen_relations.py           奇門 306 關係矩陣
jarvis/stark_vault.py               術數知識檢索
jarvis/yilin.py                     4096 易林 loader / lookup / semantic profile
jarvis/divination_packet.py         DIVINATION_PACKET_V1
knowledge/yilin/entries/01..64.json 4096 林辭
knowledge/yilin/manifest.json       corpus contract
knowledge/yilin/source_snapshot.json pinned source hashes / anomaly registry
knowledge/yilin/collation_status.json textual completeness matrix
knowledge/yilin/image_ontology.json project semantic heuristic
tools/import_yilin_kanripo.py       reproducible corpus importer
tools/validate_yilin.py             strict Yilin validator
```

## 驗證

```bash
pip install -r requirements-dev.txt
ruff check .
python -m pytest -q
python tools/validate_knowledge.py
python tools/validate_yilin.py
```

核心原則：**JARVIS 負責盤與知識，ChatGPT 負責解。**
