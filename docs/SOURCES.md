# 來源與版本政策

## 主要來源

1. [《遁甲演義》（維基文庫四庫全書本）](https://zh.wikisource.org/wiki/%E9%81%81%E7%94%B2%E6%BC%94%E7%BE%A9)：用於比對二十四節氣、陰陽十八局、九宮、值符值使、星門與傳統格局。
2. [《奇門遁甲秘笈大全》（中國哲學書電子化計劃）](https://ctext.org/wiki.pl?chapter=828124&if=gb&remap=gb)：用於比對天盤九星、中盤八門、下盤九宮及常見判斷術語。
3. [香港天文台二十四節氣](https://www.hko.gov.hk/tc/gts/astronomy/Solar_Term.htm)：用於確認節氣的天文定義與官方 UTC+8 時刻資料。
4. [6tail/lunar-python](https://github.com/6tail/lunar-python)：程式採 `1.4.8` 的 `Solar`、`EightChar`、`getPrevJieQi(False)` 與 `getNextJieQi(False)` API。
5. [Hudl StatsBomb Open Data](https://github.com/hudl/open-data)：用來整理比賽事件、比賽階段、射門結果及守門事件標籤；本庫不重新散布比賽資料。
6. [StatsBomb：Modelling Team Playing Style](https://blogarchive.statsbomb.com/articles/soccer/modelling-team-playing-style/)：用來區分持球與無球事件及比賽風格維度。
7. [FIFA Football Language](https://inside.fifa.com/innovation/football-data)：用來核對跨賽事足球分析的共同框架。
8. [IFAB Laws of the Game](https://www.theifab.com/laws-of-the-game-documents/)、[Law 12](https://www.theifab.com/laws/latest/fouls-and-misconduct/) 與 [VAR Protocol](https://www.theifab.com/laws/latest/video-assistant-referee-var-protocol/)：用來界定犯規、紀律、重新開始及影像覆核語境。

## 使用方式

- 古籍用來追溯符號、局表與格局，但不長篇轉錄；知識庫使用現代中文摘要。
- 古籍版本不同時，條目明示差異並標記 `knowledge_only`，不拼湊成假定的唯一標準。
- 曆法結果由固定套件版本生成；官方節氣資料用於抽樣交叉檢查。
- 足球映射、freeze_at 與情境排序是本專案設計，來源欄明示為應用規約，不冒充古法。
- 外部足球來源只定義事件語彙；「符號可能對應哪種足球行為」由 `football-semantic-composition-v2.0.0` 規約負責，兩者分欄保存。

## 新增來源要求

新增內容需優先提供古籍原典、官方資料、論文或所用軟體的一手文件。二手教學可輔助理解，但不能單獨改變自動判定條件。
