# HW3 AI 評分回饋

> 本份回饋由 **Anthropic Claude Opus 4.7** 與 **OpenAI GPT-5.5** 兩個獨立模型，分別針對 Phase 1 與 Phase 2 程式碼與文件進行評分；最終加權分數為兩模型平均後，進行全班性的 Normalize，以及老師加分。

---

## 本次公布的兩個分數

本次 HW3 作業，每位同學會公布**兩個分數**，計算方式為下列三個候選值中**最高的兩個**：

| 候選 | 來源 | 計算 | 值 |
|---|---|---|---:|
| A | Max(Phase 1 兩模型評分) | max(Opus 86.0, GPT 92.0) | 92.00 |
| B | Max(Phase 2 兩模型評分) | max(Opus 84.0, GPT 86.8) | 86.75 |
| C | 最終加權分數 | 詳見下方加權計算 | 91.83 |

### 你的兩個分數

### **92.00**　／　**91.83**

_（A：Max(Phase 1 兩模型評分) = 92.00；C：最終加權分數 = 91.83）_

## 最終加權分數（候選 C）的計算

| 來源 | Phase 1 (40%) | Phase 2 (60%) | 加權平均 |
|---|---:|---:|---:|
| Anthropic Claude Opus 4.7 | 86.0 | 84.0 | 84.80 |
| OpenAI GPT-5.5 | 92.0 | 86.8 | 88.85 |
| **兩模型平均** | **89.0** | **85.4** | **86.83** |
| 老師加分 (professor_bonus) | | | +5 |
| **最終分數** | | | **91.83** |

## 計算公式

```
Phase 1 平均  = (Opus_P1 + GPT_P1) / 2
Phase 2 平均  = (Opus_P2 + GPT_P2) / 2
加權平均      = 0.4 × Phase 1 平均 + 0.6 × Phase 2 平均
Normalize 後  = 依全班分布做校準
最終分數      = min(100, Normalize 後 + 老師加分)
```

## 專案基本資料

- **github_id**：`MelanieShih-1`
- **領域**（Haiku 抽取）：`oura_ring_smart_health_wearable`
- **領域分類**（taxonomy）：`industry_specific_apps`
- **Phase 1 CI**：✓ 通過
- **Phase 2 CI**：✓ 通過

## Phase 1 分項評語（40% 權重）

| 面向 | Opus 分數 | Opus 評語 | GPT 分數 | GPT 評語 |
|---|---:|---|---:|---|
| 資料收集 | 78 | data/raw 25 份檔案，符合 Phase 1 門檻但未達高分區（>20）邊緣。格式以 .md 為主（24）、.txt 1 份，多樣性偏低。README 對來源組織分三層資料夾（使用支援/產品規格_功能/評價體驗）描述清楚並列舉參考連結與時間範疇（2024–2026），動機與市場觀察說明完整。扣分點：授權合規狀態未明確標示（license_compliance_signal=missing），多為網頁爬取內容無 robots/條款交代。 | 88 | data/raw 25 份，24 個 .md 加 1 個 .txt，數量與格式多樣性達高標；README 清楚分為使用支援、產品規格、評價體驗，但授權合規說明不足。 |
| RAG 系統完整度 | 88 | data_update.py 888 行，含 metadata 解析、markdown 清理、SHA-256 hash、pgvector 寫入與 chunking（1000/200）邏輯完整。rag_query.py 427 行，retrieval top-k 流程清楚，支援 metadata 過濾（source_prefix/type/section）、Cohere rerank 二階段、HF embedding 與 LiteLLM/OpenAI 客戶端整合，互動模式有 /rerank /filter /topk 等指令。citation 以 [編號] 顯示來源。設計決策章節對每個節點有理由。扣分：rerank 預設關閉、固定字元 chunking 對 markdown header 結構未感知。 | 92 | data_update.py 具清洗、1000/200 chunk、HF embedding、pgvector 寫入與 metadata；rag_query.py 有 top-k、filter、rerank、來源引用與 LiteLLM/OpenAI 相容整合。 |
| 冪等性 | 90 | README 明確支援 --rebuild --build-db 旗標，且實作 SHA-256 file hash 比對：hash 未變則跳過，改變則刪除舊 chunks 後重建，達到冪等與增量更新雙重目標。metadata 含 file_hash 與 updated_at 欄位支援追蹤。扣分點：未見 mtime 輔助快取或 manifest 檔案紀錄整體建庫狀態，且 .env.example 中 EMBEDDING_PROVIDER 預設為 sentence-transformers 與 README 建議的 huggingface 不一致，可能影響重現一致性。 | 96 | README 與程式支援 --rebuild；data_update.py 以 SHA-256 file_hash 判斷異動，未變更跳過、變更時刪除舊 chunks 後重建，增量更新完整。 |

