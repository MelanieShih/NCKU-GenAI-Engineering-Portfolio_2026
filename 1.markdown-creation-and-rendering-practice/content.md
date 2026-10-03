<style>
  /* 1. 整體字體、行距與文字顏色 */
  body {
    font-family: 'Helvetica Neue', Helvetica, Arial, 'Microsoft JhengHei', sans-serif;
    line-height: 1.5;
    color: #333333;
  }

  /* 2. 大標題美化 */
  h2 {
    color: #2C3E50;
    border-bottom: 2px solid #2C3E50;
    padding-bottom: 5px;
    margin-top: 20px;
  }

  h3 {
    color: #34495e;
    margin-bottom: 5px;
  }

  /* 3. 個人簡介區塊 (Blockquote) 變成精緻卡片 */
  blockquote {
    background-color: #f8f9fa;
    border-left: 5px solid #4a90e2;
    padding: 15px 20px;
    margin: 20px 0;
    border-radius: 0 8px 8px 0;
  }

  /* 4. 表格美化 */
  table {
    width: 100%;
    border-collapse: collapse;
    margin: 20px 0;
    font-size: 0.95em;
  }
  th {
    background-color: #2C3E50;
    color: white;
    padding: 12px;
    text-align: left;
  }
  td {
    padding: 12px;
    border-bottom: 1px solid #e0e0e0;
  }

  /* 5. 程式碼區塊底色微調 */
  pre {
    background-color: #f4f6f8;
    border-radius: 8px;
    border: 1px solid #e1e4e8;
    padding: 12px;
    overflow-x: auto;
  }

  /* 6. ✅ 修正 icon：固定尺寸 + inline 對齊 */
  img.icon {
    width: 16px !important;
    height: 16px !important;
    display: inline-block !important;
    vertical-align: -2px !important;
    margin: 0 !important;
  }

  /* 7. ✅ 聯絡資訊：flex + nowrap（避免 icon/文字被拆開；pandoc HTML/PDF 都穩） */
  .contact { margin-top: 6px; }
  .contact .row {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
    margin: 2px 0;
  }
  .contact .sep { color: #999; margin: 0 2px; }
  .contact .nowrap {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    white-space: nowrap;
  }
</style>

<img src="assets/profile.jpg" alt="Melanie 照片" width="115"
     style="float: right; border-radius: 8px; margin-left: 20px; margin-bottom: 10px; border: 1px solid #ddd; object-fit: cover;">

# 施孟伶
**國立台北科技大學 工業工程管理系**

<!-- 重要：以下 HTML 區塊每一行都從第 1 欄開始（不要縮排），否則 pandoc 可能當成 code block -->
<div class="contact">
<div class="row">
<span class="nowrap"><img class="icon" src="https://api.iconify.design/mdi/email.svg?height=16&width=16" width="16" height="16" alt=""><span>t114378077@ntut.org.tw</span></span>
<span class="sep">|</span>
<span class="nowrap"><img class="icon" src="https://api.iconify.design/mdi/phone.svg?height=16&width=16" width="16" height="16" alt=""><span>0911-855-855</span></span>
</div>

<div class="row">
<span class="nowrap"><img class="icon" src="https://api.iconify.design/mdi/github.svg?height=16&width=16" width="16" height="16" alt=""><a href="https://github.com/MelanieShih">GitHub</a></span>
<span class="sep">|</span>
<span class="nowrap"><img class="icon" src="https://api.iconify.design/mdi/map-marker.svg?height=16&width=16" width="16" height="16" alt=""><span>Taipei, Taiwan</span></span>
</div>
</div>

<div style="clear: both; padding-top: 10px;"></div>

> **個人簡介 (Profile)**
> 具備扎實的資料科學與自然語言處理 (NLP) 背景，專注於檢索增強生成 (RAG) 系統開發與工作流自動化。擁有多項產學合作專案的經驗，善於連結學術理論與業界需求，期望能在 AI 系統開發與資料科學領域持續創造價值。

## 教育背景 (Education)

| 學校 / 系所 | 學位 | 就讀期間 | 核心領域與學習重點 |
| :--- | :---: | :---: | :--- |
| **台北科技大學 工業工程管理系** | 碩士 | 2024 - 迄今 | 資料科學、生成式AI系統開發 |
| **雲林科技大學 工業工程管理系** | 學士 | 2020 - 2024 | 工廠製程改善、統計資料分析 |

## 專業技能 (Technical Skills)

- **AI 與資料科學**：Natural Language Processing (NLP), RAG 架構, 機器學習
- **系統自動化**：n8n 自動化工作流, Docker 虛擬環境
- **開發工具**：Git, Gradio (UI 快速建置)

## 產學合作與專案經歷 (Professional & Project Experience)

### 產學合作案「電動車充電樁智慧客服系統」
* **專案角色**：AI 系統核心開發
* **使用技術**：`Python`, `n8n`, `Docker`, `Qdrant`
* **專案貢獻**：
  1. 針對充電樁工程公司痛點，規劃並建置自動化智慧客服流程。
  2. 運用 n8n (透過 Docker 部署於本地端) 串接 Line Bot 作為使用者介面。
  3. 優化後端 RAG 檢索模組：導入高階解析技術處理「複雜表格」，並向量化儲存至 Qdrant 資料庫。
  4. 整合 LLM API，**使客服問答準確率顯著提升，平均回應時間縮短**。
  * **系統架構說明**：`User -> Line Bot -> n8n -> Qdrant (檢索) -> LLM (生成) -> 回覆 User`

### 精實管理蹲點「經濟部數位管理共榮與加值計畫」
* **專案角色**：企劃與技術導入負責人
* **專案貢獻**：
  * 撰寫企業數位轉型計畫書，並於 2026 年 1 月成功取得核准。
  * 負責跨領域團隊溝通與專案時程管理，目前正進行計畫書細部修訂與系統架構評估，致力於將 AI 自動化流程導入企業日常管理。

## 學術研究 (Academic Research)

### 1. 知識庫檢索系統之意圖分類 (Intent Classification) 研究
- **研究動機**：優化 RAG 系統中 Query 與 Knowledge Base 的匹配精準度。
- **創新應用**：將應用於釣魚網站偵測的演算法進行改寫。其核心為計算 Query 與 Document 向量間的夾角餘弦值：`Cosine Similarity = (A · B) / (||A|| * ||B||)`。
- **目前進度**：已完成模型雛形驗證，並著手撰寫學術論文的前三章。

### 2. 傳統產業分析報告：
- 針對台灣金屬加工業進行深度調研。
- 涵蓋總體經濟趨勢、競爭者對比（如中鋼），以及公司在國際市場的戰略定位分析。

## 近期里程碑 (Upcoming Milestones)

- [x] 完成充電樁客服系統產學計畫案提案
- [x] 參與 2025 中國工業工程學會研討會發表
- [x] 準備 2026 APIEMS 國際研討會

## 附錄：技術實作精選 (Appendix: Code Sample)

以下為使用 Python 進行文本 Cosine Similarity 計算的概念雛形，應用於 RAG 系統之意圖分類任務：

```python
import numpy as np
from numpy.linalg import norm

def verify_intent_match(query_vec, document_vec, threshold=0.85):
    """
    計算 Query 與 Document 的餘弦相似度，判斷意圖是否匹配。
    應用於 RAG 檢索前過濾階段。
    """
    if norm(query_vec) == 0 or norm(document_vec) == 0:
        return False, 0.0

    similarity = np.dot(query_vec, document_vec) / (norm(query_vec) * norm(document_vec))
    is_match = similarity >= threshold

    return is_match, similarity