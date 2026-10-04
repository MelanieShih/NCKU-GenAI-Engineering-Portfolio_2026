"""Tests for code-author deterministic selftest helpers."""

import importlib.util
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ST_PATH = REPO_ROOT / "skills" / "code-author-melanieshih" / "scripts" / "selftest.py"


def _load():
    spec = importlib.util.spec_from_file_location("code_author_selftest", ST_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


st = _load()


def test_has_entry_function_true():
    code = "def merge_intervals(intervals):\n    return intervals\n"
    assert st.has_entry_function(code, "merge_intervals") is True


def test_has_entry_function_false():
    code = "def something_else(intervals):\n    return intervals\n"
    assert st.has_entry_function(code, "merge_intervals") is False


def test_select_samples_prefers_explicit_samples():
    payload = {
        "sample_inputs": [{"input": [1], "expected": 1}],
    }
    samples, source = st.select_samples(payload, "irrelevant", "f")
    assert source == "provided"
    assert samples == [{"input": [1], "expected": 1}]


def test_select_samples_derives_merge_intervals():
    samples, source = st.select_samples({}, "Implement merge_intervals(intervals)", "merge_intervals")
    assert source == "derived"
    assert any(case["expected"] == [] for case in samples)
    assert any(case["expected"] == [[1, 4]] for case in samples)


def test_select_samples_derives_parse_csv_line():
    samples, source = st.select_samples({}, "Implement parse_csv_line(line) for CSV with quoted fields", "parse_csv_line")
    assert source == "derived"
    assert any(case["expected"] == [""] for case in samples)
    assert any(case["expected"] == ["a", "", "b"] for case in samples)


def test_run_sample_success():
    code = "def binary_search(arr, target):\n    return arr.index(target) if target in arr else -1\n"
    ok, err = st.run_sample(code, "binary_search", {"input": [[1, 2, 3], 2], "expected": 1}, 1.0)
    assert ok is True
    assert err == ""


def test_run_sample_runtime_error():
    code = "def f(x):\n    return 1 / x\n"
    ok, err = st.run_sample(code, "f", {"input": [0], "expected": 0}, 1.0)
    assert ok is False
    assert "runtime error" in err


def test_run_sample_mismatch():
    code = "def kth_smallest(nums, k):\n    return None\n"
    ok, err = st.run_sample(code, "kth_smallest", {"input": [[3, 1, 2], 1], "expected": 1}, 1.0)
    assert ok is False
    assert "mismatch" in err


def test_load_payload_from_argv():
    payload, state, source = st._load_payload(["selftest.py", '{"code":"def f():\\n    return 1"}'])
    assert state == "ok"
    assert source == "argv"
    assert payload["code"].startswith("def f")
