# AIASE 2026 Final Project Report

> GitHub ID: `melanieshih`

---

## 1. 專案總覽

本專案依課程規範完成三個 Track 之核心 skill：

1. **Basic Track**：`text2sql-melanieshih`
2. **Pairwise Track**：`code-author-melanieshih`、`bug-hunter-melanieshih`
3. **Open Track**：`open-code-repair-melanieshih`

整體實作採三層化設計：

- **結構層**：完成 repo 結構、`SKILL.md`、`PAIRWISE_ROLE.md`、`OPEN_TRACK.md` 與相關宣告檔
- **deterministic 驗證層**：將安全檢查、格式保證與局部 correctness 驗證下放至 `scripts/`
- **模型協作層**：以 Hermes 經 LiteLLM 進行 live 單題驗證，確認 skill 可在實際代理流程中被呼叫

課程後續公告將正式評分流程由 chat 中的 fenced JSON 更新為 **file-based result contract**，因此，本專案後續所有 skill 已統一採用以下原則：

- `run_dev.py` 以 `--toolsets skills,terminal --yolo -Q -q` 呼叫 Hermes
- 各 skill 的 `scripts/run.py` 將最終 JSON 寫入 `AIASE_RESULT_PATH`
- 若未設定 `AIASE_RESULT_PATH`，則 fallback 至 `./aiase_result.json`
- chat stdout 僅作輔助觀察，不再作為唯一評分依據

此設計有助於將模型生成能力與可驗證之工程規則明確分離，並將錯誤來源區分為 deterministic 邏輯問題、契約包裝問題或推論服務鏈問題。

---

## 2. Basic Track：Text2SQL Skill

### 2.1 任務要求

Basic Track 要求 skill 接收以下輸入欄位：

- `task_id`
- `question`
- `db_schema`
- optional `dialect`

並產生：

- 一段唯讀 SQLite 查詢
- 一份由 `scripts/run.py` 寫入結果檔的 JSON contract

在新版規範下，Basic Track 的主要完成證據不再是 chat 中的 fenced JSON，而是：

1. skill 成功寫出結果檔
2. `run_dev.py` 成功讀回結果檔
3. `sql` 執行結果與 `gold_sql` 達成 bag equality

### 2.2 元件分工

Basic Track 由四個元件協同組成：

1. **`skills/text2sql-melanieshih/SKILL.md`**
   - 定義 Hermes 如何理解輸入 payload、推理步驟與 helper 使用方式
   - 明確要求以 `validate_sql.py` 與 `run.py` 完成最終流程

2. **`skills/text2sql-melanieshih/scripts/validate_sql.py`**
   - 以 deterministic 規則檢查 SQL 是否唯讀
   - 拒絕 DDL、DML、`PRAGMA` 等高風險語句
   - 在 SQLite 上驗證 SQL 與輸入 schema 的相容性

3. **`skills/text2sql-melanieshih/scripts/run.py`**
   - 將最終 contract 寫入 `AIASE_RESULT_PATH`
   - 若該環境變數不存在，則 fallback 至 `./aiase_result.json`

4. **repo 根目錄 `run_dev.py` 與 `aiase_contract.py`**
   - `run_dev.py`：建立 task payload、設定 `AIASE_RESULT_PATH`、呼叫 Hermes、讀取結果檔並進行比對
   - `aiase_contract.py`：提供共用 contract 檢查與結果讀取邏輯

### 2.3 設計理由

此分工可將任務責任切分為：

- LLM：根據自然語言問題產生候選 SQL
- validator：檢查安全性與 schema 相容性
- wrapper：保證結果檔格式一致
- runner：保證評分方式與課程更新後規範一致

相較於僅以 prompt 要求模型直接輸出 SQL，此設計具備以下優點：

- 安全規則可由程式明確落實
- 若失敗發生，可快速定位於 SQL 本身、validator、wrapper 或推論服務鏈
- file-based contract 降低 chat 格式變動或 reasoning token 汙染對評分的影響

### 2.4 執行結果

Basic Track 目前已完成以下驗證：

- `validate_sql.py` 的 direct tests 通過
- `text2sql` live 單題成功
- `run_dev.py --track basic --task task_nl2sql_EXAMPLE` 成功
- 公開 Basic dev set 整批執行時，首次結果為：

```text
15/21 passed
```

當時失敗題包括：

- `task_nl2sql_011`
- `task_nl2sql_014`
- `task_nl2sql_015`
- `task_nl2sql_016`
- `task_nl2sql_017`
- `task_nl2sql_EXAMPLE`

其主要失敗型態為：

- `HTTP 500`
- `litellm.MidStreamFallbackError`
- `Hosted_vllmException - Timeout on reading data from socket`
- `no result file (task not produced)`

上述失敗題經逐題補跑後，全部成功。例如：