## Phase 2 分項評語（60% 權重）

| 面向 | Opus 分數 | Opus 評語 | GPT 分數 | GPT 評語 |
|---|---:|---|---:|---|
| 資料收集深度 | 80 | data/ 共 25 份（24 md + 1 txt），分三類資料夾：產品規格_功能、使用支援、評價體驗，結構清晰且涵蓋官方與第三方評測。README §1.2 列出時間範疇 2024–2026。但授權合規說明缺失（scanner 標 license missing），README 未明確標注各來源 license 或 robots/合規處理，扣分。 | 74 | data/ 共25份達門檻，含官方支援、產品規格與評測彙整；但多為網頁md/txt，缺學術或臨床來源，README 未明確標註授權條款。 |
| skill.md 品質 | 86 | skill.md 9 章節齊全（10173 字），Core Concepts 7 條具體（Smart Sensing/PPG/感測器類型）、Key Entities 含 Oura Ring 4 Ceramic、PVD/DLC 塗層、Stelo 等具體實體與競品。Methodology 含飛航模式、首次設定等實務細節。Knowledge Gaps 聚焦產品限制而非資料缺漏，專業度佳。Source References 含類型與日期，整體像領域專家整理。 | 88 | skill.md 必要章節齊全，§Core Concepts 有7項，§Key Entities 含產品、感測器、競品等具體實體；內容完整但較偏產品導購，引用深度有限。 |
| README 設計決策 | 88 | README §3 完整回答 chunking（1000/200 理由）、embedding（中文友善 + HF API 取捨）、vectorDB（pgvector vs Chroma/Qdrant 評估）、metadata schema（9 欄詳列用途）、retrieval（top-k + 可選 rerank + 過濾）、prompt（角色 + 禁臆測 + 引用）、idempotency（SHA-256）、skill_builder（分流策略）。具體理由與取捨完整，Mermaid 四張流程圖加分。 | 92 | README §3 完整回答 chunking、embedding、pgvector、retrieval、prompt、idempotency 與 skill_builder，且有多語、metadata、雲端/本地取捨理由。 |
| skill_builder 品質 | 82 | skill_builder.py 設計 10 題全域問題涵蓋核心定位、設計、感測、監測指標、特殊健康、App/同步、評價、名詞、限制，並依問題分流到三個資料夾（source_prefix routing）提升精準度。LLM synthesis prompt 強調整合而非拼貼，要求重新定義 Knowledge Gaps 為產品限制。問題多元且覆蓋 Overview/Trends/Entities，但缺顯式 trends 類問題。 | 90 | skill_builder.py 設計10個全域問題，涵蓋 Overview、規格、健康指標、支援、評價與限制，並用 source_prefix 分流後由 LLM 統整，非單純拼貼。 |

## 整體評語

### 亮點

- 完整的技術決策文檔，每個節點都有明確的選型理由
- 多語言優化的 embedding 與 reranking 模型組合，適合繁體中文
- 結構化的資料夾分類與 metadata schema 設計，支援精細的檢索過濾
- 實現了增量更新與冪等性機制，避免重複建庫
- skill.md 包含完整的 9 個必要章節，展現 RAG 知識整合

### 改進建議

- 訂閱制 API 依賴（Gemini、Cohere、HuggingFace），無本地離線方案
- skill.md 生成依賴 LLM 合成，內容品質受模型與 prompt 影響
- README 未明確說明資料來源的授權與合規狀態
- reranking 為可選功能，預設未啟用可能影響檢索精度

---

_本份評分回饋由自動化評分管線（Anthropic + OpenAI 雙模型獨立評分 → 平均 → rescale → 老師加分）產出，僅作為個人學習參考。若對評分有疑問請於課堂或 office hour 提出。_
