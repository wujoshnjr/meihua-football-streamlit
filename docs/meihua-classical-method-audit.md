# 梅花古法方法審查 — JARVIS 10.2

本文件說明 JARVIS 如何在不改動 deterministic 卦象的前提下，先辨起卦方法，再決定《周易》文本、體用、旺衰、互變與外應的相對審查權重。

> **先辨起卦法 → 梅花定結構 → 周易依方法決定權重 → 易林補轉變情境 → 外應驗內卦 → ChatGPT 合參**

## 1. 為什麼要做方法審查

JARVIS 10.1 已能提供《周易》64 卦、384 標準爻與《焦氏易林》4096 轉卦，但「有原典」不等於「每種梅花起卦法都應用同一權重」。

若不先辨方法，最容易出現的錯誤是：

- 年月日時先天數法一律把動爻爻辭放到最高權重；
- 忽略體用、生克、旺衰與互變的主要骨架；
- 把三要、十應或外應在沒有當時紀錄的情況下由 AI 補造；
- 把通用爻位階段直接換成固定比賽分鐘；
- 把古典吉凶字樣直接換成現代勝率或比分。

JARVIS 10.2 因此加入 `MEIHUA_CLASSICAL_METHOD_AUDIT`。

## 2. 目前 implemented 方法

目前正式 engine 只有：

```text
年月日時起卦
→ XIANTIAN_NUMBER_METHOD
```

固定計算仍由 `meihua.engine.build_meihua_snapshot` 完成：

```text
年支數 + 農曆月 + 農曆日 → 上卦
再 + 時支數 → 下卦
總數餘六 → 動爻
```

方法審查層**不能改本卦、互卦、變卦、動爻、體用或旺衰**。

## 3. XIANTIAN_NUMBER_METHOD 權重

目前年月日時法採：

1. deterministic 本卦與體／用定位；
2. 體用生克 + 體卦旺衰；
3. 互上／互下對體作用；
4. 變用對體作用；
5. 動靜、內外與真正有記錄的外應；
6. 《周易》卦辭／彖／象／動爻作 `SUPPORTING` source-aware review；
7. 《焦氏易林》本卦→最終變卦補 transformation context；
8. ChatGPT 最終合參。

因此：

```text
周易動爻原文 = 要讀
但不是單句最高裁決器
```

若動爻原文與體用旺衰、互變結構形成張力，packet 必須保留張力，不可硬把其中一層刪掉。

## 4. 體一用百：Body/Use Network

JARVIS 10.2 不再只輸出一個 `body_use_relation` 當完整梅花含意，而是固定建立：

```text
original_use  → immediate
mutual_upper  → middle
mutual_lower  → middle
changed_use   → late
```

每層都保存：

- trigram
- relation_to_body
- neutral relation class
- relative stage

這些是相對作用層，不是固定分鐘，也不是投票權重。

## 5. 三要、十應、外應

目前 UI 尚未在占測當時記錄三要、十應與其他外應，所以 packet 必須明示：

```text
three_essentials = NOT_RECORDED
ten_responses = NOT_RECORDED
external_omens = NOT_RECORDED
```

重要規則：

- 缺失就是缺失；
- 不讓 AI 想像一個外應；
- 不把賽後事件補成賽前外應；
- 未來若實作，必須保存 observation timestamp、來源與鎖定指紋。

## 6. 真生真克與證據強度

現代足球映射不能只因「某物屬金／木／水／火／土」就給同樣權重。

JARVIS 對 modern application 的最低要求是：

```text
source_basis
abstract_meaning
possible_scenario
observable_signals
counter_signals
confidence_note
```

也就是說：

> 類象只是候選鏡頭；真正有沒有作用，要看可觀察證據與反證。

這仍不把術數變成統計勝率模型。

## 7. HOUTIAN_OBJECT_METHOD

JARVIS 已保留後天物卦法的 knowledge profile，但目前：

```text
status = knowledge_only_not_implemented
```

在 deterministic engine、UI 輸入規格與 golden tests 完成前，不得宣稱可正式起後天物卦。

未來若實作，至少要保存：

- 物象是什麼；
- 誰在何時觀察；
- 物象如何歸卦；
- 方位如何取得；
- 時數如何定爻；
- 《周易》爻辭／卦辭如何提升為 `PRIMARY_SUPPORT`；
- 原始觀察不可事後修改。

## 8. Review Summary

每個梅花 `DIVINATION_PACKET_V2` 現在進一步產生 `review_summary`：

- `method_weighting`
- `relation_signals`
- `contradiction_register`
- `uncertainty_register`
- `source_coverage_audit`

其用途不是自動下吉凶，而是確保 ChatGPT 在解讀前先看到：

1. 本次到底採什麼方法；
2. 哪些層同向、哪些層有張力；
3. 哪些材料真的有來源；
4. 哪些古法層目前缺資料；
5. 哪些足球含意只是 project heuristic。

## 9. 不可破壞邊界

JARVIS 不做：

- 某卦 = 主勝；
- 某爻 = 客勝；
- 某林辭 = 固定比分；
- 吉／凶 = 統計勝率；
- 賽後事件回填賽前外應；
- AI 補古籍缺字；
- 方法未實作卻宣稱已可用。

JARVIS 只負責：

> **起卦、方法審查、原典審查、知識檢索、矛盾與不確定性登錄、AI handoff。**

最終綜合解卦仍由 ChatGPT 完成。
