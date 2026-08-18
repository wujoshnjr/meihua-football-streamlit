# JARVIS 術數 AI — Operation STARK

**JARVIS 10.1 · Knowledge Completion** 把產品固定在一件事：JARVIS 保存術數知識、deterministic 起局／起卦、核對原典與來源、整理成 AI 解卦包；最後的綜合解局／解卦交給 ChatGPT。

> **周易核文本 × 梅花定結構 × 易林補劇情 × ChatGPT 合參**

JARVIS 不自動把吉凶字樣、單一卦象、爻辭或林辭換成勝率、固定比分或必然賽果。足球欄位一律是 `modern application`，必須保留可觀察訊號與反證。

## 核心流程

```text
問題 + 事件所在地時間 / IANA 時區
        ↓
奇門 deterministic 起局
或
梅花 deterministic 起卦
        ↓
梅花：核對《周易》本卦 / 互卦 / 變卦
      + 卦辭 / 彖 / 大象 / 真正動爻爻辭 / 可直接映射的小象
        ↓
體用 / 旺衰 / 上下卦 / 本互變深讀
        ↓
唯一查《焦氏易林》本卦 → 最終變卦
        ↓
來源 provenance + project heuristic + 足球支持 / 反證
        ↓
DIVINATION_PACKET_V2
        ↓
ChatGPT 最終合參
```

## 網站入口

- **JARVIS**：流程與知識覆蓋。
- **奇門起局**：時家奇門・轉盤・拆補法。
- **梅花起卦**：年月日時起卦 +《周易》原典審查 +《焦氏易林》轉卦鏡頭。
- **知識庫**：搜尋奇門、梅花、《周易》64 卦／384 爻與《焦氏易林》4096 轉卦。
- **AI 解卦包**：下載最新 `DIVINATION_PACKET_V2` 交給 ChatGPT。

## 奇門遁甲

目前正式引擎鎖定：

**時家奇門・轉盤・拆補法・事件所在地民用時・晚子時換日・中五寄坤二・天禽隨天芮。**

知識層包含：

- 9 九宮、8 八門、9 九星、8 八神、10 天干／三奇六儀。
- 陰陽遁、局數、值符值使、旬空、驛馬、刑墓迫與常用格局。
- **Core 306 Matrix**：81 天地盤干 + 72 星門 + 72 門宮 + 81 星宮。
- 8 層深讀：宮 → 門 → 星 → 神 → 天盤干 → 地盤干 → 格局 → 空／馬。
- 每次 packet 只放入實際盤面命中的關係，不把 306 全部塞給 AI。

「Core 306」只指這四類已固定的核心關係矩陣，不宣稱等於奇門所有可能組合。神×門、神×星、神×宮等 Extended Relations 屬後續審查工程。

## 梅花易數

正式引擎目前鎖定 **年月日時起卦**：年支數 + 農曆月 + 農曆日取上卦，再加時支數取下卦與動爻；餘八取卦、餘六取爻。

結構層包含：

- 8 八卦、64 六十四卦。
- 本卦、互卦、變卦。
- 體／用、五種生克關係、旺／平／衰。
- 上下卦內外角色與五行互動。
- 6 個爻位階段與 8 個足球觀察維度。

## 《周易》原典審查層

JARVIS 10.1 新增固定來源的 source-aware corpus：

```text
64 / 64 卦
384 / 384 標準爻
卦辭 / 彖 / 大象
逐爻爻辭
可直接映射的小象
乾、坤另保留用九 / 用六
upstream = kanripo/KR1a0001
pinned commit = 8284adbf9e3435d713180e24f05bf75f8b7d1d96
```

Corpus 以 8 個 shard 保存，每一卦與每一爻都帶 source file、page、pinned commit 與 source SHA-256。固定數位底本完整 **不等於** 所有歷代版本、異文、標點、注家已全部校勘。

乾卦在此底本中把大象與六小象集中在同一象傳 block；JARVIS 保守保留來源結構，不假裝能無爭議逐條切開。其他可直接映射的小象逐爻保存。

### 易義審查順序