- `task_nl2sql_011` → `PASS`
- `task_nl2sql_014` → `PASS`
- `task_nl2sql_015` → `PASS`
- `task_nl2sql_016` → `PASS`
- `task_nl2sql_017` → `PASS`
- `task_nl2sql_EXAMPLE` → `PASS`

因此可判定：

- Basic Track 的 SQL correctness、deterministic validation 與 file-based contract 皆成立
- 首次 batch failure 主要反映推論服務鏈不穩，而非 repo 端 deterministic logic 失敗

---

## 3. Pairwise Track：Code Author 與 Bug Hunter

### 3.1 任務定位與雙角色結構

Pairwise Track 需同時提交兩個角色：

- `code-author`
- `bug-hunter`

本專案同步完成：

- `skills/code-author-melanieshih/`
- `skills/bug-hunter-melanieshih/`
- `PAIRWISE_ROLE.md`

此配置可同時覆蓋：

- **程式生成能力**：依描述產出 Python 函式
- **程式審查能力**：對候選程式進行結構化錯誤分析

### 3.2 Code Author 設計

`code-author` 的任務是根據 `task_description` 與 `constraints` 產出 Python 函式，並滿足：

- 函式名稱符合 `constraints.entry_function`
- 程式長度不超過 `constraints.max_loc`
- 不使用 `constraints.imports_forbidden`
- 能處理常見 edge cases
- 由 `scripts/run.py` 寫出結果檔

主要 deterministic helper 包括：

- `skills/code-author-melanieshih/scripts/selftest.py`
- `skills/code-author-melanieshih/scripts/run.py`

其中 `selftest.py` 負責：

- 抽取與確認 entry function
- 計算 SLOC / LoC
- 檢查 forbidden imports
- 對常見 edge cases 進行局部驗證
- 將錯誤訊息整理為可由 skill 使用的結構化資訊

### 3.3 Bug Hunter 設計

`bug-hunter` 的任務是讀取候選 Python 程式與任務描述，輸出結構化 bug report，結果檔中至少包含：

- `task_id`
- `verdict`
- `bugs[]`
- `confidence`

其中每個 `bugs[]` 項目包含：

- `type`
- `severity`
- `line_start` / `line_end`
- `description`
- `suggested_fix`

主要 deterministic helper 為：

- `skills/bug-hunter-melanieshih/scripts/analyze.py`
- `skills/bug-hunter-melanieshih/scripts/run.py`

analyzer 先以 AST 與 task-agnostic probes 取得程式形狀與可疑區域，再由 skill 將分析結果整合為語意清楚的 bug report，此設計可降低純語言模型審查時之過度猜測，提升 line range 與 bug type 的一致性。

### 3.4 設計理由

Pairwise Track 最常見的失敗點通常不是演算法本身，而是：

- function name 不符
- LoC 超標
- 違反 import 限制
- output contract 不穩定
- bug report 噪音過多或 line number 不準

因此，本專案優先完成 deterministic harness，再由模型進行生成或分析，並透過 wrapper 寫入結果檔，降低「看似成功、實際不符合 contract」的風險。

### 3.5 執行結果

目前已確認：

- `PAIRWISE_ROLE.md` 符合雙角色提交要求
- `code-author` live 單題成功
- `bug-hunter` live 單題成功

`code-author` 公開 pairwise dev set 首次執行結果：

```text
5/6 passed
```

唯一失敗題為：

- `task_pair_001` → `no result file (task not produced)`

經單題補跑後：

```text
task_pair_001 → PASS
```

因此 `code-author` 可視為完成本地驗證。

`bug-hunter` 公開 pairwise dev set 首次執行結果：

```text
5/6 passed
```

失敗題為：

- `task_pair_EXAMPLE`

此題之 student-facing payload 位於 `dev_set/pairwise/task_pairwise_EXAMPLE.json`，其欄位僅包含：

- `task_id`
- `task_description`
- `constraints`
- `sample_tests`

但 `bug-hunter` 的 skill 輸入需求必須包含：

- `task_id`
- `task_description`
- `code`

因此，`task_pair_EXAMPLE` 對 `bug-hunter` 而言屬於 **minimal example 與 skill input mismatch**，失敗原因不是 skill 本體無法完成任務，而是 example payload 未提供待審查程式碼，改以附帶 `code` 欄位的 live 單題測試後，`bug-hunter` 能正常產生結果檔與結構化 bug report，故可合理判定 bug-hunter 的核心邏輯已成立。

---

## 4. Open Track：Open Code Repair

### 4.1 題目選擇與任務目標

Open Track 採用之 skill 為：

- `open-code-repair-melanieshih`

其任務為：

- 輸入一段 buggy Python function、任務描述、函式限制與測試樣本
- 產生一段 repaired implementation
- 以 deterministic evaluator 比較修補前後在同一組測試下的表現
- 由 `scripts/run.py` 將最終 repair contract 寫入結果檔

