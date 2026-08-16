# 來源與版本政策

## 主要來源

1. [《遁甲演義》（維基文庫四庫全書本）](https://zh.wikisource.org/wiki/%E9%81%81%E7%94%B2%E6%BC%94%E7%BE%A9)：用於比對二十四節氣、陰陽十八局、九宮、值符值使、星門與傳統格局；[卷三九星旺相休囚表](https://zh.wikisource.org/wiki/%E9%81%81%E7%94%B2%E6%BC%94%E7%BE%A9_%28%E5%9B%9B%E5%BA%AB%E5%85%A8%E6%9B%B8%E6%9C%AC%29/%E5%8D%B73)用於月支旺衰實作。
2. [《奇門遁甲秘笈大全》（中國哲學書電子化計劃）](https://ctext.org/wiki.pl?chapter=828124&if=gb&remap=gb)：用於比對天盤九星、中盤八門、下盤九宮及常見判斷術語。
3. [卷二十干剋應訣](https://ctext.org/wiki.pl?chapter=254334&if=gb)：比對天地盤十干組合與古典格名。未見固定格名者只列五行組合推導。
4. [八門遇九星斷例](https://ctext.org/wiki.pl?chapter=496054&if=gb)：證明星門逐組合參的文獻脈絡；本站的 72 組摘要不冒充原文逐句轉錄。
5. [論主客](https://ctext.org/wiki.pl?chapter=961040&if=gb&remap=gb)：比對天地盤、先後動靜等主客版本，支持盤前鎖定。
6. [門迫宮迫相關卷](https://ctext.org/wiki.pl?chapter=799331&if=gb)：比對門宮生剋及迫制術語。
7. [香港天文台二十四節氣](https://www.hko.gov.hk/tc/gts/astronomy/Solar_Term.htm)：用於確認節氣的天文定義與官方 UTC+8 時刻資料。
8. [6tail/lunar-python](https://github.com/6tail/lunar-python)：程式採 `1.4.8` 的 `Solar`、`EightChar`、`getPrevJieQi(False)` 與 `getNextJieQi(False)` API。
9. [IANA Time Zone Database](https://www.iana.org/time-zones) 與 [Python `zoneinfo`](https://docs.python.org/3/library/zoneinfo.html)：保存歷史法定偏移、夏令時間與標準程式接口。IANA 在 2026-07-08 發布 2026c；匯出仍記錄執行環境實際可用版本，不把上游最新版冒充本機版本。
10. [NOAA General Solar Position Calculations](https://gml.noaa.gov/grad/solcalc/solareqns.PDF)：界定真太陽時所需的均時差、經度與時區校正；只作時間版本診斷。
11. [Hudl StatsBomb Open Data](https://github.com/hudl/open-data)：用來整理比賽事件、比賽階段、射門結果及守門事件標籤；本庫不重新散布比賽資料。
12. [StatsBomb：Modelling Team Playing Style](https://blogarchive.statsbomb.com/articles/soccer/modelling-team-playing-style/)：用來區分持球與無球事件及比賽風格維度。
13. [FIFA Football Language](https://inside.fifa.com/innovation/football-data)：用來核對跨賽事足球分析的共同框架。
14. [IFAB Laws of the Game](https://www.theifab.com/laws-of-the-game-documents/)、[Law 12](https://www.theifab.com/laws/latest/fouls-and-misconduct/) 與 [VAR Protocol](https://www.theifab.com/laws/latest/video-assistant-referee-var-protocol/)：用來界定犯規、紀律、重新開始及影像覆核語境。
15. [Dixon & Coles (1997)](https://doi.org/10.1111/1467-9876.00065)：以動態 Poisson 迴歸建模足球比分；作為 JARVIS 基準與後續低比分修正的主要論文來源。
16. [scikit-learn TimeSeriesSplit](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html)：確認時間序列評估不能用未來樣本訓練過去預測。
17. [scikit-learn Probability calibration](https://scikit-learn.org/stable/modules/calibration.html)：用於定義可靠度圖、校準評估及校準資料與測試資料分離原則。
18. [Guo et al. (2017), On Calibration of Modern Neural Networks](https://proceedings.mlr.press/v70/guo17a.html)：用於 temperature scaling 的單參數校準方法；本站把它限制在獨立 CALIBRATION split。

## 使用方式

- 古籍用來追溯符號、局表與格局，但不長篇轉錄；知識庫使用現代中文摘要。
- 古籍版本不同時，條目明示差異並標記 `knowledge_only`，不拼湊成假定的唯一標準。
- 曆法結果由固定套件版本生成；官方節氣資料用於抽樣交叉檢查。
- 足球映射、freeze_at 與情境排序是本專案設計，來源欄明示為應用規約，不冒充古法。
- 外部足球來源只定義事件語彙；「符號可能對應哪種足球行為」由 `football-semantic-composition-v2.0.0` 規約負責，兩者分欄保存。
- 306 組關係中，只有原典可追溯的固定格名標成古典格；其餘標成「古籍合參概念＋五行組合推導」。
- NOAA 公式能回答太陽時計算，不能用來證明奇門必須採真太陽時；切換時間法須另立方法版本。
- 中國哲學書電子化計劃頁面若暫時限制自動存取，資料仍只採其搜尋索引可核對的卷名與條件，不以二手網站補造成逐字古訣。
- 足球機率先以可重現基準建立，不以單場命中調參；奇門特徵只有在時間序列盲測相對基準提供穩定增量時才可啟用。

## 新增來源要求

新增內容需優先提供古籍原典、官方資料、論文或所用軟體的一手文件。二手教學可輔助理解，但不能單獨改變自動判定條件。任何新用神、主客、時間或應期規則都要同時加入來源、權威層級、schema 版本、介面標示及測試。
