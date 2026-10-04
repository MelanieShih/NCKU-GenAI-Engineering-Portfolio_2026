# HW3：打造你的個人知識 RAG 系統

> **課程作業｜Build Your Personal RAG — From Raw Data to Agent Skill**
> 繳交方式：上傳至 GitHub Classroom

---

## Deadline

| 階段 | 截止時間 |
|---|---|
| **系統可執行版（data_update + rag_query）** | 2026/4/14 23:59 |
| **完整版（含 skill.md + README）** | 2026/4/21 23:59 |

> 📌 **不允許遲交。第一階段 CI 未通過者，第二階段評分上限為 60 分。**

---

## 作業目標

> **RAG as Personal Knowledge Engine** — 從零開始，自行收集感興趣領域的原始資料，建構輕量化 RAG（Retrieval-Augmented Generation）系統，並透過 LLM 問答，最終將知識濃縮為可供 Agent 使用的 `skill.md` 技能文件。

本作業的核心學習目標：

- 理解 RAG 系統的全流程架構：**Data Collection → Chunking → Embedding → Vector Store → Retrieval → LLM Generation**
- 實踐「**資料即規格**」：設計可重複執行的 `data_update.py`，讓資料的更新與索引完全自動化
- 體驗 **LiteLLM** 作為統一 LLM 介面的優勢，無縫切換底層模型
- 將 RAG 系統的輸出提升至 **Agent 可直接使用的 Skill 層級**：從問答到知識萃取，完成「升維建構」

---

## 作業流程總覽

```mermaid
flowchart TD
    A[自行收集原始資料\n文章 / PDF / 網頁 / 論文] --> B[data_update.py\n資料清理 + Chunking]
    B --> C[Embedding Model\n產生向量]
    C --> D[(Vector DB\npgvector / ChromaDB)]
    D --> E[rag_query.py\nCLI 問答介面]
    E --> F[LiteLLM\n統一 LLM 呼叫層]
    F --> G[LLM 回應\n含引用來源]
    G --> H[skill_builder.py\n自動萃取知識]
    H --> I[skill.md\nAgent 技能文件]

    style D fill:#dbeafe,stroke:#3b82f6
    style I fill:#dcfce7,stroke:#16a34a
    style F fill:#fef9c3,stroke:#ca8a04
```

---

## 📁 必繳檔案結構

> ⚠️ **Python 版本要求：`>= 3.10`。** 請在 `README.md` 中明確聲明你開發時的 Python 版本（例如 `3.11.9`），助教將以該版本或相近版本進行複現。使用過舊版本（如 3.8、3.9）可能導致型別標注語法錯誤或套件不相容，造成複現失敗。

```
AIASE2026-HW3/
├── data/                       ← 原始資料（文件、Markdown、PDF 等）（必要）
│   ├── raw/                    ← 最原始的來源資料
│   └── processed/              ← 清理後、可直接 chunk 的文字檔（由 data_update.py 生成）
├── docker-compose.yml          ← Vector DB 啟動設定（使用 pgvector / Qdrant 者必要）
├── data_update.py              ← 資料收集、清理、索引腳本（必要）
├── rag_query.py                ← RAG 問答 CLI 介面（必要）
├── skill_builder.py            ← skill.md 自動生成腳本（必要）
├── skill.md                    ← 最終產出的 Agent 技能文件（必要）
├── README.md                   ← 完整說明文件（必要）
├── requirements.txt            ← Python 套件清單（必要）
└── .env.example                ← 環境變數範本（必要，不可 commit 真實金鑰）
```

> ⚠️ **`data_update.py`、`rag_query.py`、`skill_builder.py`、`skill.md`、`README.md`、`requirements.txt`、`.env.example` 為必要檔案，缺少任一者以 0 分計算。**

> ⚠️ **`data/` 目錄至少需包含 20 份以上的文件或資料片段（chunk 前）。資料不足將影響 RAG 系統的評分。**

> ⚠️ **請勿將真實 API Key 或任何帳號密碼 commit 至 repo。** 所有敏感資訊一律透過 `.env` 管理，repo 中只能出現 `.env.example`。

---

## 📚 資料收集規範

### 主題選擇

你需要**自主選定**一個知識主題，作為整個 RAG 系統的資料來源。主題自由，但須符合以下條件：

| 條件 | 說明 |
|---|---|
| **聚焦性** | 主題明確，有清楚的知識邊界（例如：「Transformer 架構論文」，而非「AI 所有內容」） |
| **可持續性** | 資料來源須能定期更新（新論文、新文章、新版本文件等） |
| **合法合規** | 使用合法授權的資料（Creative Commons、公開論文、官方文件、個人著作等），不可爬取付費牆內容 |
| **深度** | 資料需有足夠語意深度，能支撐有意義的 LLM 問答 |

**建議主題範例（請自行發揮）：**

> 💡 主題方向沒有限制。以下分類僅供發想，**選擇你真正感興趣、對你的研究或職涯有用的領域**，產出的 `skill.md` 才會有真實價值。

---

**🔬 學術研究導向**

