---
name: bug-hunter-melanieshih
description: Audit a Python function against its task description, use deterministic analysis signals, and write the AIASE 2026 Pairwise Bug Hunter contract through scripts/run.py using the file-based output contract.
version: 0.2.0
metadata:
  hermes:
    tags: [code, audit, python, aiase-2026, pairwise]
    category: code
---

# Bug Hunter Skill (Pairwise Track)

## When to Use

Use this skill when the user sends a JSON payload containing:

- `task_id`
- `task_description`
- `code`

The goal is to inspect the candidate Python function, identify real bugs relative to the stated specification, and write one structured bug report through the required file-based output contract.

Trigger example:

```text
/bug-hunter-melanieshih {"task_id":"task_pair_EXAMPLE","task_description":"Implement reverse_words(s): return the words in reverse order separated by a single space. Empty string returns an empty string.","code":"def reverse_words(s):\n    return s[::-1]\n"}
```

## Objective

Produce one valid bug-hunter contract that:

- keeps `task_id` exactly equal to the input,
- sets `verdict` to either `clean` or `buggy`,
- reports only bugs that are actually supported by the code and task description,
- uses valid bug `type` and `severity` labels,
- and writes one valid structured result object through `scripts/run.py`.

## Procedure

1. **Parse the payload**
   - Read `task_id`, `task_description`, and `code`.
   - Treat the task description as the ground-truth behavioral specification.
   - Interpret line numbers as 1-indexed.

2. **Probe the candidate code deterministically**
   - Run the local analyzer:

   ```text
   python3 skills/bug-hunter-melanieshih/scripts/analyze.py '<json-payload>'
   ```

   - If the code contains many quotes or backslashes, prefer piping JSON through stdin instead of hand-escaping:

   ```text
   cat <<'EOF' | python3 skills/bug-hunter-melanieshih/scripts/analyze.py
   <json-payload>
   EOF
   ```

   - Use analyzer signals to identify:
     - crashes,
     - mismatched outputs,
     - suspicious line ranges,
     - likely edge-case failures.

3. **Decide whether each suspicious region is a real bug**
   - Report only bugs that are supported by the specification and observed behavior.
   - Avoid speculative or weakly supported findings.
   - Prefer one high-quality finding over many noisy findings.

4. **Assign labels carefully**
   - `type` must be one of:
     - `off_by_one`
     - `null_deref`
     - `type_error`
     - `logic_error`
     - `edge_case`
     - `api_misuse`
     - `inefficient`
     - `unhandled_input`
   - `severity` must be one of:
     - `critical`
     - `high`
     - `medium`
     - `low`
   - Use the smallest valid line range that contains the bug.

5. **Construct the verdict**
   - If no real bug is supported, set:
     - `verdict = "clean"`
     - `bugs = []`
   - If one or more real bugs are supported, set:
     - `verdict = "buggy"`
     - `bugs = [...]`

6. **Write the final contract through the wrapper**
   - Call:

   ```text
   python3 skills/bug-hunter-melanieshih/scripts/run.py '<json-payload>'
   ```

   - The payload should include:
     - `task_id`
     - `verdict`
     - `bugs`
     - `confidence`

7. **Use the result file as the grading artifact**
   - `scripts/run.py` must write the final result to the path from `AIASE_RESULT_PATH`; if the variable is missing, it writes to `./aiase_result.json`.
   - Do not rely on the visible conversation text as the grading artifact.
   - A short confirmation message is acceptable, but do not restate the JSON contract in the chat.

## Bug Classification Guidance

- **`off_by_one`**
  - wrong loop or index bounds
  - misses first or last element

- **`logic_error`**
  - algorithm follows the wrong semantics even though it runs
  - example: reversing a string instead of reversing the order of words

- **`edge_case`**
  - fails on empty input, singleton input, invalid dimensions, or similar corner cases

- **`type_error`**
  - runtime failure caused by incompatible value types or operations

- **`unhandled_input`**
  - input shape is valid under the spec but not handled by the implementation

- **`inefficient`**
  - algorithm is functionally correct but clearly violates an expected efficiency requirement

## Pitfalls

- Over-reporting is harmful. False positives on clean code will reduce score.
- Under-reporting is also harmful. Always returning `clean` will miss real defects.
- Wrong line numbers weaken evaluation even when the bug category is correct.
- Relying on chat formatting is fragile; the grader reads the result file, not the conversation transcript.
- Hand-escaping the final contract is risky for quote-heavy code; use `scripts/run.py`.
- Do not expose internal reasoning, chain-of-thought markers, or hidden control tokens.

## Verification

Before finalizing, verify all of the following:

- `task_id` exactly matches the input
- `verdict` is either `"buggy"` or `"clean"`
- `bugs` is an array
- `bugs == []` whenever `verdict == "clean"`
- each bug object contains:
  - `line_start`
  - `line_end`
  - `severity`
  - `type`
  - `description`
  - `suggested_fix`
- `scripts/run.py` successfully wrote the result file
- the result file is a valid JSON object

## Final Output Contract

The grading payload is the JSON object written by `scripts/run.py`.

Expected JSON fields:

- `task_id`
- `verdict`
- `bugs`
- `confidence`

Do not output plain text analysis by itself.  
Do not output raw JSON in chat as the primary grading artifact.  
Do not restate the report outside the written result object.
