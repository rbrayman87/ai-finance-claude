"""Smoke tests for scripts/generate_finance_pdf.py.

Each test runs the script as a CLI (the way the finance-report-pdf skill
calls it) and checks that a valid nine-page PDF comes out.
"""

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "generate_finance_pdf.py"
SAMPLE_JSON = Path(__file__).resolve().parent / "fixtures" / "sample_plan.json"

# Cover, score dashboard, cash flow, debt, investments, retirement,
# protection, action items, 90-day plan.
EXPECTED_PAGES = 9


def run_script(*args, cwd):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=120,
    )


def assert_valid_pdf(path):
    assert path.exists(), f"{path} was not created"
    content = path.read_bytes()
    assert content.startswith(b"%PDF-"), "output is not a PDF"
    assert content.rstrip().endswith(b"%%EOF"), "PDF is truncated"
    pages = len(re.findall(rb"/Type\s*/Page(?!s)", content))
    assert pages == EXPECTED_PAGES, f"expected {EXPECTED_PAGES} pages, got {pages}"


def test_demo_mode_writes_sample_pdf(tmp_path):
    result = run_script("--demo", cwd=tmp_path)

    assert result.returncode == 0, result.stderr
    assert "Generated: FINANCE-PLAN-sample.pdf" in result.stdout
    assert_valid_pdf(tmp_path / "FINANCE-PLAN-sample.pdf")


def test_demo_mode_respects_output_path(tmp_path):
    output = tmp_path / "nested" / "dir" / "demo.pdf"
    result = run_script("--demo", "--output", str(output), cwd=tmp_path)

    assert result.returncode == 0, result.stderr
    assert_valid_pdf(output)


def test_json_input_generates_pdf(tmp_path):
    output = tmp_path / "plan.pdf"
    result = run_script("--data", str(SAMPLE_JSON), "--output", str(output), cwd=tmp_path)

    assert result.returncode == 0, result.stderr
    assert_valid_pdf(output)
    # The client name ends up in the PDF metadata title.
    assert b"Alex Morgan" in output.read_bytes()


def test_missing_arguments_is_an_error(tmp_path):
    result = run_script(cwd=tmp_path)

    assert result.returncode != 0
    assert "--demo" in result.stderr


def test_missing_data_file_is_an_error(tmp_path):
    result = run_script("--data", str(tmp_path / "nope.json"), cwd=tmp_path)

    assert result.returncode == 1
    assert "ERROR reading --data file" in result.stderr


def test_invalid_json_is_an_error(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    result = run_script("--data", str(bad), cwd=tmp_path)

    assert result.returncode == 1
    assert "ERROR reading --data file" in result.stderr