| 主題方向 | 資料來源範例 | 產出 Skill 的用途 |
|---|---|---|
| **個人研究領域論文集** | arXiv PDF、Semantic Scholar、ACL Anthology | 研究助手：「這個方向最近有哪些突破？主要作者群？」 |
| **特定技術的官方文件** | LangGraph / CrewAI / MCP / FastAPI Docs | 開發助手：「如何在 LangGraph 中實作 interrupt？」 |
| **開源專案 codebase 與 README** | GitHub repo 的 Markdown 文件群 | 程式碼顧問：「這個專案的 agent memory 如何設計？」 |
| **AI 安全與對齊研究** | Anthropic / DeepMind / ARC 公開報告、Alignment Forum 文章 | AI 安全分析師：「RLHF 與 RLAIF 的核心差異？目前最受關注的對齊方法？」 |
| **個人學習筆記 / 課程資料** | 自己整理的 Markdown 筆記、教材 | 複習助手：「RLHF 的核心步驟為何？」 |

---

**📱 科技產品與市場分析導向**

| 主題方向 | 資料來源範例 | 產出 Skill 的用途 |
|---|---|---|
| **AI PC / 消費性電子市場分析師** | IDC / Gartner 公開報告、品牌財報摘要、科技媒體評測（AnandTech、Tom's Hardware、The Verge）、供應鏈新聞 | 市場顧問：「2025 年 AI PC 的主要成長驅動力？Intel vs. AMD vs. Qualcomm 的市佔競爭格局？」 |
| **智慧型手機產業分析師** | Counterpoint Research 公開報告、各品牌發表會稿、GSMA 公開數據、科技媒體旗艦機評測 | 產品策略師：「折疊機市場的滲透率瓶頸？Android 高階旗艦的差異化策略如何演變？」 |
| **半導體 / 晶片產業分析師** | SEMI 公開報告、台積電 / 三星 / Intel 法說會逐字稿、IC Insights 公開摘要、EE Times 文章 | 產業顧問：「先進封裝（CoWoS）的產能供需現況？AI 訓練晶片與推論晶片的設計差異？」 |
| **穿戴裝置 / 健康科技分析師** | IDC 穿戴裝置報告、Apple Health 相關文章、Garmin / Fitbit 官方白皮書、醫療可穿戴論文 | 健康科技顧問：「智慧手錶的健康監測功能可信度如何？醫療級穿戴裝置的市場規模？」 |
| **雲端服務市場分析師** | AWS / Azure / GCP 官方白皮書與定價頁、Synergy Research 公開報告、Cloudflare 年度 Radar 報告 | 雲端採購顧問：「三大雲端在 AI 訓練服務上的定價策略差異？Multi-cloud 的主要採用動機？」 |

---

**📊 商業、行銷與投資分析導向**

| 主題方向 | 資料來源範例 | 產出 Skill 的用途 |
|---|---|---|
| **行銷與消費者洞察分析師** | Nielsen / Kantar 公開報告、品牌行銷案例研究、HBR 行銷文章、公開廣告素材分析、CMO Survey | 行銷策略顧問：「Z 世代對社群廣告的接受度趨勢？DTC 品牌的成功關鍵因素？」 |
| **社群媒體行銷趨勢分析師** | Meta / TikTok / LinkedIn 官方年度報告、HootSuite Global Report、Sprout Social Benchmark | 社群策略師：「B2B 內容行銷在 LinkedIn 的最佳發文策略？短影音 ROI 如何衡量？」 |
| **品牌策略與消費者心理分析師** | 知名品牌 Case Study（哈佛商業評論）、廣告獎（Cannes Lions）得獎案例分析、消費心理學論文 | 品牌顧問：「奢侈品牌進入大眾市場的成功案例有哪些？情感行銷的神經科學依據？」 |
| **創投與新創生態追蹤** | Crunchbase 公開資料、CB Insights 報告、知名 VC 部落格（a16z、Sequoia、GGV 文章）| 產業雷達：「最近哪些賽道獲得最多 A 輪投資？台灣新創在 AI 領域的切入角度？」 |
| **電商與零售產業趨勢分析師** | Shopify 年報、eMarketer 公開摘要、電商平台官方白皮書、物流業者年報 | 電商顧問：「跨境電商的主要物流痛點？直播帶貨在東南亞的滲透率與變現模式？」 |
| **永續發展與 ESG 報告分析師** | 公開 ESG 報告（台積電、鴻海、TSMC等）、TCFD 框架文件、CDP 公開資料、GRI 標準文件 | ESG 顧問：「台灣科技業的碳排放揭露現況？供應鏈 Scope 3 的主要挑戰與解法？」 |
| **總體經濟與金融市場觀察** | Fed / ECB 公開會議紀錄、IMF / World Bank 公開報告、財經媒體深度分析（FT、Bloomberg 公開文章）| 宏觀分析師：「升息循環尾聲的歷史市場走勢規律？台灣出口與美國製造業PMI的相關性？」 |

---

**🏥 專業領域垂直分析導向**

