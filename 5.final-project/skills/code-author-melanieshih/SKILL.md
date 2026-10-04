---
name: code-author-melanieshih
description: Implement a Python function from a natural-language task description, run deterministic self-checks, and emit the AIASE 2026 Pairwise Code Author contract.
version: 0.2.0
metadata:
  hermes:
    tags: [code, python, aiase-2026, pairwise]
    category: code
---

# Code Author Skill (Pairwise Track)

## When to Use

Use this skill when the user sends a JSON payload containing:

- `task_id`
- `task_description`
- `constraints`

The goal is to produce **one valid Python implementation** that:

- defines exactly the function named by `constraints.entry_function`,
- stays within `constraints.max_loc`,
- avoids any import in `constraints.imports_forbidden`,
- handles common edge cases,
- and is written to the required file-based output contract.

Trigger example:

```text
/code-author-melanieshih {"task_id":"task_042","task_description":"Implement merge_intervals(intervals): merge overlapping intervals, empty input returns [].","constraints":{"entry_function":"merge_intervals","max_loc":500,"imports_forbidden":["os","sys","subprocess"]}}
```

## Procedure

1. **Parse the payload carefully**
   - Read `task_description`.
   - Read `constraints.entry_function`.
   - Read `constraints.max_loc`.
   - Read `constraints.imports_forbidden`.
   - Do not rename the required function.

2. **Extract the behavioral requirements**
   - Identify input shape and return type.
   - Identify the most likely edge cases from the description.
   - Prefer a short, direct, idiomatic solution over a clever one.

3. **Draft the candidate function**
   - Write exactly one implementation for `constraints.entry_function`.
   - Keep it compact and readable.
   - Avoid unnecessary helpers, classes, side effects, file I/O, networking, subprocesses, threads, or dynamic imports.
   - Prefer built-in Python features and simple control flow.
   - If the task matches a standard pattern, implement the standard pattern immediately instead of exploring alternatives.

### Fast Paths for Common Pairwise Tasks

When the task clearly matches one of the following, use the corresponding textbook solution directly and move on:

- **merge_intervals(intervals)**
  - If empty, return `[]`.
  - Sort intervals by start.
  - Scan once, merging when `cur_start <= last_end`.
  - Touching intervals must merge.

- **binary_search(arr, target)**
  - Use iterative binary search.
  - Return `-1` for empty input or missing target.
  - Keep the implementation `O(log n)`.

- **parse_csv_line(line)**
  - Use a single-pass state machine.
  - Maintain:
    - current field buffer,
    - result list,
    - `in_quotes` flag,
    - index pointer.
  - Rules:
    - comma outside quotes ends a field,
    - comma inside quotes is literal,
    - `""` inside quotes becomes one literal `"`,
    - empty string returns `[""]`.
  - Do not use regex-based guessing.
  - Because the generated code will contain many quote characters, be extra careful not to hand-write the final JSON contract manually.

- **unique_paths(m, n)**
  - Return `0` if `m <= 0` or `n <= 0`.
  - Return `1` for a 1x1 grid.
  - Use a standard DP solution.

- **kth_smallest(nums, k)**
  - Validate bounds first.
  - If invalid, return `None`.
  - Otherwise sort and return the `(k-1)` indexed item.

4. **Use a single terminal call to finalize**
   - Prefer **one** terminal tool call total.
   - Call `run.py` directly and let it compute:
     - `loc`
     - `self_test_results`
     - edge-case checks derived from the task description
   - For ordinary tasks, you may call:
   - `python3 skills/code-author-melanieshih/scripts/run.py '<json-payload>'`
   - For quote-heavy code (especially `parse_csv_line`), prefer piping JSON through stdin with a heredoc:
   - `cat <<'EOF' | python3 skills/code-author-melanieshih/scripts/run.py`
   - `<json-payload>`
   - `EOF`
   - The payload should include:
     - `task_id`
     - `task_description`
     - `constraints`
     - `code`
     - `rationale`
     - `confidence`
   - Do not manually construct `self_test_results` unless you truly need a second pass.

5. **Repair only when needed**
   - Inspect the `self_test_results` returned by `run.py`.
   - If `failed > 0`, fix the implementation and call `run.py` one more time.
   - If `loc_violation` is true, simplify the code.
   - If `import_violations` is non-empty, remove those imports.
   - Stop after at most **2 total terminal runs**.
   - Prefer targeted fixes instead of rewriting everything.
   - If the first draft already matches a known fast path, make only the smallest correction needed.

6. **Write the final contract**
   - The grading payload must be written by `run.py` to the path from `AIASE_RESULT_PATH`.
   - If the code contains many quotes or backslashes (for example `parse_csv_line`), never manually escape the final JSON yourself. Let `run.py` serialize it.
   - Keep `rationale` to 1–2 short sentences.
   - After `run.py` succeeds, the conversation does not need to restate the JSON contract.

## Pitfalls

- **Empty input handling** is the most common failure. If the description mentions empty input explicitly, implement it explicitly.
- **Off-by-one** errors are common in binary search, interval merging, indexing, and loops.
- **Forbidden imports** will be flagged by the harness. Do not import `os`, `sys`, `subprocess`, or any forbidden module.
- **LoC inflation** hurts maintainability and can violate `max_loc`. Keep the solution lean.
- **Wrong function name** is an automatic failure even if the logic is otherwise correct.
- **Relying on chat formatting** is fragile. The grading artifact is the result file written by `run.py`, not the visible conversation text.
- **Overthinking** wastes time. Prefer a short textbook solution plus one self-test over a long planning loop.
- **Pattern drift** wastes time. For a recognized standard task, do not compare many algorithms—use the standard one immediately.
- **Manual JSON escaping** is risky on quote-heavy tasks. Never type the final contract by hand when `code` contains many `"` or `\\`; always let `run.py` write the result object.

## Verification

The final output object written by `run.py` must contain:

- `task_id` — must exactly equal the input `task_id`
- `code` — valid Python source defining `constraints.entry_function`
- `loc` — measured source lines of code
- `self_test_results` — object containing at least `passed` and `failed`
- `rationale` — short explanation of the implementation strategy
- `confidence` — number in `[0.0, 1.0]`

Do not output raw Python by itself as the only final artifact. Always write the final contract via `scripts/run.py`.
