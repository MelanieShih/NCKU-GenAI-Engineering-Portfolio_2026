# Pairwise Code Author Task Analysis

本文件整理 `dev_set/pairwise/reference_tasks/` 中 5 題公開 reference task，目的是在 LiteLLM / Hermes 不穩定時，仍能持續補強 `code-author` 的 deterministic 設計、edge-case 覆蓋與 unit test 策略。

---

## 1. `merge_intervals`

- `task_id`: `task_pair_001`
- `entry_function`: `merge_intervals`

### 標準解法

- 先處理空輸入：`[] -> []`
- 依 `start` 排序
- 用單次掃描合併區間
- 合併條件要用 `<=`，因為 touching intervals 也要合併

### 常見錯誤

- 忘記空輸入，直接取 `intervals[0]`
- 寫成 `<` 而不是 `<=`
- 沒先排序，導致 unsorted case 錯誤
- 直接修改原輸入列表，造成副作用或 alias 問題

### 應覆蓋的 edge cases

- 空列表
- 單一區間
- 完全重疊
- touching intervals
- unsorted intervals
- 被包含的子區間

---

## 2. `binary_search`

- `task_id`: `task_pair_002`
- `entry_function`: `binary_search`

### 標準解法

- iterative binary search
- 維護 `lo`, `hi`
- 條件使用 `while lo <= hi`
- 找不到回傳 `-1`

### 常見錯誤

- `while lo < hi` 導致漏掉最後一格
- `mid` 更新後邊界移動不正確
- 空陣列未處理
- 對 sorted/non-decreasing 的假設沒有維持一致

### 應覆蓋的 edge cases

- 空陣列
- 單一元素且命中
- 單一元素但未命中
- target 在第一格
- target 在最後一格
- target 不存在且比最小值小
- target 不存在且比最大值大

---

## 3. `parse_csv_line`

- `task_id`: `task_pair_003`
- `entry_function`: `parse_csv_line`

### 標準解法

- 使用 single-pass state machine
- 維護：
  - `result`
  - `current`
  - `in_quotes`
  - index `i`
- 當前在 quoted field 內時：
  - `""` 代表 literal `"`
  - 單一 `"` 代表關閉 quoted field
- quoted field 外遇到 `,` 才分欄

### 常見錯誤

- 只用 `split(",")`
- 每遇到 `"` 就切換 `in_quotes`，卻沒處理 `""`
- 無法解析 `a,"b,c",d`
- 空字串沒回傳 `[""]`
- 最後一欄沒有 append

### 應覆蓋的 edge cases

- 空字串
- 一般 CSV：`a,b,c`
- 空欄位：`a,,b`
- quoted field 含逗號：`a,"b,c",d`
- escaped quote：`"hello ""world"""`
- 全部都是 quoted fields
- 單一欄位

---

## 4. `unique_paths`

- `task_id`: `task_pair_004`
- `entry_function`: `unique_paths`

### 標準解法

- 對 `m <= 0` 或 `n <= 0` 直接回傳 `0`
- 對 `1 x 1` 回傳 `1`
- 使用標準 DP：
  - 第一列與第一行皆為 1
  - 其餘格子為上方與左方和

### 常見錯誤

- 忘記處理 `m <= 0` 或 `n <= 0`
- base case 寫錯
- 索引維度反了
- 沒處理 `1 x n` 或 `n x 1`

### 應覆蓋的 edge cases

- `1,1`
- `1,n`
- `m,1`
- `2,2`
- `3,3`
- `3,7`
- `0,n`
- `m,0`

---

## 5. `kth_smallest`

- `task_id`: `task_pair_005`
- `entry_function`: `kth_smallest`

### 標準解法

- 先驗證：
  - `nums` 不可空
  - `k >= 1`
  - `k <= len(nums)`
- 驗證失敗回傳 `None`
- 否則排序後回傳 `sorted(nums)[k - 1]`

### 常見錯誤

- 把 `k` 當成 0-based
- 忘記處理空陣列
- `k > len(nums)` 時丟 exception
- 沒處理 duplicates

### 應覆蓋的 edge cases

- 一般 case
- `k = 1`
- `k = len(nums)`
- 空陣列
- 單元素合法 / 非法
- duplicates
- 逆序輸入

---

## 對 `selftest.py` 的設計啟示

這五題的共同點很明確：

- 都有至少一個「空輸入或非法輸入」條件
- 都有 textbook solution
- 都能用少量 deterministic sample 擋掉常見錯誤

因此 `code-author` 的 deterministic 策略應該優先做到：

1. 檢查 entry function 名稱是否正確
2. 檢查 forbidden imports
3. 檢查 SLOC
4. 依 task description 自動派生 sample cases
5. 回傳清楚的 mismatch / runtime error 訊息

這也是目前 `skills/code-author-melanieshih/scripts/selftest.py` 的設計方向。