| 主題方向 | 資料來源範例 | 產出 Skill 的用途 |
|---|---|---|
| **生醫 / 藥廠研發趨勢分析師** | PubMed 公開論文、FDA 公開核准資料、BioSpace 新聞、生技公司法說會稿 | 生醫顧問：「GLP-1 藥物市場的競爭格局？AI 輔助藥物設計的主流方法有哪些？」 |
| **教育科技（EdTech）產業分析師** | HolonIQ 公開報告、UNESCO 教育報告、知名 EdTech 公司年報與部落格 | EdTech 策略師：「AI 家教應用的使用者留存挑戰？各地政府對 GenAI in Education 的監管立場？」 |
| **遊戲產業分析師** | Newzoo 公開報告、Steam 公開數據、GDC 公開演講稿、遊戲媒體評測資料庫 | 遊戲產業顧問：「手遊市場的 ARPU 趨勢？PC 獨立遊戲的行銷策略演變？」 |
| **法律法規知識庫** | 公開法條（全國法規資料庫）、公開判決書摘要、GDPR / AI Act 原文、法律白皮書 | 法規查詢助手：「個資法第幾條規範資料保存期限？GDPR 與台灣個資法的主要差異？」 |
| **房地產市場分析師** | 內政部不動產資訊平台公開數據、信義房屋 / 永慶年度報告、都市計畫公文 | 房市顧問：「台灣六都房價所得比的長期趨勢？捷運效應對周邊房價的影響程度？」 |
| **人才市場與職場趨勢分析師** | LinkedIn Workforce Report、104 人力銀行公開數據、McKinsey Future of Work 報告 | HR 顧問：「台灣 AI 工程師的薪資中位數與供需缺口？遠端工作政策對員工留任率的影響？」 |

---

**🌐 時事、文化與知識管理導向**

| 主題方向 | 資料來源範例 | 產出 Skill 的用途 |
|---|---|---|
| **特定國家 / 產業政策追蹤** | 政府公報、立法院公文、公開政策白皮書、NIST / 歐盟 AI Act 原文 | 政策分析師：「台灣 AI 政策的主要補助方向？半導體出口管制的最新動向？」 |
| **名人 / 思想家觀點彙整** | 公開演講稿、部落格、LinkedIn 文章、TED Talk 逐字稿、播客逐字稿 | 觀點摘要機：「Sam Altman 對 AGI 安全的核心主張？Paul Graham 對新創失敗的分析？」 |
| **特定語言 / 文學作品分析** | 公版著作（Project Gutenberg、中研院語料庫）、詩集、散文集 | 文學分析師：「這位作者的意象系統有哪些特徵？與同時代作家的風格差異？」 |
| **體育賽事與運動科學** | 公開賽事統計資料（NBA Stats、FIFA 公開數據）、運動科學論文、ESPN 公開分析 | 運動分析師：「NBA 三分球革命的戰術演變脈絡？精英跑者訓練方法的近十年轉變？」 |

> 💡 **鼓勵選擇與自己研究、職涯或興趣直接相關的主題**——這樣你最終產出的 `skill.md` 對你自己也有真實使用價值，甚至可以直接整合進你的個人 AI 工作流。

---

## 🛠️ 系統元件規範

### 元件一：`data_update.py`（資料收集與索引）

這是本作業技術核心。`data_update.py` 需支援**冪等性（Idempotent）執行**：每次執行後，Vector DB 中的資料應完整反映 `data/` 目錄的最新狀態，不可重複累積舊資料。

**必要功能：**

```
python data_update.py [options]
```

| 功能 | 說明 |
|---|---|
| **資料載入** | 讀取 `data/raw/` 中的原始檔案（支援至少兩種格式：`.md`、`.txt`、`.pdf` 擇二或以上） |
| **文字清理與輸出** | 移除無意義內容（HTML 標籤、頁首頁尾、重複空白等），並將清理後的純文字**儲存至 `data/processed/`**，命名慣例為原始檔名去掉副檔名後加 `.txt`，例如：`data/raw/paper.pdf` → `data/processed/paper.txt`；`data/raw/notes.md` → `data/processed/notes.txt` |
| **Chunking** | 讀取 `data/processed/` 中的清理後文字，切分為適合 embedding 的片段（需實作至少一種合理策略，如固定長度 + overlap）|
| **Embedding** | 呼叫 Embedding Model（詳見下方「Embedding Model 選型說明」）|
| **向量寫入** | 將 chunk 文字、向量、來源 metadata 寫入 Vector DB |
| **全量重建** | 支援 `--rebuild` 旗標，清空 `data/processed/` 並重建整個索引 |
| **增量更新** | 預設僅更新有變動的文件（以檔案 hash 或修改時間判斷）|

> 💡 **`data/processed/` 的設計目的**：讓清理流程與向量化流程解耦。若 Embedding 出現問題需要重跑，不必重新解析 PDF；若資料清理邏輯修改，也可以只重跑清理步驟。這是業界 data pipeline 的常見最佳實踐。`data/processed/` 中的 `.txt` 檔案建議一併 commit 至 repo，方便助教在不重跑清理步驟的前提下直接驗證。

**建議 Vector DB（擇一）：**

| 工具 | 特色 | 適合情境 |
|---|---|---|
| **pgvector** | PostgreSQL 擴充，SQL 查詢能力強 | 熟悉 SQL、需要 metadata 過濾 |
| **ChromaDB** | 純 Python、零設定 | 快速上手、本地端 |
| **Qdrant** | 效能佳、REST API | 進階使用、未來部署考量 |
| **FAISS** | Meta 出品、記憶體內執行 | 離線、無 server 需求 |

