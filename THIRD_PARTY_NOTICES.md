# Third-party notices

本專案透過 `requirements.txt` 安裝下列主要依賴，並未把其原始碼複製到本儲存庫：

| 套件 | 用途 | 授權 |
|---|---|---|
| [Streamlit](https://github.com/streamlit/streamlit) | Web 介面 | Apache-2.0 |
| [pandas](https://github.com/pandas-dev/pandas) | 表格呈現 | BSD-3-Clause |
| [NumPy](https://github.com/numpy/numpy) | pandas 相依與數值基礎 | BSD-3-Clause |
| [Apache Arrow / PyArrow](https://github.com/apache/arrow) | Streamlit 表格傳輸 | Apache-2.0 |
| [6tail/lunar-python](https://github.com/6tail/lunar-python) | 四柱與節氣 API | MIT；Copyright (c) 2020 6tail |

各套件的完整授權條款以其固定版本套件及上游儲存庫為準。

知識庫引用的古籍及外部頁面只提供結構化摘要與連結，未把第三方網站的完整內容納入程式碼；詳見 `docs/SOURCES.md`。

足球事件語彙參考 Hudl StatsBomb Open Data 的公開 JSON 結構、FIFA Football Language 與 IFAB Laws。本儲存庫只保存事件類別摘要與來源連結，不重新散布比賽事件資料；使用上游資料時仍須遵守各來源的授權與引用要求。
