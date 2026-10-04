# AIASE 2026 Final Project

本專案依課程規範完成三個 Track 的提交內容，包含：

- **Basic Track**：`text2sql-melanieshih`
- **Pairwise Track**：`code-author-melanieshih`、`bug-hunter-melanieshih`
- **Open Track**：`open-code-repair-melanieshih`

本版 README 已同步老師後續公告之更新規範，重點如下：

- 正式 Hermes 呼叫格式採用 `--toolsets skills,terminal --yolo -Q -q`
- 評分主契約改為 **file-based result contract**
- skill 應透過 `scripts/run.py` 將最終結果寫入 `AIASE_RESULT_PATH`
- chat stdout 僅作輔助觀察，不再作為唯一評分依據

---

## 1. 專案結構與功能摘要

### 1.1 Basic Track：`text2sql-melanieshih`

- 路徑：`skills/text2sql-melanieshih/`
- 主要檔案：
  - `skills/text2sql-melanieshih/SKILL.md`
  - `skills/text2sql-melanieshih/scripts/validate_sql.py`
  - `skills/text2sql-melanieshih/scripts/run.py`

功能摘要：

- 根據 `question` 與 `db_schema` 產生唯讀 SQLite 查詢
- 以 deterministic validator 驗證 SQL 安全性與 schema 相容性
- 以 `run.py` 將最終 contract 寫入結果檔

### 1.2 Pairwise Track：`code-author-melanieshih`、`bug-hunter-melanieshih`

- 路徑：
  - `skills/code-author-melanieshih/`
  - `skills/bug-hunter-melanieshih/`
- 主要檔案：
  - `skills/code-author-melanieshih/scripts/selftest.py`
  - `skills/code-author-melanieshih/scripts/run.py`
  - `skills/bug-hunter-melanieshih/scripts/analyze.py`
  - `skills/bug-hunter-melanieshih/scripts/run.py`

功能摘要：

- `code-author`：根據任務描述與限制產生 Python 函式，並以 deterministic self-test 驗證 entry function、LoC、forbidden imports 與局部 correctness
- `bug-hunter`：分析候選程式並輸出結構化 bug report，欄位包括 `verdict`、`bugs`、`type`、`severity`、`line range` 與 `suggested_fix`

### 1.3 Open Track：`open-code-repair-melanieshih`

- 路徑：`skills/open-code-repair-melanieshih/`
- 主要檔案：
  - `skills/open-code-repair-melanieshih/SKILL.md`
  - `skills/open-code-repair-melanieshih/scripts/evaluate_repair.py`
  - `skills/open-code-repair-melanieshih/scripts/run.py`
  - `dev_set/open_track/repair_tasks/`

功能摘要：

- 接收 buggy Python function、任務描述、限制條件與測試樣本
- 產生 repaired implementation
- 比較修補前與修補後在相同樣本上的測試表現
- 將 `repair_evaluation` 與修補結果寫入結果檔

---

## 2. 環境安裝與 Hermes 設定

### 2.1 Python 套件

```bash
python -m pip install -r requirements.txt
```

目前 `requirements.txt` 包含：

- `radon==6.0.1`
- `pytest==8.3.3`
- `PyYAML==6.0.2`

若某 skill 需要額外套件，則另以該 skill 底下的 `scripts/requirements.txt` 管理。

### 2.2 Hermes / LiteLLM 環境變數

課程環境使用 Hermes 經由 LiteLLM Gateway 呼叫模型。`base_url` 與 `api_key` 應置於本機環境變數，不應寫死於 repo 中。

建議將設定寫入 `~/.hermes/.env`：

```bash
AIASE_LITELLM_BASE_URL=https://litellm.netdb.csie.ncku.edu.tw/v1
AIASE_LITELLM_KEY=<YOUR_TOKEN>
```

對應範例檔案：

- `docs/hermes-config.example.yaml`
- `docs/hermes-env.example`

### 2.3 結果檔規格

更新後的正式評分流程改採 **file-based result contract**：

- `run_dev.py` 會自動設定 `AIASE_RESULT_PATH`
- skill 的 `scripts/run.py` 需將最終 JSON 寫入該路徑
- 若未設定 `AIASE_RESULT_PATH`，各 skill 會 fallback 到 `./aiase_result.json`

因此：

- `aiase_result.json` 通常只代表**最近一次成功寫出的單題結果**
- 不代表整批 dev set 的彙總結果

---

## 3. 課程規格對應

### 3.1 Hermes 正式呼叫格式

目前課程正式呼叫格式為：

```bash
hermes chat --toolsets skills,terminal --yolo -Q -q '/skill-name {json}'
```

參數意義：

- `skills,terminal`：同時提供 skill 載入與 `scripts/` 執行能力
- `--yolo`：非互動評分流程中自動放行工具呼叫
- `-Q`：避免 chat 輸出格式美化干擾結果擷取
- `-q`：非互動式單行 prompt 呼叫

本 repo 根目錄的 `run_dev.py` 已同步使用此格式。

### 3.2 Pairwise Track 雙角色提交

Pairwise Track 需同時提交兩個角色：

- `code-author`
- `bug-hunter`

`PAIRWISE_ROLE.md` 目前同時保留新舊相容格式，確保本地檢查與課程流程均可辨識。

### 3.3 Open Track 可驗證性要求

Open Track 的重點不在主題新穎性，而在：

- scenario 可公開重現
- metric 可由 deterministic script 驗證
- 結果不可僅依賴模型自述

本專案採用 **code repair** 主題，並以 deterministic evaluator 比較 buggy version 與 repaired version 在同一組樣本上的結果，符合課程對 verifiable scenario 的要求。

---

## 4. deterministic 驗證方式

### 4.1 Repo 規格檢查

```bash
python3 verify_repo.py --github-id melanieshih
```

