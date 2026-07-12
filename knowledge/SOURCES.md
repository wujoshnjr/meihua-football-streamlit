# 知識與技術來源說明

## 傳統內容

- 《周易》六十四卦的卦名、上下卦與卦序屬古典公共領域知識。
- 本專案不大量複製現代網站的解說文字；`hexagrams.json` 與 `trigrams.json` 的文字為重新整理與足球情境轉譯。
- 足球比分規則不是古典《周易》原文，而是系統基於體用、生剋、本互動變與歷史案例建立的研究性規則。
- 單一歷史案例只能形成 `hypothesis`；在通過留出驗證前預測權重為 0。

## 技術來源

- GitHub Models 免費原型與限額：GitHub Docs
- GitHub Models REST inference/catalog：GitHub Docs
- Streamlit Community Cloud Secrets：Streamlit Docs
- 字元 n-gram TF-IDF 與 cosine similarity：由專案以純 Python 實作，避免額外原生相依套件。

所有外部服務規則、模型與免費限額都有可能變動，部署時應以官方最新文件為準。