> 💡 **推薦使用 pgvector**，原因在於：可結合 SQL 進行 metadata 過濾、可在 Docker 環境中快速啟動，且是業界真實 RAG 系統最常見的選擇之一。

**📌 Embedding Model 選型說明（重要：費用規則）**

> ⚠️ **老師透過 LiteLLM 提供兩類 LLM 資源：(1) 受限制的 Gemini 用量（每人上限 $3 美元）；(2) 免費的本地端模型（速度有限，多人同時存取可能有 crash 風險，請盡早開發 。**
>> Gemini - 以gemini-2.5-flash為主
>> Local Model - 以gpt-oss-20b為主

> **Embedding Model 費用不在涵蓋範圍內**，請依下表選擇免費方案。

LiteLLM 的 `embedding()` 函式支援 100+ 個 Embedding Provider，包含多種完全免費的本地選項：

| 方案 | 模型範例 | 費用 | 需要 API Key | 適合情境 |
|---|---|---|---|---|
| ✅ **sentence-transformers（本地）** | `all-MiniLM-L6-v2`<br>`paraphrase-multilingual-MiniLM-L12-v2` | **完全免費** | ❌ 不需要 | 英文資料 / 中英混合 |
| ✅ **HuggingFace Inference API（免費額度）** | `huggingface/sentence-transformers/all-MiniLM-L6-v2` | **免費**（有速率限制） | 需要免費 HF Token | 不想在本地下載模型 |
| ✅ **Ollama 本地部署** | `ollama/nomic-embed-text`<br>`ollama/mxbai-embed-large` | **完全免費** | ❌ 不需要 | 已有 Ollama 環境 |
| ❌ **OpenAI（不建議）** | `text-embedding-3-small` | **付費**，老師不負擔 | 需要 OpenAI Key | — |

**推薦方案：`sentence-transformers` 本地模型**

sentence-transformers 是 HuggingFace 維護的 Python 框架，提供超過 15,000 個預訓練模型，可直接在本地端執行，無需任何 API Key 或網路呼叫。

```python
# 方案 A（推薦）：直接使用 sentence-transformers，完全本地、完全免費
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")  # 支援中英文
embeddings = model.encode(chunks)  # 回傳 numpy array

# 方案 B：透過 LiteLLM 統一介面呼叫（需免費 HF Token）
from litellm import embedding
import os
os.environ["HF_TOKEN"] = "hf_xxxxxx"   # 至 huggingface.co/settings/tokens 免費申請

response = embedding(
    model="huggingface/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    input=chunks
)
vectors = [item["embedding"] for item in response.data]
```

**推薦模型對照表：**

| 模型名稱 | 向量維度 | 語言支援 | 模型大小 | 備註 |
|---|---|---|---|---|
| `all-MiniLM-L6-v2` | 384 | 英文為主 | ~80MB | 速度快，英文資料首選 |
| `paraphrase-multilingual-MiniLM-L12-v2` | 384 | 50+ 語言（含中文） | ~420MB | **中英混合資料推薦** |
| `all-mpnet-base-v2` | 768 | 英文 | ~420MB | 品質較高，速度稍慢 |
| `nomic-embed-text`（via Ollama） | 768 | 英文為主 | ~270MB | 需先安裝 Ollama |

> 💡 **若你的資料包含中文**，強烈建議使用 `paraphrase-multilingual-MiniLM-L12-v2`，其對中文語義的捕捉效果遠優於英文 only 模型。

### 元件二：`rag_query.py`（LLM 問答介面）

提供互動式 CLI 問答，每次查詢需完整執行 RAG 流程：**Embed Query → Retrieve Chunks → LLM Generate**。

**必要功能：**

```bash
# 互動式模式
python rag_query.py

# 單次查詢模式
python rag_query.py --query "你的問題" [--top-k 5] [--model gemini-2.5-flash]
```

| 功能 | 說明 |
|---|---|
| **Query Embedding** | 將使用者問題向量化 |
| **Similarity Search** | 從 Vector DB 取得最相關的 top-k chunks |
| **Prompt 組裝** | 將 retrieved chunks 與問題組成完整 prompt |
| **LiteLLM 呼叫** | 透過 LiteLLM 統一介面呼叫 LLM |
| **引用來源顯示** | 回應中需顯示每個引用 chunk 的來源檔案與段落編號 |
| **Multi-turn 對話** | 互動式模式需保留對話歷史（至少 3 輪）|

**LiteLLM 整合說明：**

本作業統一使用 LiteLLM 作為 LLM 呼叫層，助教將提供統一 API Key 與 Endpoint 設定，你只需要在 `.env` 中填入即可切換模型，無需更改任何程式碼。

```python
# 範例：透過 LiteLLM 呼叫 LLM
from litellm import completion

response = completion(
    model="gemini-2.5-flash",       # 可透過 --model 參數切換
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt_with_context}
    ]
)
```

`.env.example` 範本：

