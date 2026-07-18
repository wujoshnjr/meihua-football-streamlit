# 知識庫來源與資料分層

## 古典經文

六十四卦的卦辭、彖傳、大象、六爻爻辭、小象，以及《文言》《說卦》《繫辭》《序卦》《雜卦》，取自 `@freizl/yijing` 2.1.0 的繁體中文結構化資料，並保留其 MIT 授權聲明。該資料專案列出的底層對照來源包括：

- [維基文庫《周易》](https://zh.wikisource.org/wiki/%E5%91%A8%E6%98%93)
- [中國哲學書電子化計劃《周易》](https://ctext.org/book-of-changes/zh)
- [@freizl/yijing](https://github.com/freizl/yijing)

古典原文屬公有領域。結構化資料的授權與作者資訊見專案根目錄 `THIRD_PARTY_NOTICES.md`。

## 《焦氏易林》

顯示用林辭採用維基文庫的繁體標點校對本，並固定保存 `Subiectum/Zhouyi` commit `3ea1b1e93dc8c5dfbdf11c338f4c38a8825194a0` 的 CSV 鏡像快照。維基文庫標點與協作整理內容依 CC BY-SA 4.0 提供，署名與編輯歷史可由作品頁查閱。

- [維基文庫《焦氏易林》](https://zh.wikisource.org/wiki/%E7%84%A6%E6%B0%8F%E6%98%93%E6%9E%97)
- [固定標點快照](https://github.com/Subiectum/Zhouyi/blob/3ea1b1e93dc8c5dfbdf11c338f4c38a8825194a0/%E8%B1%A1%E6%95%B0/%E7%84%A6%E6%B0%8F%E6%98%93%E6%9E%97.csv)
- [CC BY-SA 4.0 授權](https://creativecommons.org/licenses/by-sa/4.0/)

維基文庫快照有三條明確標示「原缺」：大壯之睽、井之巽、井之渙。本專案以 Kanripo `KR3g0029 焦氏易林-漢-焦贛.txt` 的《欽定四庫全書》十六卷本補足原文，並只加入句讀標點、不改動字詞。Kanripo 快照固定於 `kr-shadow/KR3` commit `eca6cb15ba5ee47a4267fde608db2ecd2d5f55ac`，來源檔案另記上游 commit `764e995c`，以 CC0 1.0 釋出。

- [Kanripo／KR3 固定版本](https://github.com/kr-shadow/KR3/blob/eca6cb15ba5ee47a4267fde608db2ecd2d5f55ac/KR3g0029%20%E7%84%A6%E6%B0%8F%E6%98%93%E6%9E%97-%E6%BC%A2-%E7%84%A6%E8%B4%9B.txt)
- [CC0 1.0 授權](https://github.com/kr-shadow/KR3/blob/master/LICENSE)

`tools/build_jiaoshi_yilin.py` 建立 `entries[本卦][之卦]` 索引，硬性驗證 64×64＝4,096 個組合全部存在、非空、含標點並以句末標點結束。標點快照的兩個非卦名索引會依固定六十四變次序校正；三條原缺補足記錄在 `source_completion_notes`。Kanripo 原始快照及其一筆索引校正則另存於 `base_source_label_corrections`，兩種來源不混稱為同一版本。

## 本專案整理

- 六十四卦的上下卦與六爻二進位結構由排卦引擎交叉驗證。
- 互卦、錯卦與綜卦由六爻結構機械計算，不是人工解讀。
- 八卦數、體用、互卦、變卦與五行循環整理於 `meihua_principles.json`。
- `meaning_overview` 是便於索引的現代簡要提要，不針對任何比賽或事件下判斷。
- `conditional_trigram_meanings.json` 的古典核心以[《周易・說卦》](https://ctext.org/book-of-changes/shuo-gua/zh)及[《梅花易數》卷一](https://zh.wikisource.org/wiki/%E6%A2%85%E8%8A%B1%E6%98%93%E6%95%B8/%E5%8D%B7%E4%B8%80)八卦類象為底層；其中足球義項、條件訊號與優先級是本專案應用層，不冒充古籍原文。

## 完整性界線

本知識庫所稱「完整」是指：

- 八個經卦全部具備結構與傳統類象欄位。
- 八個經卦各具八個條件式義項與六條規則，共 64 義項、48 規則。
- 六十四卦全部具備卦辭、彖傳、大象。
- 三百八十四爻全部具備爻辭與小象。
- 乾坤的用九／用六與文言已收錄。
- 五篇易傳附錄已收錄。
- 《焦氏易林》64 個本卦各有 64 個之卦，共 4,096 條非空、完整標點林辭。

這不表示收錄歷代所有注家、所有版本異文或所有占法；《焦氏易林》的「完整」特指上述標點顯示本的 4,096 組索引與標點覆蓋完整，不代表已完成跨版本文字校勘。版本差異應由人工文獻校勘，不由排卦程式自行裁決。
