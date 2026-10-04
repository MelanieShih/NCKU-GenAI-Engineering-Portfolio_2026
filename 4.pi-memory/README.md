[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/uuH2W7ZW)
# AIASE2026 HW4 - Pi Memory (Python)

本作業實作一個可掛接到 Pi 的本地記憶系統，核心流程為：

`capture -> store -> retrieve -> inject`

其中：

- `memory/store.py` 負責 JSON 持久化、去重與記憶刪除
- `memory/bm25.py` 提供純 BM25 lexical retrieval baseline
- `memory/hybrid.py` 提供 BM25 + embedding 的 hybrid retrieval
- `memory/core.py` 串接 capture / retrieve / inject / time decay
- `memory/cli.py` 提供 `capture`、`recall`、`forget`、`inject` 等 CLI 入口
- `pi-bridge/extension.ts` 讓 Pi 透過 subprocess 呼叫 Python 記憶系統

本專案符合 HW4 的兩個主軸：

1. **任務一**：完成可測試的記憶迴路核心（Store + BM25 + injection）
2. **任務二**：加入進階功能並接回 Pi 使用

---

## 設計概述

### 系統架構

```text
Pi (local model via Ollama / OpenAI-compatible endpoint)
    │
    │ before_agent_start / remember / /recall / /forget
    ▼
pi-bridge/extension.ts
    │
    │ subprocess: python -m memory.cli ...
    ▼
memory/core.py
    ├─ capture -> memory/store.py
    ├─ retrieve -> memory/bm25.py or memory/hybrid.py
    └─ inject
    ▼
memory JSON file on disk
```

### 任務一功能

- `JsonStore.load()`：讀取既有 JSON 記憶檔；檔案不存在時安全回空
- `JsonStore._persist()`：建立目錄並寫回 UTF-8 JSON
- `JsonStore.add()`：以 `summary` 的 SHA-256 做去重，並保留外部傳入的 `id`
- `bm25_search()`：實作標準、確定性的 BM25 排序

### 任務二功能

本次完成的任務二項目如下：

1. **Hybrid retrieval**
   - 保留 `memory/bm25.py::bm25_search()` 作為純 BM25 baseline
   - 另以 `memory/hybrid.py::hybrid_search()` 實作 BM25 + embedding 融合
   - 可透過 `mode=bm25|hybrid` 或 `PI_MEMORY_RETRIEVAL_MODE` 切換

2. **Privacy Filter**
   - 在 observation 寫入記憶前以 regex 遮蔽敏感資訊
   - 例如：`sk-...`、`ghp_...`、`password=...`、`api_key=...`

3. **Time Decay**
   - 依 `last_used_at` 對久未使用記憶做衰減重排
   - 透過環境變數開關，不影響 pure BM25 benchmark baseline

4. **`/recall`、`/forget`**
   - 在 Pi bridge 中新增 slash commands
   - 讓使用者可直接在 Pi 內列出、查詢與刪除記憶

### 與 Pi 的連接方式

本作業的 Python 記憶系統並不直接寫在 Pi 內，而是透過 extension bridge 連接：

- `before_agent_start`：自動呼叫 `python -m memory.cli inject`
- `remember` tool：呼叫 `python -m memory.cli capture`
- `/recall`：呼叫 `python -m memory.cli recall`
- `/forget`：呼叫 `python -m memory.cli forget`

因此，Pi 只負責 agent 生命週期與工具調度，記憶邏輯仍維持在 Python 端。

---

## 環境

本專案測試與 demo 使用的環境如下：

- **OS**：Windows
- **Python**：3.12
- **虛擬環境**：`.venv`
- **本地 LLM（demo 用）**：`qwen2.5:7b`
- **模型參數量**：7.6B
- **context size**：32768
- **後端**：Ollama（OpenAI-compatible local endpoint）
- **endpoint**：`http://localhost:11434/v1`
- **GPU / VRAM**：NVIDIA GeForce RTX 2080 Ti，11 GB VRAM
- **embedding model**：`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`

說明：

- 單元測試與 benchmark 主要驗證 Python 記憶系統，**不依賴模型強弱**
- 本地模型主要用於 **Pi demo**，例如展示 `remember` 與跨 session 注入
- 整個作業執行與 demo 都不需要呼叫雲端推論 API

---

## 安裝與測試

### 1. 安裝依賴

```powershell
pip install -r requirements.txt
```

### 2. Windows 建議先設定編碼

`benchmark/run_benchmark.py` 在 Windows 預設 `cp950` 下可能因 `≈` 符號出現編碼錯誤，因此建議先執行：

```powershell
chcp 65001
$env:PYTHONIOENCODING="utf-8"
```

### 3. 執行單元測試

```powershell
$env:PYTHONPATH="."
pytest -q
```

本專案目前測試結果：

```text
13 passed
```

---

## 如何跑 benchmark

### Pure BM25 baseline

```powershell
$env:PYTHONPATH="."
$env:PI_MEMORY_RETRIEVAL_MODE="bm25"
$env:PI_MEMORY_ENABLE_DECAY="0"

python benchmark/run_benchmark.py --k 5
python benchmark/run_benchmark.py --corpus corpus_large.jsonl --queries queries_large.jsonl --k 5
```

### Hybrid retrieval

```powershell
$env:PYTHONPATH="."
$env:PI_MEMORY_RETRIEVAL_MODE="hybrid"
$env:PI_MEMORY_ENABLE_DECAY="0"

python benchmark/run_benchmark.py --k 5
python benchmark/run_benchmark.py --corpus corpus_large.jsonl --queries queries_large.jsonl --k 5
```

### Benchmark 結果

