> 說明：本 Open Track skill 的設計已對齊課程評分 gate，包含 skill 可呼叫、結果檔契約合法、metric 可由 deterministic script 計算、安全限制可檢查，以及執行時間受 runtime budget 約束。

## 1. Skill 簡介

本 Open Track skill 針對小型 Python 演算法函式之修補任務進行設計，輸入為一段帶有缺陷的 Python 函式、任務描述、結構限制與測試樣本；輸出為一段修正版程式碼，並以本地 deterministic evaluator 證明修補後版本相較於原始 buggy version 在相同測試集合上具有可量化的改善。

## 2. Skill 名稱與目錄

- Skill 名稱：`open-code-repair-melanieshih`
- 目錄路徑：`skills/open-code-repair-melanieshih/`

## 3. 呼叫方式

評分環境以 slash command 呼叫：

```text
/open-code-repair-melanieshih
```

正式呼叫範例：

```bash
hermes chat --toolsets skills,terminal --yolo -Q -q '/open-code-repair-melanieshih {"task_id":"open_repair_001","task_description":"Repair binary_search(arr, target): return the index of target in sorted arr, or -1 if not found.","buggy_code":"def binary_search(arr, target):\n    left, right = 0, len(arr) - 1\n    while left < right:\n        mid = (left + right) // 2\n        if arr[mid] == target:\n            return mid\n        if arr[mid] < target:\n            left = mid + 1\n        else:\n            right = mid - 1\n    return -1\n","constraints":{"entry_function":"binary_search","max_loc":500,"imports_forbidden":["os","sys","subprocess"]},"sample_inputs":[{"input":[[],3],"expected":-1},{"input":[[1,2,3,4,5],1],"expected":0},{"input":[[1,2,3,4,5],5],"expected":4},{"input":[[1,2,3,4,5],6],"expected":-1}]}'
```

輸入 payload 範例：

```json
{
  "task_id": "open_repair_001",
  "task_description": "Repair binary_search(arr, target): return the index of target in sorted arr, or -1 if not found.",
  "buggy_code": "def binary_search(arr, target):\n    left, right = 0, len(arr) - 1\n    while left < right:\n        mid = (left + right) // 2\n        if arr[mid] == target:\n            return mid\n        if arr[mid] < target:\n            left = mid + 1\n        else:\n            right = mid - 1\n    return -1\n",
  "constraints": {
    "entry_function": "binary_search",
    "max_loc": 500,
    "imports_forbidden": ["os", "sys", "subprocess"]
  },
  "sample_inputs": [
    {"input": [[], 3], "expected": -1},
    {"input": [[1, 2, 3, 4, 5], 1], "expected": 0},
    {"input": [[1, 2, 3, 4, 5], 5], "expected": 4},
    {"input": [[1, 2, 3, 4, 5], 6], "expected": -1}
  ]
}
```

結果檔中的預期 JSON 範例：

```json
{
  "task_id": "open_repair_001",
  "repaired_code": "def binary_search(arr, target):\n    left, right = 0, len(arr) - 1\n    while left <= right:\n        mid = (left + right) // 2\n        if arr[mid] == target:\n            return mid\n        if arr[mid] < target:\n            left = mid + 1\n        else:\n            right = mid - 1\n    return -1\n",
  "repair_summary": "Fix the off-by-one search loop and preserve the required function contract.",
  "confidence": 0.93,
  "repair_evaluation": {
    "buggy_passed": 4,
    "buggy_failed": 1,
    "repaired_passed": 5,
    "repaired_failed": 0,
    "total_tests": 5,
    "improved": true,
    "fully_fixed": true,
    "repair_delta": 1,
    "loc": 11,
    "loc_violation": false,
    "import_violations": [],
    "sample_source": "provided",
    "sample_count": 5,
    "entry_function_found": true,
    "buggy_errors": [],
    "repaired_errors": []
  }
}
```

評分主體為結果檔，而非 chat stdout。`scripts/run.py` 會將最終結果寫入 `AIASE_RESULT_PATH`；若該環境變數不存在，則 fallback 至 `./aiase_result.json`。

## 4. 自定 Verifiable Scenario

本 skill 的 scenario 為 **algorithmic code repair**，目前公開 scenarios 包含：

