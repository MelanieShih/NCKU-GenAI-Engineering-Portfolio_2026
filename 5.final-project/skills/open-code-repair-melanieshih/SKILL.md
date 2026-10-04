---
name: open-code-repair-melanieshih
description: Repair a buggy Python function, verify that the repaired version passes more deterministic tests than the original, and write a file-based repair contract for the AIASE 2026 Open Track.
version: 0.1.0
metadata:
  hermes:
    tags: [code, repair, python, aiase-2026, open-track]
    category: code
---

# Open Code Repair Skill

## When to Use

Use this skill when the user provides a JSON payload containing:

- `task_id`
- `task_description`
- `buggy_code`
- `constraints`
- optional `sample_inputs`

The goal is to transform the buggy implementation into a repaired implementation that:

- preserves the required entry function name,
- stays within `constraints.max_loc`,
- avoids forbidden imports,
- passes more deterministic tests than the original buggy version,
- and is written to the required file-based output contract.

Trigger example:

```text
/open-code-repair-melanieshih {"task_id":"open_repair_001","task_description":"Repair binary_search(arr, target): return the index of target in sorted arr, or -1 if not found.","buggy_code":"def binary_search(arr, target):\n    left, right = 0, len(arr) - 1\n    while left < right:\n        mid = (left + right) // 2\n        if arr[mid] == target:\n            return mid\n        if arr[mid] < target:\n            left = mid + 1\n        else:\n            right = mid - 1\n    return -1\n","constraints":{"entry_function":"binary_search","max_loc":500,"imports_forbidden":["os","sys","subprocess"]}}
```

## Procedure

1. **Parse the payload**
   - Read `task_id`, `task_description`, `buggy_code`, and `constraints`.
   - Keep the exact function name from `constraints.entry_function`.
   - If `sample_inputs` are present, treat them as the highest-priority verification set.

2. **Understand the bug before editing**
   - Infer expected behavior from the task description.
   - Identify the smallest likely defect: off-by-one, missing edge case, bad state transition, invalid bounds handling, or wrong return behavior.
   - Prefer a minimal repair over a full rewrite unless the original implementation is fundamentally broken.

3. **Draft the repaired implementation**
   - Produce one repaired function.
   - Keep it short, deterministic, and side-effect free.
   - Avoid file I/O, networking, subprocesses, randomization, threads, or dynamic imports.
   - Do not change the public contract of the function.

### Fast Repair Patterns

When the task clearly matches one of these common bug families, apply the corresponding direct repair pattern:

- **binary_search**
  - Use `while left <= right`.
  - Return `-1` if the target is missing.
  - Update bounds carefully to avoid off-by-one failures.

- **merge_intervals**
  - Sort by interval start.
  - Merge touching intervals as overlapping.
  - Return `[]` on empty input.

- **parse_csv_line**
  - Use a single-pass state machine.
  - Treat commas inside quotes as literal content.
  - Treat `""` inside quotes as a literal `"`.
  - Return `[""]` on empty input.

- **unique_paths**
  - Guard invalid dimensions with `0`.
  - Use a standard DP table or 1-D DP compression.

- **kth_smallest**
  - Validate `k` bounds.
  - Return `None` when invalid.
  - Otherwise return the `(k - 1)` indexed value after sorting.

4. **Verify with the local repair harness**
   - Prefer one terminal call total.
   - Call:

   ```
   python3 skills/open-code-repair-melanieshih/scripts/run.py '<json-payload>'
   ```

   - For quote-heavy code, prefer piping JSON through stdin.
   - The payload passed to `run.py` should include:
     - `task_id`
     - `task_description`
     - `buggy_code`
     - `repaired_code`
     - `constraints`
     - optional `sample_inputs`
     - `repair_summary`
     - `confidence`

5. **Repair once more only if needed**
   - Inspect `repair_evaluation`.
   - If `improved` is false, or `entry_function_found` is false, or `import_violations` is non-empty, repair the code and run the harness once more.
   - Stop after at most 2 verification runs.
   - Prefer targeted fixes instead of a full rewrite.

6. **Write the final contract**
   - The grading payload must be written by `scripts/run.py` to the path from `AIASE_RESULT_PATH`.
   - Do not rely on the visible conversation output as the grading artifact.
   - Do not append a restated JSON contract after the script succeeds.

## Pitfalls

- Returning the original buggy code will usually fail the `improved` check.
- Renaming the entry function is an automatic contract failure.
- Forbidden imports still count as a failure even when the logic is correct.
- Long rewrites create extra risk and can violate the line budget.
- Quote-heavy functions such as CSV parsing are error-prone if you hand-escape JSON manually.
- Relying on chat formatting is fragile; the grader reads the result file written by `scripts/run.py`.

## Verification

The final output object written by `scripts/run.py` must contain:

- `task_id` — exactly equal to the input `task_id`
- `repaired_code` — valid Python source defining `constraints.entry_function`
- `repair_summary` — short explanation of what was fixed
- `confidence` — number in `[0.0, 1.0]`
- `repair_evaluation` — deterministic evaluation object containing at least:
  - `buggy_passed`
  - `repaired_passed`
  - `total_tests`
  - `improved`
  - `fully_fixed`
  - `loc`
  - `loc_violation`
  - `import_violations`

The `repair_evaluation` score must come from `scripts/run.py`, not from free-form prose or chat formatting.