此題目選擇的核心目的，在於建立一個兼具生成與驗證的 Open Track skill，相較於僅輸出文字性修補建議的設計，code repair 可透過實際執行結果量化 skill 是否有效，較符合課程對 verifiable scenario 的要求。

### 4.2 題目選擇理由

選擇 code repair 作為 Open Track 主題，主要基於以下考量：

1. **可驗證性高**  
   同一組測試可同時套用於 buggy version 與 repaired version，適合定義明確且不可由敘述性輸出規避的 metric。

2. **與前兩階段具連續性**  
   Basic Track 聚焦於 SQL 生成與驗證，Pairwise Track 聚焦於程式生成與錯誤分析，Open Track 則進一步整合為發現問題、產生修補版本並驗證改善幅度的完整工作流。

3. **不易以模型自述取代真正修補**  
   若 skill 僅輸出修補說明而未提供可執行程式碼，`repair_delta`、`improved` 與 `fully_fixed` 等指標不可能成立。

### 4.3 系統架構

Open Track 由四個部分構成：

1. **`SKILL.md`**
   - 定義輸入 payload、修補目標、輸出欄位、行為限制與建議流程

2. **`evaluate_repair.py`**
   - 對 buggy code 與 repaired code 套用相同樣本
   - 計算通過題數、失敗題數、改善幅度與結構性限制結果

3. **`run.py`**
   - 將最終 repair contract 寫入結果檔
   - 同時保留與現有測試相容的 stdout 行為

4. **`dev_set/open_track/repair_tasks/`**
   - 提供公開 scenario，包含 buggy code、任務描述、限制與 sample inputs

### 4.4 執行流程

Open Track 單次呼叫流程如下：

1. 讀取 `task_id`、`task_description`、`buggy_code`、`constraints` 與 `sample_inputs`
2. 辨識缺陷型態，例如 off-by-one、state-machine bug、邊界條件錯誤或 recurrence 錯誤
3. 生成一版 repaired implementation，並維持原始 entry function 名稱與限制條件
4. 呼叫 `evaluate_repair.py`，對 buggy version 與 repaired version 套用相同測試
5. 若 repaired version 未改善，則重新修正；若改善成立，則輸出最終 contract
6. 由 `run.py` 寫入包含 `repair_evaluation` 的結果檔

### 4.5 評估指標

Open Track 之主要評估指標包括：

- `buggy_passed`
- `repaired_passed`
- `repair_delta`
- `improved`
- `fully_fixed`

另包含結構性指標：

- `loc`
- `loc_violation`
- `import_violations`
- `entry_function_found`
- `buggy_errors`
- `repaired_errors`
- `sample_count`
- `sample_source`

上述 metric 不可由單純敘述性輸出取巧，原因在於：

- buggy 與 repaired 版本接受相同測試集合
- evaluator 直接計算改善幅度與結構限制
- 若未真正修補程式，`repair_delta` 不會提升
- 若違反函式名稱、LoC 或 import 限制，evaluator 仍會保留負向訊號

### 4.6 Public Scenarios

目前建立三個公開 scenario：

1. `open_repair_001_binary_search`
2. `open_repair_002_parse_csv`
3. `open_repair_003_unique_paths`

這三題分別覆蓋：

- off-by-one / bounds handling bug
- state-machine / parser bug
- edge-case / recurrence bug

### 4.7 執行結果

目前 Open Track 已完成：

- skill 架構與 `SKILL.md`
- deterministic evaluator
- output wrapper
- 三個 public scenarios
- pytest
- live 單題成功

實際 live 測試 `open_repair_001` 時，成功觀察到：

- buggy passed：`4/5`
- repaired passed：`5/5`
- improved：`true`
- fully fixed：`true`

因此，可判定 Open Track 已具備結構完整性、可驗證性與本地重現能力。

---

## 5. 可重現的驗證結果

### 5.1 Repo 結構驗證

```bash
python3 verify_repo.py --github-id melanieshih
```

結果：

```text
passed: 28/28
```

### 5.2 全部測試

```bash
python -m pytest tests -q
```

結果：

```text
188 passed
```

### 5.3 Basic Track

- `text2sql` live 單題成功
- `validate_sql.py` 可直接驗證候選 SQL
- 公開 Basic dev set 經 batch 執行與 targeted rerun 後完成驗證

### 5.4 Pairwise Track

- `code-author` live 單題成功
- `bug-hunter` live 單題成功
- `code-author` dev set 經補跑後完成驗證
- `bug-hunter` 在 reference tasks `001~005` 全數成功
- `task_pair_EXAMPLE` 之失敗屬於 payload mismatch，而非 skill contract 失敗

### 5.5 Open Track