| 模式 | 資料集 | Recall@5 | MRR | nDCG@5 |
|---|---|---:|---:|---:|
| BM25 | `corpus.jsonl` + `queries.jsonl` | 0.810 | 0.810 | 0.802 |
| BM25 | `corpus_large.jsonl` + `queries_large.jsonl` | 0.838 | 0.826 | 0.795 |
| Hybrid | `corpus.jsonl` + `queries.jsonl` | 0.905 | 0.881 | 0.887 |
| Hybrid | `corpus_large.jsonl` + `queries_large.jsonl` | 0.838 | 0.863 | 0.815 |

---

## 如何掛 bridge 到 Pi 並重現 demo

### 1. 準備 demo 記憶資料

```powershell
cd "C:\Users\Lab539\Desktop\成大AI\AIASE2026-HW4"
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH="."
$env:PI_MEMORY_PATH="$env:TEMP\hw4-demo-pi-memory.json"
Remove-Item $env:PI_MEMORY_PATH -ErrorAction SilentlyContinue

python -m memory.cli capture --summary "Use pnpm as package manager" --tags tooling
python -m memory.cli capture --summary "Run pytest -q before commit" --tags testing
python -m memory.cli capture --summary "Payment provider is Stripe" --tags billing
python -m memory.cli capture --summary "Deploy with docker compose on aws" --tags deploy
python -m memory.cli capture --summary "Weekly team sync is Tuesday 10am" --tags meeting
python -m memory.cli capture --summary "Use black and ruff for code style checks" --tags style
python -m memory.cli capture --summary "Feature flags are used for gradual rollout" --tags rollout
python -m memory.cli capture --summary "API authentication uses JWT bearer tokens" --tags auth
python -m memory.cli capture --summary "Python version is 3.10 or higher" --tags python
python -m memory.cli capture --summary "Chinese embeddings use a local sentence-transformers model" --tags embedding
```

確認資料：

```powershell
python -m memory.cli recall --list 20
```

### 2. 啟動 Pi 並載入 extension

若系統沒有 `pi` 指令，可直接使用：

```powershell
$env:PYTHONPATH="."
$env:PI_MEMORY_PATH="$env:TEMP\hw4-demo-pi-memory.json"
npx @earendil-works/pi-coding-agent -e .\pi-bridge\extension.ts
```

### 3. Pi 內 demo 指令

#### `remember`

```text
Please remember that we use pnpm as the package manager.
```

#### `/recall`

```text
/recall
/recall package manager
/recall payment provider
/recall deploy docker
```

#### `/forget`

先在 PowerShell 取一筆 id：

```powershell
$id = ((python -m memory.cli recall --list 20 | Out-String) | python -c "import sys,json; s=sys.stdin.buffer.read().decode('utf-8-sig'); data=json.loads(s); print(data[0]['id'])")
$id
```

再回 Pi 輸入：

```text
/forget <memory_id>
/recall --list
```

#### 重現 inject / 跨 session 記憶

1. 在 Pi 中先讓它記住一條事實
2. 關閉 Pi
3. 用同一個 `PI_MEMORY_PATH` 重開 Pi
4. 詢問：

```text
What package manager do we use?
```

若能回答 `pnpm`，代表 `before_agent_start -> inject` 已生效。

---

## Pi 與相關套件說明

本作業直接或間接使用到的 Pi 元件如下：

- **直接使用**
  - `@earendil-works/pi-coding-agent`
    - 提供 `ExtensionAPI`
    - 載入 `pi-bridge/extension.ts`
    - 執行 `before_agent_start`、`remember`、`/recall`、`/forget`

- **間接使用**
  - `pi-ai`
    - 負責模型 provider / model abstraction
    - 讓 Pi 能以統一介面接到本地 OpenAI-compatible endpoint
  - Pi agent runtime / core
    - 負責 session lifecycle、slash command 執行與工具調度

---

## 任務二完成項目與接到 Pi 的方式

### 1. Hybrid retrieval

- Python 端：`memory/hybrid.py`
- 使用方式：
  - CLI：`python -m memory.cli recall --query "..." --mode hybrid`
  - benchmark：`$env:PI_MEMORY_RETRIEVAL_MODE="hybrid"`
- Pi 端：
  - 目前 `/recall <query>` 預設走 CLI recall 路徑
  - 若使用 `--mode hybrid`，會轉交 Python CLI 的 hybrid retrieval

### 2. Privacy Filter

- Python 端：在 capture 流程先遮蔽敏感字串
- 使用方式：

```powershell
python -m memory.cli capture --summary "token sk-abcDEF1234567890 password=hello123"
python -m memory.cli recall --list 5
```

- Pi 端：
  - 只要 Pi 透過 `remember` 呼叫 `capture`，就會自動經過 privacy filter

### 3. Time Decay

- Python 端：在 retrieval 後根據 `last_used_at` 做重排
- 使用方式：

```powershell
$env:PI_MEMORY_ENABLE_DECAY="1"
$env:PI_MEMORY_DECAY_HALF_LIFE_HOURS="24"
python -m memory.cli recall --query "deploy docker aws" --k 5 --mode bm25 --decay on
```

- Pi 端：
  - 透過 `/recall` 轉到 Python CLI 後即可啟用相同 decay 邏輯

### 4. `/recall`、`/forget`

- Pi extension 以 `pi.registerCommand(...)` 註冊 slash commands
- 實際執行時會呼叫：
  - `python -m memory.cli recall ...`
  - `python -m memory.cli forget --id ...`

---

## 檔案位置

- 記憶核心：`memory/`
- Pi bridge：`pi-bridge/extension.ts`
- benchmark：`benchmark/run_benchmark.py`
- demo 資料：`demo/`

DEMO 截圖與影片存放位置：

- 截圖 `demo/screenshots/`
- 影片連結 `demo/README.md`