- `dev_set/open_track/repair_tasks/open_repair_001_binary_search.json`
- `dev_set/open_track/repair_tasks/open_repair_002_parse_csv.json`
- `dev_set/open_track/repair_tasks/open_repair_003_unique_paths.json`

三組 scenario 分別覆蓋：

1. **Off-by-one / bounds handling bug**
   - `binary_search`
   - 驗證單元素、首尾元素與找不到目標值等情況

2. **State-machine / parser bug**
   - `parse_csv_line`
   - 驗證 quoted field、escaped quote、空欄位與空字串輸入

3. **Edge-case / recurrence bug**
   - `unique_paths`
   - 驗證非法尺寸、單列單行與標準 DP recurrence

### Metric 定義

主要評估指標如下：

- `repair_delta = repaired_passed - buggy_passed`
- `improved = (repair_delta > 0)`
- `fully_fixed = (repaired_failed == 0 and repaired_passed == total_tests)`
- `pass_rate = repaired_passed / total_tests`

結構性輔助指標如下：

- `entry_function_found`
- `loc_violation`
- `import_violations`

### Pass Condition

有效修補需同時滿足：

- `entry_function_found == true`
- `loc_violation == false`
- `import_violations == []`
- `improved == true`

完整成功修補則再額外要求：

- `fully_fixed == true`

### 不可作弊性說明

本 metric 不依賴模型自述，而由 `skills/open-code-repair-melanieshih/scripts/evaluate_repair.py` 直接計算，其不可作弊性主要來自：

1. buggy code 與 repaired code 必須接受同一組測試集合
2. 若未真正改善功能，`repair_delta` 與 `improved` 不會成立
3. 若違反函式名稱、LoC 或 forbidden import 限制，evaluator 仍會保留負向訊號
4. `repair_summary` 與說明文字不參與得分核心，主要證據為 `repair_evaluation`

### Staff perturbation robustness

預期 staff-side perturbations 可能包括：

- 更換 task_id
- 調整 sample case 排列順序
- 擴充 edge-case 測試
- 更換同類型 bug family 下的 buggy implementation
- 對 `task_description` 進行等義改寫

由於 evaluator 直接比較 buggy 與 repaired 版本在相同測試集上的表現，因此此 skill 主要追求的是 **bug family level robustness**，而非僅對單一固定樣本過度適配。

## 5. 預期失敗模式

1. **Semantic repair failure**
   - 產出的修補版本雖有改動，但未真正改善核心行為
   - 對應訊號：`improved == false` 或 `repair_delta <= 0`

2. **Contract / execution failure**
   - 輸出未維持正確 entry function，或違反 import / LoC 限制
   - 對應訊號：`entry_function_found == false`、`import_violations != []`、`loc_violation == true`

3. **Parser-heavy instability**
   - 如 `parse_csv_line` 類型問題，quoted field 與 escaped quote 易造成局部修補不完整
   - 對應訊號：`fully_fixed == false`，但 `improved == true`

## 6. 互動對象

本 skill 主要與下列對象互動：

1. **Hermes terminal tool**
   - 用於呼叫 `skills/open-code-repair-melanieshih/scripts/run.py`

2. **deterministic evaluator**
   - `skills/open-code-repair-melanieshih/scripts/evaluate_repair.py`
   - 負責計算 `buggy_passed`、`repaired_passed`、`repair_delta`、`improved` 與其他結構性訊號

3. **Python coding task family**
   - 題型與 Pairwise `code-author` 所處理之小型 Python 演算法函式相同
   - 因此本 skill 與前兩個 Track 之間具有工作流上的延續性

本 skill 未依賴外部 reference skill 或 subagent。

## 7. Token Budget 估算

單一 scenario 的 token 消耗主要來自：

- `task_description`
- `buggy_code`
- `repaired_code`
- `repair_summary`
- JSON contract

由於 deterministic 驗證由本地 script 執行，模型 token 主要集中於理解 buggy code 與產生 repaired code。

| Scenario | 預估 input tokens | 預估 output tokens | 預估 total |
|---|---:|---:|---:|
| `open_repair_001_binary_search` | 1,200 | 700 | 1,900 |
| `open_repair_002_parse_csv` | 1,800 | 1,000 | 2,800 |
| `open_repair_003_unique_paths` | 1,300 | 800 | 2,100 |

以上皆遠低於 50k tokens / scenario。