目前結果：

```text
passed: 28/28
```

### 4.2 全部測試

```bash
python -m pytest tests -q
```

目前結果：

```text
188 passed
```

> 在 WSL 與 `/mnt/c/...` 掛載環境下，可能出現 `.pytest_cache` 寫入警告；此警告不影響測試正確性。

### 4.3 Pairwise deterministic helper

```bash
python -m pytest tests/test_code_author_selftest.py -q
```

### 4.4 Open Track deterministic helper

```bash
python -m pytest tests/test_open_code_repair.py -q
```

目前結果：

```text
4 passed
```

---

## 5. Live 單題測試指令

### 5.1 Basic Track：Text2SQL

```bash
hermes chat --toolsets skills,terminal --yolo -Q -q '/text2sql-melanieshih {"task_id":"task_nl2sql_001","question":"List the names of all students.","db_schema":"CREATE TABLE Students (sid INTEGER PRIMARY KEY, name TEXT);","dialect":"sqlite"}'
```

成功判準：

- `scripts/run.py` 已寫出結果檔
- 結果檔包含 `task_id`、`sql`、`rationale`、`confidence`

### 5.2 Pairwise：Bug Hunter

```bash
hermes chat --toolsets skills,terminal --yolo -Q -q '/bug-hunter-melanieshih {"task_id":"task_pair_EXAMPLE","task_description":"Implement reverse_words(s): return the words in reverse order separated by a single space. Empty string returns an empty string.","constraints":{"entry_function":"reverse_words","max_loc":500,"imports_forbidden":["os","sys","subprocess"]},"code":"def reverse_words(s):\n    return s[::-1]"}'
```

成功判準：

- `scripts/run.py` 已寫出結果檔
- 結果檔包含 `task_id`、`verdict`、`bugs`、`confidence`

### 5.3 Pairwise：Code Author

```bash
hermes chat --toolsets skills,terminal --yolo -Q -q '/code-author-melanieshih {"task_id":"task_pair_EXAMPLE","task_description":"Implement reverse_words(s): return the words in reverse order separated by a single space. Empty string returns an empty string.","constraints":{"entry_function":"reverse_words","max_loc":500,"imports_forbidden":["os","sys","subprocess"]}}'
```

成功判準：

- `scripts/run.py` 已寫出結果檔
- 結果檔包含 `task_id`、`code`、`loc`、`self_test_results`、`confidence`

### 5.4 Open Track：Open Code Repair

```bash
hermes chat --toolsets skills,terminal --yolo -Q -q '/open-code-repair-melanieshih {"task_id":"open_repair_001","task_description":"Repair binary_search(arr, target): return the index of target in sorted arr, or -1 if not found.","buggy_code":"def binary_search(arr, target):\n    left, right = 0, len(arr) - 1\n    while left < right:\n        mid = (left + right) // 2\n        if arr[mid] == target:\n            return mid\n        if arr[mid] < target:\n            left = mid + 1\n        else:\n            right = mid - 1\n    return -1\n","constraints":{"entry_function":"binary_search","max_loc":500,"imports_forbidden":["os","sys","subprocess"]}}'
```

成功判準：

- `scripts/run.py` 已寫出結果檔
- 結果檔包含 `repaired_code`、`repair_summary`、`confidence`、`repair_evaluation`
- `repair_evaluation` 應顯示：
  - `improved: true`
  - `fully_fixed: true`

---

## 6. 目前已確認的成果

### 6.1 Basic Track

- `text2sql` live 單題成功
- `validate_sql.py` 可直接驗證 SQL
- 公開 Basic dev set 首次整批執行曾受 LiteLLM / Hosted vLLM timeout 影響，得到 `15/21 passed`
- 失敗題 `011`、`014`、`015`、`016`、`017`、`EXAMPLE` 經逐題補跑後皆成功
- 因此，Basic Track 已在新版 file-based runner 下完成公開 dev set 驗證

### 6.2 Pairwise Track

- `code-author` live 單題成功
- `bug-hunter` live 單題成功
- `code-author` dev set 首次為 `5/6`，失敗題 `task_pair_001` 補跑成功
- `bug-hunter` dev set 首次為 `5/6`
- `bug-hunter` 的 `task_pair_EXAMPLE` 失敗原因為 student-facing minimal example 不含 `code` 欄位，與 bug-hunter 的輸入需求不完全對齊；改以附 `code` 的 live 單題測試後成功

### 6.3 Open Track

- `pytest tests/test_open_code_repair.py -q` 通過
- Open Track live 單題成功
- `binary_search` scenario 實測顯示：
  - buggy version：`4/5`
  - repaired version：`5/5`
  - `improved = true`
  - `fully_fixed = true`

---

## 7. 已知限制

### 7.1 `<|channel>thought` / `<channel|>` marker

在課程 Gemma 4 / LiteLLM live inference 路徑上，部分回應會混入：

```text
<|channel>thought
<channel|>
```

目前判斷如下：

- 此現象會影響 stdout 可讀性
- 但在新版 file-based 規格下，評分主體已改為結果檔，故不再是主要評分阻礙
- 問題較可能位於課程 Gemma 4 endpoint、vLLM reasoning parser 或 LiteLLM router 的輸出處理鏈

### 7.2 LiteLLM / Hosted vLLM timeout 與 connection error

在 batch 執行或部分 live 測試中，曾出現：

- `HTTP 500`
- `litellm.MidStreamFallbackError`
- `Hosted_vllmException - Timeout on reading data from socket`
- `Connection error`

本專案的處理方式為：

- 以 deterministic tests、repo 驗證與 live 單題成功作為主要完成證據
- 對 timeout 題目進行 targeted rerun，以區分 skill 邏輯錯誤與推論服務鏈不穩

---