1. 核對來源、卦序、卦名、卦符、上下卦。
2. 讀本卦卦辭／彖／大象。
3. 讀體用與旺衰。
4. 讀互卦中段機制。
5. **逐字讀真正動爻爻辭與可用小象**，再與通用爻位階段交叉。
6. 讀變卦卦辭／彖／大象。
7. 再讀《焦氏易林》本→變。
8. 產生足球候選劇本、支持、反證與矛盾。
9. 最後由 ChatGPT 合參。

`knowledge/zhouyi_review_policy.json` 明確禁止：某卦=主勝、某爻=客勝、某林辭=固定比分、吉凶字樣=統計機率。

## 《焦氏易林》4096 層

固定 base corpus：

```text
64 本卦 × 64 之卦 = 4096 / 4096
source blocks = 64 / 64
base edition = WYG / 文淵閣四庫全書
upstream = kanripo/KR3g0029
pinned commit = 764e995ce74aa249081918ca1b0c23bbca62bec8
```

每條保存林辭、raw transcription、卷／頁、source section、校語、gaiji token、來源 label anomaly 與 pinned commit。`MEIHUA_YILIN_BRIDGE` **只查梅花本卦 → 最終變卦**，是本專案跨系統合參，不宣稱等同焦林直日法。

`knowledge/yilin/image_ontology.json` 是 JARVIS 的 project heuristic：把道路、渡涉、車馬、阻滯、門戶、對抗、刑法、資訊、協作、離散、得失、傷病、康復、轉折等意象轉成候選足球情境、observable 與 counter-signals。它不是焦氏原註，也不是預測準確率。

## DIVINATION_PACKET_V2

`DIVINATION_PACKET_V2` 新增：

- 實際排盤／起卦使用的事件所在地 aware datetime。
- `zhouyi_review`：本／互／變原典、真正動爻、source audit、易義審查規約。
- `yilin_bridge`：唯一的本→變易林條目，不再在 `knowledge_context` 重複一份。
- 正式 JSON Schema：`schemas/divination_packet_v2.schema.json`。
- deterministic SHA-256。

ChatGPT 的責任是：不重起盤、不改 packet；先讀盤象與原典，再分開 project heuristic 與 football modern application；保留矛盾與反證，最後才做綜合判讀。

## 來源真實性

主要來源登錄於 `knowledge/sources.json`：

- 《遁甲演義》與相關奇門古籍。
- 《梅花易數》。
- 《周易》：Kanripo `KR1a0001` pinned transcription；Wikisource / Chinese Text Project 作 crosscheck。
- 《焦氏易林》：Kanripo `KR3g0029` WYG pinned transcription；Wikisource / Chinese Text Project 作 crosscheck。
- lunar-python 1.4.8、IANA tzdb / Python zoneinfo。
- FIFA / IFAB / StatsBomb 只提供足球可觀察語彙，不證成術數有效。

原典數位轉錄、後世注解、專案摘要與足球現代應用必須分層；不得用 AI 補寫古籍或靜默修改來源疑點。

## 主要結構

```text
app.py
pages/00_Home.py
pages/1_Qimen_Cast.py
pages/2_Meihua_Cast.py
pages/3_Knowledge_Vault.py
pages/4_AI_Packet.py
qimen/                              deterministic 奇門
meihua/                             deterministic 梅花
jarvis/qimen_relations.py           Qimen Core 306
jarvis/stark_vault.py               術數知識檢索
jarvis/zhouyi.py                    周易 source review / search
jarvis/yilin.py                     易林 4096 lookup / semantic profile
jarvis/divination_packet.py         DIVINATION_PACKET_V2
knowledge/zhouyi/entries/01..08.json 周易 64/384 corpus shards
knowledge/zhouyi/manifest.json
knowledge/zhouyi_review_policy.json
knowledge/yilin/entries/01..64.json
schemas/divination_packet_v2.schema.json
tools/import_zhouyi_kanripo.py
tools/validate_zhouyi.py
tools/import_yilin_kanripo.py
tools/validate_yilin.py
```

## 驗證

```bash
pip install -r requirements-dev.txt
python tools/import_zhouyi_kanripo.py --check
python tools/validate_zhouyi.py
python tools/import_yilin_kanripo.py
ruff check .
python -m pytest -q
python tools/validate_knowledge.py
python tools/validate_yilin.py
```

**JARVIS 負責盤、原典與知識；ChatGPT 負責解。**