```bash
# =============================================
# LiteLLM 設定（助教提供，用於 Chat Completion）
# =============================================
LITELLM_API_KEY=your_api_key_here
LITELLM_BASE_URL=https://your-litellm-endpoint/

# =============================================
# Embedding Model 設定（三選一，擇一填寫）
# =============================================

# 選項 A（推薦）：sentence-transformers 本地模型，完全免費，無需 API Key
# 只需 pip install sentence-transformers，程式會自動下載模型（首次約 80–420MB）
EMBEDDING_PROVIDER=sentence-transformers
EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2   # 中英文皆適合

# 選項 B：HuggingFace Inference API，免費額度，需免費申請 HF Token
# 至 https://huggingface.co/settings/tokens 申請（免費帳號即可）
# EMBEDDING_PROVIDER=huggingface
# EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
# HF_TOKEN=hf_xxxxxx

# 選項 C：Ollama 本地部署（需先安裝 Ollama 並執行 ollama pull nomic-embed-text）
# EMBEDDING_PROVIDER=ollama
# EMBEDDING_MODEL=nomic-embed-text
# OLLAMA_BASE_URL=http://localhost:11434

# =============================================
# Vector DB 設定（依你選擇的 DB 填寫）
# =============================================
PGVECTOR_CONNECTION_STRING=postgresql://user:password@localhost:5432/ragdb
# 或
# CHROMA_PERSIST_DIR=./chroma_db
```

### 元件三：`skill_builder.py`（技能文件生成）

`skill_builder.py` 是讓這個 RAG 系統「升維」的關鍵。它不是讓你問單一問題，而是**系統性地萃取整個知識庫的核心洞察**，生成 `skill.md`。

```bash
python skill_builder.py [--output skill.md] [--model gemini-2.5-flash]
```

**`skill_builder.py` 應自動執行以下工作：**

1. **主題掃描**：向 RAG 系統提出多個預設的「全域問題」，例如：
   - 「這個知識庫涵蓋哪些主要概念和子主題？」
   - 「目前最重要的研究方向或趨勢為何？」
   - 「主要的作者、機構、或資料來源有哪些？」
   - 「這個領域的核心工具、框架、或方法論有哪些？」

2. **知識整合**：將多次查詢的結果，透過 LLM 整合為連貫的知識摘要

3. **Skill.md 生成**：輸出符合 Agent Skill 格式的文件

---

## 📄 `skill.md` 格式規範

`skill.md` 是本作業的最終成果，格式須符合可供 Agent 直接讀取的 Skill 文件標準：

```markdown
# Skill: [主題名稱]

## Metadata
- **知識領域**：[例如：機器學習 / Transformer 架構 / 量化金融]
- **資料來源數量**：[N 份文件]
- **最後更新時間**：[YYYY-MM-DD]
- **適用 Agent 類型**：[研究助手 / 技術顧問 / 領域問答機器人]

## Overview（一段話摘要）
[200字以內，說明這個 Skill 的核心知識範疇與能力邊界]

## Core Concepts（核心概念）
[條列 5–15 個最重要的概念，每個概念附 1–2 句說明]

## Key Trends（最新趨勢）
[條列 3–10 個目前最重要的發展方向或研究趨勢]

## Key Entities（重要實體）
[作者、機構、工具、框架、資料集等，分類條列]

## Methodology & Best Practices（方法論與最佳實踐）
[這個領域中被廣泛接受的方法、流程或原則]

## Knowledge Gaps & Limitations（知識邊界）
[說明這個 Skill 目前的知識侷限，例如資料截止日期、未覆蓋的子主題等]

## Example Q&A（代表性問答）
[列出 3–5 組具代表性的問題與簡短答案，展示此 Skill 能回答的問題類型]

## Source References（來源索引）
[列出資料來源清單，包含文件名稱、類型、日期等]
```

> 💡 `skill.md` 的品質，代表你的 RAG 系統是否真正「讀懂」了你的資料庫。這份文件應能讓任何人（或任何 Agent）在不問一句話的前提下，快速掌握這個知識域的全貌。

---

## 📖 README.md 撰寫要求

`README.md` 需讓他人（或 AI）能在乾淨的環境中，**從零開始完整重現你的 RAG 系統**，並包含你的設計決策說明。請包含以下各節：

### 1. 專案簡介
- 說明你選擇的知識主題，以及選擇理由
- 概述資料來源的類型與規模（幾份文件、什麼格式、涵蓋的時間範圍）
- 簡述你的 RAG 系統架構與技術選型

### 2. 系統架構說明（含 Mermaid 圖）

請提供你的系統架構 Mermaid 圖，至少包含：

````markdown
```mermaid
graph LR
    A[data/raw/] --> B[data_update.py]
    B --> C{Chunking\nStrategy}
    C --> D[Embedding Model]
    D --> E[(pgvector)]
    E --> F[rag_query.py]
    F --> G[LiteLLM]
    G --> H[skill_builder.py]
    H --> I[skill.md]
```
````

### 3. 設計決策說明（Design Decisions）

> 💡 這是評分最重要的章節之一。請詳細說明你在每個技術節點上的選擇與理由：

請至少回答以下問題（以條列方式說明，越詳細越好）：

