# NCKU-GenAI-Engineering-Portfolio_2026
為TAICA 臺灣大專院校人工智慧學程聯盟課程學習內容，是由國立成功大學莊坤達教授開設的研究所課程《生成式AI應用系統與工程》（Generative AI Application Systems and Engineering）。
# 🚀 國立成功大學《生成式AI應用系統與工程》課程專案集
**Generative AI Application Systems and Engineering - Portfolio**

本專案集收錄課程《生成式AI應用系統與工程》的所有實作成果，課程內容涵蓋從大型語言模型（LLM）的底層邏輯、系統架構設計，到遵循嚴格工程規範的 AI Agent Skills 系統化構建與確定性驗證 (Deterministic Validation)。

## 🧠 核心技術與技能 (Core Competencies)
透過本系列專案的實作，我具備了以下生成式 AI 工程開發能力：
* **檢索增強生成與記憶系統 (RAG & Memory)**：具備從零建置個人化 RAG 系統的能力，並能實作結合 BM25 與向量 Embedding 的混合檢索 (Hybrid Retrieval)，加入時間衰減與隱私過濾機制。
* **代理人技能開發 (Agent Skills)**：熟悉透過 Hermes 與 LiteLLM Gateway 掛載自訂工具，並嚴格遵循 File-based Result Contract 進行系統解耦。
* **結構化自動驗證 (Deterministic Validation)**：開發具備自我測試 (Self-test) 能力的程式碼生成、自動化漏洞分析與 SQL 生成驗證系統，確保 AI 產出具備可公開重現的驗證場景。
* **跨語言整合與輸出渲染**：實作 Node.js (TypeScript) Extension 與 Python 子進程 (Subprocess) 的雙向溝通；熟練運用 Markdown 控制生成式 AI 的結構化輸出。

---

## 📂 專案列表 (Projects Overview)

本系列包含 4 個漸進式實作任務與 1 個期末大型專案：

### 1. [HW1: Markdown Creation and Rendering Practice](./hw1-markdown-creation-and-rendering-practice/)
* **重點**：奠定生成式 AI 應用的前端輸出基礎。
* **說明**：實作 Markdown 文本的自動生成與網頁端渲染技術，確保 AI 產出的結構化文本（如表格、程式碼區塊）能正確且美觀地呈現給終端使用者。

### 2. [HW2: Implementation of SDD Specification Optimization](./hw2-implementation-of-sdd-specification-optimization/)
* **重點**：軟體設計文件 (Software Design Document) 的架構最佳化。
* **說明**：探討生成式 AI 系統的工程設計規範，將複雜的 AI 邏輯抽象化並模組化，確保系統具備可擴展性與高維護性。

### 3. [HW3: Build Your Personal RAG](./hw3-build-your-personal-rag/)
* **重點**：檢索增強生成 (Retrieval-Augmented Generation) 核心開發。
* **說明**：從零構建專屬的 RAG 知識庫系統。包含文件解析、Embedding 向量化、資料庫檢索與 LLM 答案生成，有效解決模型幻覺問題。

### 4. [HW4: Pi Memory Implementation](./hw4-pi-memory/)
* **重點**：可掛接至 Pi Agent 的高階本地記憶系統 (Memory System)。
* **說明**：實作 `capture -> store -> retrieve -> inject` 核心記憶迴路。具備 BM25 與向量 Embedding 的混合檢索 (Hybrid Retrieval) 能力，並加入時間衰減 (Time Decay) 與正則隱私過濾 (Privacy Filter) 機制。透過 Node.js Extension 與 Python Subprocess 雙向溝通，讓前端 Pi Agent 能使用 `/recall`、`/forget` 等指令跨 Session 存取本地 JSON 記憶。

### 5. [Final Project: AIASE 2026 Multi-Track AI Agent Skills](./final-project/)
* **重點**：多軌道 AI 代理人技能開發與確定性驗證 (Deterministic Validation)。
* **說明**：依據嚴格的 File-based Result Contract 規範，透過 Hermes CLI (`--toolsets skills,terminal --yolo -Q -q`) 開發三大獨立 AI 技能軌道：
  1. **Basic Track (Text2SQL)**：自動生成 SQLite 查詢，並透過 Python 腳本驗證語法與 Schema 相容性。
  2. **Pairwise Track (Code Author & Bug Hunter)**：自動生成受限 Python 程式碼並執行 Self-test；結構化分析候選程式碼並輸出精準的 Bug Report。
  3. **Open Track (Open Code Repair)**：自動修復 Buggy Code，並透過 Deterministic Evaluator 直接比較修補前後在同一樣本上的測試表現，確保修補結果具備嚴謹的客觀數據證據。


