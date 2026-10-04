# Task 3: 反思報告

本作業完成的系統是一個掛接在 Pi 上的本地記憶系統，核心流程為：

`capture -> store -> retrieve -> inject`

任務一完成了 JSON 持久化與純 BM25 lexical retrieval；任務二則在不破壞 pure BM25 baseline 的前提下，加入 hybrid retrieval、privacy filter、time decay，以及可由 Pi 直接操作的 `/recall`、`/forget` 進階功能。

---

## (1) 如何判斷「記憶有效」以及為何指標不可作弊

將「記憶有效」定義為：

> 當使用者提出 query 時，系統能在前 `k` 筆候選中找回真正相關的記憶，並且將較有用的記憶排在更前面。

對應到本作業提供的 benchmark，這表示：

- 系統要能從 `query` 找到對應的 `relevant_ids`
- 不只是「找得到」，還要盡量把正確記憶排在前面

因此本作業使用的三個指標分別衡量不同面向：




- **Recall@k**
  - 檢查前 `k` 筆是否至少有命中相關記憶
  - 代表 coverage

- **MRR**
  - 檢查第一個命中的相關記憶排在多前面
  - 代表 first-hit quality

- **nDCG@k**
  - 檢查整體排名品質
  - 當 query 對應多筆 relevant memory 時尤其重要

上述三個指標不容易作弊，原因有三：

1. **benchmark 已固定 query 與 gold relevant ids**
   - 每題都明確指定標準答案
   - 系統若回傳錯 id，即使文字看起來「像對的」，分數仍是錯的

2. **不是只看有沒有回傳結果**
   - 如果把所有記憶都塞進 top-k，Recall@k 可能勉強提高
   - 但 MRR 與 nDCG 會立刻反映排序品質不佳

3. **distractor 會造成真實懲罰**
   - 在大語料中，很多錯誤記憶共享相似高頻詞
   - 若系統只靠硬編碼或粗暴關鍵字堆疊，MRR / nDCG 通常會下降

因此，我認為「有效記憶」並非單純把資料存下來，而是：

- 可以持久保存
- 可以正確檢索
- 可以在實際 query 中以合理順序被取回

---

## (2) Benchmark 分數以及純 BM25 錯誤的原因

### Pure BM25（任務一）

| 資料集 | Recall@5 | MRR | nDCG@5 |
|---|---:|---:|---:|
| `corpus.jsonl` + `queries.jsonl` | 0.810 | 0.810 | 0.802 |
| `corpus_large.jsonl` + `queries_large.jsonl` | 0.838 | 0.826 | 0.795 |

### Hybrid retrieval（任務二）

| 資料集 | Recall@5 | MRR | nDCG@5 |
|---|---:|---:|---:|
| `corpus.jsonl` + `queries.jsonl` | 0.905 | 0.881 | 0.887 |
| `corpus_large.jsonl` + `queries_large.jsonl` | 0.838 | 0.863 | 0.815 |

可以看到：

- 小資料集上，Hybrid 在 Recall@5 / MRR / nDCG@5 都有明顯提升
- 大資料集上，Recall@5 與 pure BM25 持平，但 MRR 與 nDCG@5 提升
- 這代表 hybrid 主要改善的是「排序品質」與「語意對齊」，而不只是把更多文件塞進前五名

### 純 BM25 較容易失敗的題型

以下是 pure BM25 容易接不到或排名不夠前面的典型情境：

1. **Lexical mismatch**
   - 例如：`how big can an uploaded picture be?`
   - query 用的是 `picture`
   - 記憶可能寫成 `image`、`upload size`、`file limit`
   - 雖然語意接近，但字面 token 不重疊

2. **Synonym mismatch**
   - 例如：`what payment provider do we use?`
   - 記憶可能直接寫 `Stripe`
   - BM25 只能看文字重疊，不會自動把 `payment provider` 對應到 `Stripe`

3. **Cross-lingual mismatch**
   - 例如中文 query 去找英文或中英混合記憶
   - BM25 依賴 token overlap，對跨語言語意幾乎沒有幫助

4. **Distractor interference**
   - 在大語料中，有很多共享高頻詞的相似記憶
   - 即使真正答案在庫中，也可能被不完全相關的記憶蓋過

因此，pure BM25 是一個很好的 baseline，但它的能力邊界也很明確：只要 query 和記憶的字面表達不一致，效果就容易下降。

---

## (3) 確定性 vs 機率性的分界

這份系統中，刻意保留「確定性」與「機率性」兩條路徑，因為兩者在工程上扮演不同角色：

### 確定性

下列功能是確定性的：

- `JsonStore.add()` 的 SHA-256 去重
- `JsonStore.load()` / `_persist()` 的 JSON 持久化
- `memory/bm25.py::bm25_search()`
- `/recall`、`/forget` 的 CLI 與 bridge 參數解析

這些元件的特徵是：

- 相同輸入會得到相同輸出
- 不依賴模型推理
- 適合做單元測試與 benchmark baseline

這也是為什麼我保留 pure BM25 路徑，且不把 embedding 邏輯直接塞進 `bm25_search()`，因任務一需要可驗證、可重現、確定性的檢索基準。

### 機率性

下列功能帶有機率性或語意近似特性：

- `memory/hybrid.py::hybrid_search()`
- 本地 embedding 模型的語意相似度
- Pi 在 demo 中透過本地 LLM 觸發 `remember` 的決策

這些功能的特徵是：

- 它們不是單靠字面重疊，而是利用向量空間中的語意相似度
- 即使在同一台機器上通常仍可重現，性質上仍是「近似式」而非完全符號式
- 更適合改善 synonym / paraphrase / cross-lingual 類型問題

