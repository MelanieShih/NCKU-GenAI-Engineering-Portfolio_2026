---
name: text2sql-melanieshih
description: Convert a natural-language question plus SQLite schema into a verified read-only SQL query for AIASE 2026 Basic Track, then write the result through scripts/run.py using the file-based output contract.
version: 0.1.0
metadata:
  hermes:
    tags: [sql, text2sql, sqlite, aiase-2026]
    category: data
---

# Text2SQL Skill

## Purpose

This skill solves the AIASE 2026 Basic Track Text2SQL task.

Given a natural-language question and a SQLite schema, produce exactly one correct read-only SQLite query, validate it with the bundled validator, then emit the final contract with the bundled output wrapper.

This skill should use the helper scripts under `scripts/`:

- `scripts/validate_sql.py`
- `scripts/run.py`

The final result must be machine-readable by the grader.

## When to Use

Use this skill when the user invokes `/text2sql-melanieshih` with a JSON payload containing:

- `task_id`
- `question`
- `db_schema`
- optional `dialect`

Example trigger:

```text
/text2sql-melanieshih {"task_id":"task_nl2sql_001","question":"List the names of all students.","db_schema":"CREATE TABLE Students (sid INTEGER PRIMARY KEY, name TEXT);","dialect":"sqlite"}
```

## Inputs

The input is a JSON object with these fields:

- `task_id`: the task identifier that must be copied exactly into the final answer
- `question`: the natural-language request to answer
- `db_schema`: SQLite DDL text describing the available schema
- `dialect`: expected SQL dialect, usually `sqlite`

## Objective

Produce exactly one correct read-only SQLite query that answers the question using only the provided schema, validate that query, and write the final result to the grader result file.

## SQL Requirements

The generated SQL must satisfy all of the following:

1. It must be exactly one SQLite `SELECT` statement.
2. It must be read-only.
3. It must only use tables and columns that appear in `db_schema`.
4. It must preserve schema names exactly as provided.
5. It must be valid SQLite syntax.
6. It should end with a semicolon.
7. If joins can duplicate requested entities, use `DISTINCT` when appropriate.
8. If the question requires filtering, grouping, ordering, aggregation, or limits, express that explicitly in SQL.

## Forbidden SQL Behavior

The SQL must not:

- modify the database
- create, alter, or drop objects
- contain multiple statements
- rely on tables or columns not present in `db_schema`

Do not generate write or DDL commands such as insert, update, delete, create, drop, alter, pragma, vacuum, attach, detach, or replace.

## Procedure

Follow this process:

1. Parse the input JSON payload.
2. Copy `task_id` exactly from the input.
3. Read the `question` carefully.
4. Inspect `db_schema` and identify the relevant tables, columns, joins, filters, grouping, ordering, aggregation, deduplication, or limits.
5. Draft one SQLite `SELECT` query that answers the question.
6. Validate the drafted SQL by invoking:

   ```text
   python scripts/validate_sql.py '{"schema_ddl":"<db_schema>","sql":"<candidate_sql>"}'
   ```

7. If validation fails, revise the SQL and validate again.
8. Once validation succeeds, invoke:

   ```text
   python scripts/run.py '{"task_id":"<task_id>","sql":"<final_sql>","rationale":"<brief rationale>","confidence":<confidence>}'
   ```

9. `scripts/run.py` must write the final result to the path from `AIASE_RESULT_PATH`; if that variable is missing, it writes to `./aiase_result.json`.
10. After invoking `scripts/run.py`, do not rely on the chat response to carry the grading payload. A short confirmation message is acceptable, but do not restate the final JSON contract in the conversation.

## Verification

Before producing the final answer, verify all of the following:

- `scripts/validate_sql.py` accepted the final SQL
- `scripts/run.py` successfully wrote the result file
- the result file is a valid JSON object
- `task_id` exactly matches the input
- `sql` is a single read-only SQLite `SELECT` statement
- `confidence` is a number between `0.0` and `1.0`
- the JSON top-level value is an object
- `rationale` is brief and relevant

## Final Output Contract

The grading payload is the JSON object written by `scripts/run.py` to the result file.
Do not rely on chat formatting, Markdown fences, or extra prose as the grading mechanism.

The JSON object written to the result file must contain exactly these fields:

- `task_id`
- `sql`
- `rationale`
- `confidence`

## Required Output Shape

Return this exact structural pattern:

```json
{
  "task_id": "task_nl2sql_001",
  "sql": "SELECT name FROM Students;",
  "rationale": "This query returns the requested student names.",
  "confidence": 0.95
}
```

## Field Semantics

- `task_id`: copy the input task identifier exactly
- `sql`: the final SQLite query as a string
- `rationale`: one brief sentence explaining why the SQL answers the question
- `confidence`: a numeric estimate between `0.0` and `1.0`

## Output Discipline

Do not expose internal reasoning.  
Do not expose hidden control tokens.  
Do not expose intermediate drafts.  
Do not output plain SQL alone as the only final artifact.  
Do not manually recreate the final contract when `scripts/run.py` can write it.  
Do not rely on the conversation message itself as the grading artifact.

If you are uncertain, still return the best valid answer in the required result-object format and let `scripts/run.py` write it.

## Example

Input:

```text
/text2sql-melanieshih {"task_id":"task_nl2sql_001","question":"List the names of all students.","db_schema":"CREATE TABLE Students (sid INTEGER PRIMARY KEY, name TEXT);","dialect":"sqlite"}
```

Candidate SQL:

```text
SELECT name FROM Students;
```

Validation command:

```text
python scripts/validate_sql.py '{"schema_ddl":"CREATE TABLE Students (sid INTEGER PRIMARY KEY, name TEXT);","sql":"SELECT name FROM Students;"}'
```

Final wrapper command:

```text
python scripts/run.py '{"task_id":"task_nl2sql_001","sql":"SELECT name FROM Students;","rationale":"The question asks for student names, so the query selects the name column from Students.","confidence":0.95}'
```

Correct final result payload:

```json
{
  "task_id": "task_nl2sql_001",
  "sql": "SELECT name FROM Students;",
  "rationale": "The question asks for student names, so the query selects the name column from Students.",
  "confidence": 0.95
}
```

## Failure Handling

If the question is somewhat ambiguous, choose the most reasonable interpretation supported by the provided schema and still write a valid result object.

If multiple tables seem plausible, prefer the interpretation that most directly answers the wording of the question.

If confidence is lower, reflect that in the `confidence` field rather than breaking the output format.

## Final Reminder

The grader reads the result file written by `scripts/run.py`.  
Always ensure that file contains the final valid answer object.