- **Chunking 策略**：你如何切分文件？固定長度？依段落？依語意邊界？Overlap 設定為何？為什麼？
- **Embedding 模型選擇**：選用哪個 Embedding 模型（`sentence-transformers` / HuggingFace / Ollama）？為什麼適合你的主題？中英文混合如何處理？本地模型與 API 呼叫各有何取捨？
- **Vector DB 選型**：為何選擇此 DB？有沒有評估過其他選項？
- **Retrieval 策略**：top-k 設定為何？有沒有使用 reranking 或 metadata 過濾？
- **Prompt Engineering**：你的 RAG prompt 如何設計？如何告訴 LLM 要引用來源？
- **Idempotency 設計**：`data_update.py` 如何保證冪等性？如何偵測資料是否已更新？
- **skill_builder.py 問題設計**：你設計了哪些「全域問題」來萃取知識？為什麼？

### 4. 環境設定與執行方式

> ⚠️ **這是評分時最關鍵的章節。** 助教會依照此章節的指令，在乾淨環境中逐步複現你的系統。指令不完整、路徑錯誤、缺少前置步驟，都會導致複現失敗，視同無法執行以 0 分計算。請確保每一行指令都能直接複製貼上執行。

#### 4-1. Python 版本與虛擬環境（必讀）

本作業**要求 Python 3.10 以上**。請在 README 中明確聲明你開發時使用的完整 Python 版本（例如 `3.11.9`），助教將以該版本或相近版本進行複現。

> ⚠️ **為什麼一定要用虛擬環境？** 在 Ubuntu 22.04+ 等現代 Linux 發行版中，直接執行 `pip install` 會遭遇 `error: externally-managed-environment`，系統禁止在全域 Python 環境安裝套件。這不是 bug，是 Linux 保護機制。**解法是建立虛擬環境**，這也是所有 Python 專案的標準做法，能避免不同專案的套件版本互相汙染。

```bash
# Step 0：確認 Python 版本（需 >= 3.10）
python3 --version
# 若版本過舊，請先升級：sudo apt install python3.11

# Step 1：建立虛擬環境（擇一）
python3 -m venv .venv                    # ✅ 推薦：標準 venv，無需額外安裝
# conda create -n hw3 python=3.11        # 或使用 conda

# Step 2：啟動虛擬環境
source .venv/bin/activate                # Linux / macOS
# .venv\Scripts\activate                 # Windows（若適用）

# 啟動後，命令列提示符會出現 (.venv) 前綴，代表成功進入虛擬環境
# (.venv) user@host:~/AIASE2026-HW3$

# Step 3：安裝套件
pip install -r requirements.txt
```

> 💡 **`requirements.txt` 須包含 Python 版本備註**，格式如下首行，方便助教確認相容性：

```
# Python >= 3.10 required (developed with 3.11.9)
sentence-transformers==2.7.0
chromadb==0.5.3
litellm==1.40.0
...
```

#### 4-2. Vector DB 啟動（`docker-compose.yml` 必要）

> ⚠️ **若你使用需要 server 的 Vector DB（pgvector、Qdrant 等），必須提供 `docker-compose.yml`**，且 volume 掛載路徑需使用**相對路徑**，確保在任何機器上 clone 後都能直接啟動，不依賴任何本機的絕對路徑。

**`docker-compose.yml` 範例（pgvector）：**

```yaml
version: "3.9"
services:
  pgvector:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: raguser
      POSTGRES_PASSWORD: ragpassword
      POSTGRES_DB: ragdb
    ports:
      - "5432:5432"
    volumes:
      - ./docker/pgdata:/var/lib/postgresql/data   # ✅ 相對路徑，可跨機器複現
      # ❌ 錯誤示範：- /home/alice/mydata:/var/lib/postgresql/data
```

```bash
# 啟動 Vector DB
docker compose up -d

# 確認啟動成功
docker compose ps
```

> ⚠️ **常見錯誤（會導致複現失敗）：**
> - ❌ volume 使用絕對路徑（如 `/home/username/data`）→ 換機器就壞
> - ❌ 只提供 `docker run` 一行指令，沒有 `docker-compose.yml` → 難以穩定重現
> - ❌ README 沒有說明需先 `docker compose up` → 助教直接跑 `data_update.py` 必然失敗
> - ❌ `.env` 中的 DB 連線字串與 `docker-compose.yml` 中的帳密不一致

若使用 **ChromaDB**（純 Python、不需 server），請在 README 中明確說明，並指定 `CHROMA_PERSIST_DIR` 的路徑：無需提供 `docker-compose.yml`，但需確保 `.env` 中的路徑與程式一致。

#### 4-3. 完整執行流程（README 必須照此格式提供）

> ⚠️ **這是評分時最關鍵的章節。** README 中的每一行指令必須能讓助教在乾淨環境 `git clone` 後，按順序逐行複製貼上執行，不需猜測任何步驟。**任何缺漏都可能造成複現失敗，視同無法執行。**

你的 README 必須包含以下所有步驟（不可省略，不可只提供部分）：

