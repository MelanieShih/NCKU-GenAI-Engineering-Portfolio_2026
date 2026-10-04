"""Tests for the Open Track deterministic code-repair helpers."""

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ER_PATH = REPO_ROOT / "skills" / "open-code-repair-melanieshih" / "scripts" / "evaluate_repair.py"
RUN_PATH = REPO_ROOT / "skills" / "open-code-repair-melanieshih" / "scripts" / "run.py"


def _load():
    spec = importlib.util.spec_from_file_location("open_code_repair_eval", ER_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ocr = _load()


def _parse_last_fenced_json(text: str) -> dict:
    matches = re.findall(r"```json\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    assert matches, f"no fenced json found in output: {text!r}"
    return json.loads(matches[-1])


def test_select_samples_derives_binary_search():
    samples, source = ocr.select_samples({}, "Repair binary_search(arr, target)", "binary_search")
    assert source == "derived"
    assert any(case["expected"] == 2 for case in samples)
    assert any(case["expected"] == -1 for case in samples)


def test_evaluate_payload_detects_improvement():
    payload = {
        "task_id": "open_repair_001",
        "task_description": "Repair binary_search(arr, target): return the index of target in sorted arr, or -1 if not found.",
        "buggy_code": (
            "def binary_search(arr, target):\n"
            "    left, right = 0, len(arr) - 1\n"
            "    while left < right:\n"
            "        mid = (left + right) // 2\n"
            "        if arr[mid] == target:\n"
            "            return mid\n"
            "        if arr[mid] < target:\n"
            "            left = mid + 1\n"
            "        else:\n"
            "            right = mid - 1\n"
            "    return -1\n"
        ),
        "repaired_code": (
            "def binary_search(arr, target):\n"
            "    left, right = 0, len(arr) - 1\n"
            "    while left <= right:\n"
            "        mid = (left + right) // 2\n"
            "        if arr[mid] == target:\n"
            "            return mid\n"
            "        if arr[mid] < target:\n"
            "            left = mid + 1\n"
            "        else:\n"
            "            right = mid - 1\n"
            "    return -1\n"
        ),
        "constraints": {
            "entry_function": "binary_search",
            "max_loc": 500,
            "imports_forbidden": ["os", "sys", "subprocess"],
        },
        "sample_inputs": [
            {"input": [[], 3], "expected": -1},
            {"input": [[1, 2, 3, 4, 5], 1], "expected": 0},
            {"input": [[1, 2, 3, 4, 5], 5], "expected": 4},
            {"input": [[1, 2, 3, 4, 5], 6], "expected": -1},
        ],
    }
    result = ocr.evaluate_payload(payload)
    assert result["improved"] is True
    assert result["repaired_passed"] > result["buggy_passed"]
    assert result["fully_fixed"] is True


def test_evaluate_payload_flags_missing_entry_function():
    payload = {
        "task_id": "open_repair_missing_entry",
        "task_description": "Repair unique_paths(m, n)",
        "buggy_code": "def wrong_name(m, n):\n    return 0\n",
        "repaired_code": "def wrong_name(m, n):\n    return 0\n",
        "constraints": {
            "entry_function": "unique_paths",
            "max_loc": 500,
            "imports_forbidden": [],
        },
        "sample_inputs": [
            {"input": [1, 1], "expected": 1},
        ],
    }
    result = ocr.evaluate_payload(payload)
    assert result["entry_function_found"] is False
    assert result["repaired_passed"] == 0
    assert result["repaired_failed"] == 1


def test_run_py_emits_contract_with_repair_evaluation():
    payload = {
        "task_id": "open_repair_003",
        "task_description": "Repair unique_paths(m, n): return the number of paths from top-left to bottom-right moving only right or down.",
        "buggy_code": (
            "def unique_paths(m, n):\n"
            "    if m <= 0 or n <= 0:\n"
            "        return 1\n"
            "    dp = [[0] * n for _ in range(m)]\n"
            "    for i in range(m):\n"
            "        for j in range(n):\n"
            "            if i == 0 or j == 0:\n"
            "                dp[i][j] = 1\n"
            "            else:\n"
            "                dp[i][j] = dp[i - 1][j] + dp[i][j - 1]\n"
            "    return dp[m - 1][n - 1]\n"
        ),
        "repaired_code": (
            "def unique_paths(m, n):\n"
            "    if m <= 0 or n <= 0:\n"
            "        return 0\n"
            "    dp = [1] * n\n"
            "    for _ in range(1, m):\n"
            "        for col in range(1, n):\n"
            "            dp[col] += dp[col - 1]\n"
            "    return dp[-1]\n"
        ),
        "constraints": {
            "entry_function": "unique_paths",
            "max_loc": 500,
            "imports_forbidden": ["os", "sys", "subprocess"],
        },
        "sample_inputs": [
            {"input": [1, 1], "expected": 1},
            {"input": [2, 2], "expected": 2},
            {"input": [3, 3], "expected": 6},
            {"input": [0, 5], "expected": 0},
        ],
        "repair_summary": "Fix invalid-dimension handling and use a correct dynamic-programming recurrence.",
        "confidence": 0.92,
    }
    proc = subprocess.run(
        [sys.executable, str(RUN_PATH), json.dumps(payload)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    result = _parse_last_fenced_json(proc.stdout)
    assert result["task_id"] == "open_repair_003"
    assert "repaired_code" in result
    assert result["repair_evaluation"]["fully_fixed"] is True
    assert result["repair_evaluation"]["improved"] is True