- `python -m pytest tests/test_open_code_repair.py -q` 通過
- Open Track live 單題成功
- `repair_evaluation` 可正確計算 `improved` 與 `fully_fixed`

### 5.6 代表性執行證據摘錄

**(1) Repo 規格驗證**

```text
$ python3 verify_repo.py --github-id melanieshih
=== verify_repo summary ===
  passed: 28/28
```

**(2) 全部測試**

```text
$ python -m pytest tests -q
188 passed
```

**(3) Basic Track 補跑證據**

```text
$ python3 run_dev.py --skill text2sql-melanieshih --track basic --task task_nl2sql_014
[PASS] task_nl2sql_014: result set matches gold (bag-equal)
```

**(4) Pairwise Bug Hunter live 單題**

```text
$ hermes chat --toolsets skills,terminal --yolo -Q -q '/bug-hunter-melanieshih {...}'
The result has been written to .../aiase_result.json
```

**(5) Open Track live 單題**

```text
$ hermes chat --toolsets skills,terminal --yolo -Q -q '/open-code-repair-melanieshih {...}'
Buggy passed: 4/5
Repaired passed: 5/5
Fully fixed: True
```

---

## 6. 失敗分析與外部限制

### 6.1 LiteLLM / Hosted vLLM timeout

在 Basic Track 與部分 live 測試中，曾出現：

- `HTTP 500`
- `litellm.MidStreamFallbackError`
- `Hosted_vllmException - Timeout on reading data from socket`

此類失敗在多數情況下可透過 targeted rerun 排除，顯示其主要來源為推論服務鏈不穩，而非 deterministic helper 或 contract 本身錯誤。

### 6.2 Connection error

Open Track 首次 live 測試曾出現：

```text
API call failed after 3 retries: Connection error.
```

在後續 retry 中成功完成，此現象同樣支持：live 失敗未必代表 skill 設計錯誤，而需區分為 infra-side connection instability。

### 6.3 Tool-call completion instability

在部分批次任務中，曾出現：

```text
no result file (task not produced)
```

當同題在 targeted rerun 中成功時，較合理的判斷為：

- 當次 agent 未完成最後寫檔步驟
- 或推論鏈中斷於 tool-call completion 階段

此類失敗不宜直接解讀為 deterministic correctness 錯誤。

### 6.4 Payload mismatch：Pairwise `task_pair_EXAMPLE`

`bug-hunter` 對 `task_pair_EXAMPLE` 的失敗原因，經檢查後可歸類為 payload mismatch：

- 該 example 只提供 `task_description`、`constraints`、`sample_tests`
- 但 `bug-hunter` 必須接收 `code` 才能審查

因此，此題較適合作為 `code-author` 的 student-facing minimal example，而非作為 `bug-hunter` correctness 證據。

### 6.5 `<|channel>thought` / `<channel|>` token leak

部分 Gemma 4 路徑的 live 輸出會混入：

```text
<|channel>thought
<channel|>
```

在舊版 stdout/fenced-JSON 評分路徑下，此問題會直接干擾最後輸出格式；但在新版 file-based 契約下，其影響已下降為：

- 影響 stdout 可讀性
- 不再是主要評分 gate 的阻礙

因此，本專案將其歸類為外部推論鏈限制，而非 repo-side blocker。

---

## 7. 結論與改進方向

本專案目前已完成：

- Basic Track 的 Text2SQL skill 與 deterministic validator
- Pairwise Track 的雙角色 skill 與角色宣告
- Open Track 的 code repair skill、public scenarios 與 deterministic evaluator
- repo 結構、自動檢查與本地測試

目前最具代表性的可重現結果為：

- `python3 verify_repo.py --github-id melanieshih` → `28/28 passed`
- `python -m pytest tests -q` → `188 passed`
- Basic / Pairwise / Open Track 均已具備 live 單題成功證據

後續改進方向包括：

1. 持續擴充 Open Track scenarios，增加更多 bug family 與樣本覆蓋率
2. 強化 Pairwise `code-author` 與 `bug-hunter` 在 batch 執行時的穩定度
3. 若課程推論服務鏈更穩定，可重新蒐集更完整的 batch-level log 作為補充證據
4. 若課程端 reasoning parser 問題獲得修正，可再次驗證 stdout 可讀性與 file-based 路徑的一致性

綜合 repo 結構、deterministic helper、測試結果與 live 單題驗證，本專案已具備完整提交內容與可重現的工程基礎；目前剩餘風險主要來自課程推論服務鏈的 timeout、connection instability 與 stdout token leak，而非 repo 端 deterministic 邏輯全面失效。

---

## 8. 參考資料

1. AIASE 2026 Final Project 規格頁與 starter repository 說明。
2. Hermes Agent 官方文件與 skill / toolset 使用說明。
3. LiteLLM Gateway 課程環境設定範例。