```bash
# ① 確認 Python 版本
python3 --version        # 需顯示 >= 3.10.x

# ② 建立並啟動虛擬環境
python3 -m venv .venv
source .venv/bin/activate

# ③ 安裝套件
pip install -r requirements.txt

# ④ 設定環境變數
cp .env.example .env
# 請將 .env 中的 LITELLM_API_KEY 和 LITELLM_BASE_URL 填入助教提供的值

# ⑤ 啟動 Vector DB（使用 pgvector 者執行，ChromaDB 跳過）
docker compose up -d
docker compose ps        # 確認 pgvector 狀態為 running

# ⑥ 全量重建索引
python data_update.py --rebuild

# ⑦ 測試 RAG 問答
python rag_query.py --query "請問這個知識庫的核心主題是什麼？"

# ⑧ 生成 Skill 文件
python skill_builder.py --output skill.md
```

**複現完整性檢查清單（繳交前自行驗證）：**

- [ ] 在全新目錄 `git clone` 後，能按照上述順序無誤執行所有指令
- [ ] `docker-compose.yml` 使用相對路徑（若有）
- [ ] `.env.example` 存在且不含真實金鑰
- [ ] `requirements.txt` 第一行有 Python 版本備註
- [ ] `data/processed/` 中有清理後的 `.txt` 檔案（已 commit）
- [ ] `python data_update.py --rebuild` 執行後無 Error，Vector DB 有資料
- [ ] `python rag_query.py --query "..."` 能回傳含引用來源的答案

### 5. 資料來源聲明（Data Sources Statement）

**必要章節。** 列出所有資料來源，並聲明其授權狀態：

| 來源名稱 | 類型 | 授權 / 合規依據 | 數量 |
|---|---|---|---|
| arXiv 論文（1234.56789 等） | PDF | CC BY 4.0 | 15 篇 |
| LangGraph 官方文件 | Markdown | Apache 2.0 | 8 份 |
| 個人研究筆記 | Markdown | 個人著作 | 5 份 |

### 6. 系統限制與未來改進

誠實說明目前 RAG 系統的不足之處，以及若有更多時間你會如何改進。

---

## 🎯 評分說明

### 自動評分（AI Agent）：60–95 分

| 評分面向 | 配分比重 | 說明 |
|---|---|---|
| **資料收集品質與深度** | 15% | 資料量是否充足（≥20份）、主題是否聚焦、來源是否多樣且合規 |
| **RAG 系統完整度** | 30% | `data_update.py` 的 chunking 策略、embedding 正確性、向量寫入完整性；`rag_query.py` 的 retrieval 流程、引用來源顯示、LiteLLM 整合 |
| **冪等性與可重複執行性** | 15% | `data_update.py --rebuild` 能否清空重建；增量更新是否正確；CI 驗證可執行性 |
| **`skill.md` 產出品質** | 25% | 是否涵蓋 Skill 文件所有必要章節；核心概念、趨勢、實體的萃取品質；知識密度與可讀性 |
| **README 設計決策深度** | 15% | 每個技術選擇的說明是否有具體理由、個人化的工程思路是否清晰 |

- AI 評分會進行相對排序，整體分佈接近 Normal Distribution，$\mu \approx 78$
- AI 評分準則細節事前不公開，期末將公布評分程式碼

### 人工抽查

- 確認 `data_update.py --rebuild` 可在乾淨環境中無誤執行
- 確認 `rag_query.py --query "測試問題"` 可回傳含引用來源的答案
- **無法執行者以 0 分計算**
- 抽查加分：`skill.md` 內容具有真實知識價值，且能清楚展示「RAG 系統確實理解了資料」，老師額外加 **1–5 分**

> 💡 **最高分的策略**：你的 `skill.md` 讀起來應該像一份**由領域專家整理的入門指南**，而非 LLM 的隨機輸出。這代表你的 RAG 系統的 chunking、retrieval 與 prompt 設計都是認真思考過的。

---

## 🤖 GitHub Actions 自動檢查（CI）

本作業設置兩階段 CI：

### 第一階段 CI 檢查項目（4/14 截止）

- ✅ `data_update.py` 是否存在
- ✅ `rag_query.py` 是否存在
- ✅ `data/` 目錄是否存在且包含至少 5 個以上的檔案（佔位確認，完整資料需於第二階段）
- ✅ `requirements.txt` 是否存在
- ✅ `.env.example` 是否存在（且不含任何真實 API Key pattern）
- ✅ `python data_update.py --help` 執行不報錯
- ✅ `python rag_query.py --help` 執行不報錯

### 第二階段 CI 檢查項目（4/21 截止）

- ✅ `skill_builder.py` 是否存在
- ✅ `skill.md` 是否存在且大於 500 字元
- ✅ `README.md` 是否存在且大於 1000 字元
- ✅ `data/` 目錄的檔案數量是否達到 20 個以上
- ✅ `python skill_builder.py --help` 執行不報錯
- ✅ `skill.md` 中是否包含必要章節關鍵字（`## Overview`、`## Core Concepts`、`## Source References` 等）

> ⚠️ **CI 僅確認結構與基本可執行性。`skill.md` 的知識品質與 RAG 系統的回答品質，由 AI 評分時實際執行驗證。**

---

## 📅 繳交方式

### 第一階段（系統可執行版）

```bash
git add data/ data_update.py rag_query.py requirements.txt .env.example
git commit -m "HW3 Phase 1: RAG system core implementation"
git push origin main
```

