# 知識庫來源與資料分層

## 古典經文

六十四卦的卦辭、彖傳、大象、六爻爻辭、小象，以及《文言》《說卦》《繫辭》《序卦》《雜卦》，取自 `@freizl/yijing` 2.1.0 的繁體中文結構化資料，並保留其 MIT 授權聲明。該資料專案列出的底層對照來源包括：

- [維基文庫《周易》](https://zh.wikisource.org/wiki/%E5%91%A8%E6%98%93)
- [中國哲學書電子化計劃《周易》](https://ctext.org/book-of-changes/zh)
- [@freizl/yijing](https://github.com/freizl/yijing)

古典原文屬公有領域。結構化資料的授權與作者資訊見專案根目錄 `THIRD_PARTY_NOTICES.md`。

## 《焦氏易林》

4,096 條林辭取自 Kanripo 的 `KR3g0029 焦氏易林-漢-焦贛.txt`，底本標示為《欽定四庫全書》十六卷本。本專案固定使用 `kr-shadow/KR3` commit `eca6cb15ba5ee47a4267fde608db2ecd2d5f55ac` 的快照；來源檔案另記其上游 Kanripo commit `764e995c`。該資料庫以 CC0 1.0 釋出。

- [Kanripo／KR3 固定版本](https://github.com/kr-shadow/KR3/blob/eca6cb15ba5ee47a4267fde608db2ecd2d5f55ac/KR3g0029%20%E7%84%A6%E6%B0%8F%E6%98%93%E6%9E%97-%E6%BC%A2-%E7%84%A6%E8%B4%9B.txt)
- [CC0 1.0 授權](https://github.com/kr-shadow/KR3/blob/master/LICENSE)

`tools/build_jiaoshi_yilin.py` 依每章固定的六十四變次序建立 `entries[本卦][之卦]` 索引，並硬性驗證 64×64＝4,096 個組合全部存在且非空。底本「艮之」章第十筆標為「小過」，但該位置依固定次序應為「小畜」；資料庫只把索引標題校正為「小畜」，林辭原文完全保留，並在 `source_label_corrections` 留下紀錄。

## 本專案整理

- 六十四卦的上下卦與六爻二進位結構由排卦引擎交叉驗證。
- 互卦、錯卦與綜卦由六爻結構機械計算，不是人工解讀。
- 八卦數、體用、互卦、變卦與五行循環整理於 `meihua_principles.json`。
- `meaning_overview` 是便於索引的現代簡要提要，不針對任何比賽或事件下判斷。

## 完整性界線

本知識庫所稱「完整」是指：

- 八個經卦全部具備結構與傳統類象欄位。
- 六十四卦全部具備卦辭、彖傳、大象。
- 三百八十四爻全部具備爻辭與小象。
- 乾坤的用九／用六與文言已收錄。
- 五篇易傳附錄已收錄。
- 《焦氏易林》64 個本卦各有 64 個之卦，共 4,096 條非空林辭。

這不表示收錄歷代所有注家、所有版本異文或所有占法；《焦氏易林》的「完整」特指上述四庫本資料快照的 4,096 組索引完整，不代表已完成跨版本文字校勘。版本差異應由人工文獻校勘，不由排卦程式自行裁決。