### 採取的設計邊界

將兩者的分工設計為：

- **BM25**：作為基線、單元測試目標、benchmark 對照組
- **Hybrid**：作為進階功能、性能提升路徑

以此分工設計的好處為：

1. 不會破壞任務一的可驗證性
2. 可以清楚比較 pure BM25 與 hybrid 的差異
3. 若 hybrid 效果不理想，仍可隨時退回穩定 baseline

---

## (4) Token 預算取捨

記憶系統不應該無限制地把所有相關記憶都注入 prompt，因為：

- context 是有限的
- 太多記憶會干擾主問題
- 過長注入會擠壓使用者真正的上下文空間

因此在 `build_injection()` 中，保留了 `token_budget` 的概念，讓系統在注入記憶時遵守上限。

### Token budget 太小的風險

- 可能只留下 1~2 筆記憶
- 有些次要但仍有價值的記憶被截掉
- recall 很高，但注入後的實際 coverage 不一定夠

### Token budget 太大的風險

- prompt 中充滿舊記憶
- 容易讓模型把注意力放在雜訊上
- 造成回答偏離主問題，甚至增加 hallucination 風險

### 取捨作法

將記憶注入當作「候選摘要」而不是「完整資料庫轉貼」：

- retrieval 負責找最相關的少量記憶
- injection 只帶入 budget 允許範圍內的內容
- 若記憶數量變多，應優先改善排序，而不是單純增加注入量

這也說明為什麼任務二中的 hybrid / decay 很重要，它們能在有限 token budget 下，把更值得注入的記憶排到前面。

---

## (5) 與 `/compact` 的關係

Pi 內建的 `/compact` 和這份作業的記憶系統看似都與「記憶」有關，但本質上解決的是不同問題。

### `/compact` 在做什麼

`/compact` 主要是：

- 壓縮**目前 session** 的對話
- 讓當前上下文更短
- 保留短期工作脈絡

它的重點是「同一場對話內如何節省 context」。

### 本作業的記憶系統在做什麼

本作業的記憶系統則是：

- 將 observation 存到硬碟
- 跨 session 持久保存
- 下次再透過 retrieval / injection 重新帶回

它的重點是「跨 session、跨時間的持久記憶」。

### 兩者關係

兩者應是互補關係，而非替代關係：

- `/compact` 解決的是**當前 session 太長**
- memory loop 解決的是**session 結束後資訊會消失**

因此，在實際 agent 系統中：

- `/compact` 可以維持短期對話品質
- 記憶系統可以維持長期專案知識

---

## (6) 我的系統 vs 手寫 `PROGRESS.md`

手寫 `PROGRESS.md` 的優點是：

- 簡單
- 可控
- 對人類讀者很直觀

但其限制包括：

1. **不可檢索**
   - 除非人工閱讀，否則 agent 很難即時找到關鍵片段

2. **不可排序**
   - `PROGRESS.md` 本身不會根據 query 自動挑選最相關的條目

3. **不容易和 agent workflow 整合**
   - 它不是一個能被 `retrieve()`、`inject()`、`/forget` 直接操作的記憶結構

相比之下，這套系統的優勢是：

- 可被 query 檢索
- 可 benchmark
- 可插入 Pi 生命週期
- 可加上 privacy filter、decay、hybrid retrieval
- 可由 `/recall`、`/forget` 主動操作

但它也並非完全取代 `PROGRESS.md`：

- `PROGRESS.md` 很適合人類維護高階里程碑與工作說明
- 記憶系統更適合存放 agent 在工作過程中累積的 durable facts

所以將兩者定位成：

- `PROGRESS.md`：人類導向的專案摘要
- memory system：agent 導向的可檢索長期記憶

---

## (7) 環境記錄

### 作業執行環境

- **OS**：Windows
- **Shell**：PowerShell
- **Python**：3.12
- **虛擬環境**：`.venv`

### Pi / LLM 環境

- **Pi extension runtime**：`@earendil-works/pi-coding-agent`
- **本地模型後端**：Ollama
- **本地模型**：`qwen2.5:7b`
- **模型架構**：Qwen2
- **參數量**：7.6B
- **context size**：32768
- **quantization**：Q4_K_M
- **用途**：Pi demo 與 remember / inject 展示

### GPU / VRAM

- **GPU**：NVIDIA GeForce RTX 2080 Ti
- **VRAM**：11 GB

### Embedding 模型

- **model**：`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- **用途**：任務二 hybrid retrieval
- **執行方式**：本地下載後本地推論

### 離線與成本

- benchmark 與單元測試主要在 Python 端完成
- demo 使用本地 LLM 與本地 embedding
- 無需雲端推論 API，因此沒有額外 API 成本

### Windows 額外注意事項

在 Windows 預設編碼下，benchmark 可能因輸出 `≈` 符號而遇到 `UnicodeEncodeError`。  
為了穩定重現，我在 README 中加入以下建議：

```powershell
chcp 65001
$env:PYTHONIOENCODING="utf-8"
```

---

## 結論

該份作業的核心價值，在於把「短期對話上下文」與「長期可檢索記憶」分開處理：

- 任務一提供可測試、可重現的 BM25 baseline 與持久化記憶
- 任務二進一步加入語意檢索、安全性與操作性
- Pi extension 則把這些 Python 記憶能力接回真實 agent workflow

此設計較接近實務系統：  
**確定性元件負責穩定與可驗證，機率性元件負責提升語意能力，而 extension 則負責把兩者接進 agent 的生命週期。**