### 第二階段（完整版）

```bash
git add skill_builder.py skill.md README.md
# 確認 data/ 已補充至 20 份以上文件
git add data/
git commit -m "HW3 Phase 2: skill builder, skill.md and full documentation"
git push origin main
```

---

## ❓ 常見問題

**Q：在 Linux 上執行 `pip install` 遇到 `externally-managed-environment` 錯誤怎麼辦？**
A：這是 Ubuntu 22.04+ 等現代 Linux 發行版的預設行為，系統禁止直接在全域 Python 環境安裝套件。請使用 Python 虛擬環境：
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
啟動虛擬環境後，後續所有 `pip install` 與 `python` 指令都會在隔離環境中執行，不會影響系統 Python。請確保 README 中也包含此步驟。

**Q：`docker-compose.yml` 一定要提供嗎？**
A：若你使用 pgvector 或 Qdrant 等需要 server 的 Vector DB，**是的，必須提供 `docker-compose.yml`**。助教批改時無法每次手動輸入冗長的 `docker run` 指令，`docker-compose.yml` 讓啟動流程標準化。此外，volume 掛載路徑**必須使用相對路徑**（例如 `./docker/pgdata`），絕對路徑在不同機器上會直接失敗。若你使用 ChromaDB（不需 server），則不需要 `docker-compose.yml`，但請在 README 中明確說明。

**Q：Vector DB 要自己架設嗎？**
A：是的，你需要自行在 local 或 Docker 中啟動 Vector DB。助教提供 pgvector 的 Docker 啟動指令，也接受 ChromaDB（純 Python，不需要 server）。如果你選擇ChromaDB，為避免binary格式的平台差異，請在requirements.txt中說明，我們將手動透過pip install requirements.txt的方式來安裝，你不用將ChromaDB整個上傳。
> 請將Database的檔案加在.gitignore檔中，讓git ignore上傳這個檔案。

**Q：Embedding Model 要用哪個？費用誰出？**
A：**老師透過 LiteLLM 提供兩類 LLM 資源：(1) 受限制的 Gemini 用量（每人上限 $3 美元）；(2) 免費的本地端模型（速度有限，多人同時存取可能有 crash 風險，請盡早開發避免塞車）。Embedding Model 的費用不在涵蓋範圍內**，請使用以下免費方案之一：

- **方案 A（推薦）：`sentence-transformers` 本地模型**，完全免費、無需 API Key，只要 `pip install sentence-transformers` 即可。中英文資料建議使用 `paraphrase-multilingual-MiniLM-L12-v2`，英文資料用 `all-MiniLM-L6-v2`。首次執行會自動從 HuggingFace 下載模型（80–420MB），之後完全離線。
- **方案 B：HuggingFace Inference API**，有免費使用額度，需至 [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) 申請免費 HF Token，透過 LiteLLM 的 `huggingface/` prefix 呼叫。
- **方案 C：Ollama 本地部署**，若你已有 Ollama 環境，可 `ollama pull nomic-embed-text` 後使用。

請在 README 中說明你選擇了哪個方案以及理由。

**Q：資料可以直接 commit 到 repo 嗎？**
A：可以，前提是資料合法合規。論文 PDF（arXiv CC授權）、官方 Markdown 文件、個人筆記均可。請在 README 中附上資料來源聲明。若資料總量超過 50MB，請使用 Git LFS 或只 commit `processed/` 的文字檔而不 commit 原始 PDF。

**Q：`data_update.py` 的「增量更新」一定要實作嗎？**
A：`--rebuild` 全量重建是必要的。增量更新（只更新有變動的檔案）是 bonus，在 CI 中不強制驗證，但會反映在 AI 評分的冪等性面向。

**Q：`skill.md` 一定要用 `skill_builder.py` 自動生成嗎？還是可以手動撰寫？**
A：`skill.md` 必須主要由 `skill_builder.py` 自動生成。你可以手動進行少量編輯與潤稿，但核心內容（概念、趨勢、實體等）必須是 RAG 系統的輸出。手動撰寫的 `skill.md` 不符合作業要求。

**Q：我可以選擇自己的研究題目或論文方向嗎？**
A：非常鼓勵！這樣你最終的 `skill.md` 對你真的有用，而不只是作業繳交。如果你在做碩士論文，可以把相關的論文、Markdown 筆記、技術文件全部丟進去，產出一份真正有價值的研究摘要。

**Q：LiteLLM 的 API Key 怎麼取得？**
A：助教會在第一階段截止日（4/14）前，透過 Discord 課程頻道統一發放 `.env` 設定內容，包含 `LITELLM_API_KEY` 與 `LITELLM_BASE_URL`。請屆時至 Discord 取得。在此之前，你可以先用 ChromaDB + 本地 sentence-transformers 完成 `data_update.py` 的開發，`rag_query.py` 的 LiteLLM 整合部分可先留 placeholder。

**Q：`skill.md` 的內容可以用中文嗎？**
A：可以。如果你的資料來源主要是中文，`skill.md` 可以全中文。如果是英文資料，`skill.md` 建議以英文為主，必要時中英混用。

---

*如有任何問題，請於 Discord 課程討論區發問。Let the RAG build your knowledge! 