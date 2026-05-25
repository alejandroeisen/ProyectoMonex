"""
test_parser.py — standalone tests for parse_tables_from_rows()

No backend, no Excel, no .env needed. Just runs the parser against
raw Python lists and checks the output.

Usage:
    python sync/test_parser.py          # from repo root
    python test_parser.py               # from sync/ directory

To add a new edge case: append a dict to CASES at the bottom of this file.
Each case has:
    name        : str   — label shown in output
    sheet       : str   — sheet name passed to parser
    rows        : list  — raw rows (each row is a list of cell values, None = empty cell)
    expect      : list  — expected output, one dict per table:
                          {"name": str, "columns": list, "row_count": int}
                          Use "row_count": None to skip row-count check.
    expect_warn : bool  — True if the case should trigger a WARNING log (optional)
"""

import sys
import os
import logging
import io

# Force UTF-8 output on Windows
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ── Import parser from excel_push.py ─────────────────────────────────────────
# Works whether you run from repo root or from sync/
_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _here)

from excel_push import parse_tables_from_rows   # noqa: E402

# ── Suppress logger output during tests (we'll capture warnings ourselves) ───
_captured_logs: list[str] = []

class _CapturingHandler(logging.Handler):
    def emit(self, record):
        # Store level name so we can check for WARNING/ERROR later
        _captured_logs.append(f"{record.levelname}: {record.getMessage()}")

_cap = _CapturingHandler()
_cap.setLevel(logging.WARNING)
logging.getLogger("excel_push").addHandler(_cap)
logging.getLogger("excel_push").setLevel(logging.DEBUG)
# Remove the default file + stream handlers so they don't spam the terminal
for h in logging.getLogger("excel_push").handlers[:]:
    if not isinstance(h, _CapturingHandler):
        logging.getLogger("excel_push").removeHandler(h)


# ── Test runner ───────────────────────────────────────────────────────────────

PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"
WARN_OK = "\033[33mWARN-OK\033[0m"

def run_tests(cases):
    passed = 0
    failed = 0

    for case in cases:
        _captured_logs.clear()

        name      = case["name"]
        sheet     = case.get("sheet", "TestSheet")
        rows      = case["rows"]
        expected  = case["expect"]
        want_warn = case.get("expect_warn", False)

        result = parse_tables_from_rows(rows, sheet)

        errors = []

        # Check table count
        if len(result) != len(expected):
            errors.append(
                f"  expected {len(expected)} table(s), got {len(result)}: "
                f"{[t['name'] for t in result]}"
            )
        else:
            for i, (got, exp) in enumerate(zip(result, expected)):
                # Check name
                if got["name"] != exp["name"]:
                    errors.append(f"  table[{i}] name: expected '{exp['name']}', got '{got['name']}'")
                # Check columns
                if "columns" in exp and got["columns"] != exp["columns"]:
                    errors.append(f"  table[{i}] columns: expected {exp['columns']}, got {got['columns']}")
                # Check row count
                if exp.get("row_count") is not None and len(got["rows"]) != exp["row_count"]:
                    errors.append(f"  table[{i}] row_count: expected {exp['row_count']}, got {len(got['rows'])}")
                # Check exact rows if provided
                if "rows" in exp and got["rows"] != exp["rows"]:
                    errors.append(f"  table[{i}] rows mismatch:\n    expected: {exp['rows']}\n    got:      {got['rows']}")

        # Check warning expectation
        had_warn = any("WARNING" in l for l in _captured_logs)
        if want_warn and not had_warn:
            errors.append("  expected a WARNING log but none was emitted")
        if not want_warn and had_warn:
            errors.append(f"  unexpected WARNING: {[l for l in _captured_logs if 'WARNING' in l]}")

        if errors:
            print(f"[{FAIL}] {name}")
            for e in errors:
                print(e)
            failed += 1
        else:
            tag = f"[{WARN_OK}]" if want_warn else f"[{PASS}]"
            print(f"{tag} {name}")
            passed += 1

    print()
    print(f"Results: {passed} passed, {failed} failed out of {passed + failed} tests.")
    return failed


# ── Test cases ────────────────────────────────────────────────────────────────
# Add your new edge cases at the bottom of this list.

CASES = [

    # ── Baseline: no ## markers (backward compat) ─────────────────────────────
    {
        "name": "No markers — whole sheet as one table",
        "sheet": "Info",
        "rows": [
            ["Campo", "Valor"],
            ["Trader", "Juan"],
            ["Desk", "Derivados"],
        ],
        "expect": [
            {"name": "Info", "columns": ["Campo", "Valor"], "row_count": 2}
        ],
    },

    # ── Single ## table ────────────────────────────────────────────────────────
    {
        "name": "Single ## table",
        "rows": [
            ["##Posiciones", None],
            ["Instrumento", "Nominal"],
            ["BONO_MX", 1_000_000],
            ["CETE", 500_000],
        ],
        "expect": [
            {"name": "Posiciones", "columns": ["Instrumento", "Nominal"], "row_count": 2}
        ],
    },

    # ── Two ## tables, clean separation ───────────────────────────────────────
    {
        "name": "Two ## tables — clean separation",
        "rows": [
            ["##Divisas", None],
            ["Par", "Spot"],
            ["USD/MXN", 17.05],
            ["##Bonos", None],
            ["Emisor", "YTM"],
            ["Mexico", 9.12],
        ],
        "expect": [
            {"name": "Divisas", "columns": ["Par", "Spot"], "row_count": 1},
            {"name": "Bonos",   "columns": ["Emisor", "YTM"], "row_count": 1},
        ],
    },

    # ── Whitespace around ## title ─────────────────────────────────────────────
    {
        "name": "Whitespace around ## title stripped",
        "rows": [
            ["  ##  Monedas-PUT  ", None],
            ["Strike", "Delta"],
            [18.5, -0.45],
        ],
        "expect": [
            {"name": "Monedas-PUT", "columns": ["Strike", "Delta"], "row_count": 1}
        ],
    },

    # ── Blank rows mid-table ignored ───────────────────────────────────────────
    {
        "name": "Blank rows mid-table ignored",
        "rows": [
            ["##Tabla", None],
            ["Col1", "Col2"],
            ["A", 1],
            [None, None],
            ["B", 2],
            [None, None],
            ["C", 3],
        ],
        "expect": [
            {"name": "Tabla", "columns": ["Col1", "Col2"], "row_count": 3}
        ],
    },

    # ── Subtotal-style row (one cell, no ##) is data, not a title ─────────────
    {
        "name": "Single-value row without ## is treated as data",
        "rows": [
            ["##Posiciones", None],
            ["Instrumento", "Nominal"],
            ["BONO_MX", 1_000_000],
            ["Subtotal", None],
            ["CETE", 500_000],
        ],
        "expect": [
            {"name": "Posiciones", "columns": ["Instrumento", "Nominal"], "row_count": 3}
        ],
    },

    # ── ## title with no header row: skipped with WARNING ─────────────────────
    {
        "name": "## title with no header → skipped + WARNING",
        "rows": [
            ["##TablaFantasma", None],
            ["##TablaReal", None],
            ["Col1", "Col2"],
            ["A", 1],
        ],
        "expect": [
            {"name": "TablaReal", "columns": ["Col1", "Col2"], "row_count": 1}
        ],
        "expect_warn": True,
    },

    # ── Table with headers but zero data rows ──────────────────────────────────
    {
        "name": "## table with headers but zero data rows",
        "rows": [
            ["##VaciaTabla", None],
            ["Col1", "Col2"],
        ],
        "expect": [
            {"name": "VaciaTabla", "columns": ["Col1", "Col2"], "row_count": 0}
        ],
    },

    # ── Two ## tables with NO blank rows between them ──────────────────────────
    {
        "name": "Two ## tables with no blank rows between",
        "rows": [
            ["##TablaA", None],
            ["X", "Y"],
            [1, 2],
            ["##TablaB", None],
            ["P", "Q"],
            [3, 4],
        ],
        "expect": [
            {"name": "TablaA", "columns": ["X", "Y"], "row_count": 1},
            {"name": "TablaB", "columns": ["P", "Q"], "row_count": 1},
        ],
    },

    # ── Entirely empty sheet ───────────────────────────────────────────────────
    {
        "name": "Entirely empty sheet → 0 tables",
        "rows": [
            [None, None],
            [None, None],
        ],
        "expect": [],
    },

    # ── Sheet with only blank rows and no ## ───────────────────────────────────
    {
        "name": "No ## and all rows blank → 0 tables",
        "rows": [[None], [None, None]],
        "expect": [],
    },

    # ── ## marker at the very last row (no header, no data) ───────────────────
    {
        "name": "## marker at last row — no header, no data → skipped + WARNING",
        "rows": [
            ["##TablaA", None],
            ["X", "Y"],
            [1, 2],
            ["##Orphan", None],
        ],
        "expect": [
            {"name": "TablaA", "columns": ["X", "Y"], "row_count": 1},
        ],
        "expect_warn": True,
    },

    # ── Exact row values check ─────────────────────────────────────────────────
    {
        "name": "Row values serialized correctly",
        "rows": [
            ["##Check", None],
            ["A", "B"],
            ["hello", 42],
            [None, 3.14],
        ],
        "expect": [
            {
                "name": "Check",
                "columns": ["A", "B"],
                "rows": [
                    {"A": "hello", "B": 42},
                    {"A": None,    "B": 3.14},
                ],
            }
        ],
    },

    # ══════════════════════════════════════════════════════════════════════════
    # # (single hash) stop-row tests
    # ══════════════════════════════════════════════════════════════════════════

    # ── # before any ## (sheet-level title) is skipped ────────────────────────
    {
        "name": "# before first ## is skipped, table still parsed",
        "rows": [
            ["#MONEDAS", None],
            [None, None],
            ["##Realizadas", None],
            ["Fecha", "Monto"],
            ["12-Dec", 500],
            ["15-Dec", 500],
        ],
        "expect": [
            {"name": "Realizadas", "columns": ["Fecha", "Monto"], "row_count": 2}
        ],
    },

    # ── # after table flushes it, trailing junk discarded ─────────────────────
    {
        "name": "# after table flushes it and discards trailing junk",
        "rows": [
            ["##Realizadas", None],
            ["Fecha", "Monto"],
            ["12-Dec", 500],
            ["15-Dec", 500],
            ["#", None],
            [None, 28223],
            ["SAXO", "-"],
            ["SCHWAB", "-"],
        ],
        "expect": [
            {"name": "Realizadas", "columns": ["Fecha", "Monto"], "row_count": 2}
        ],
    },

    # ── Full sheet: #Title + ##T1 + junk (no stop) + ##T2 ────────────────────
    {
        "name": "Full sheet: #Title, ##T1, junk stays in table, ##T2",
        "rows": [
            ["#MONEDAS", None],
            [None, None],
            ["##Realizadas", None],
            ["Fecha", "Monto"],
            ["12-Dec", 500],
            ["15-Dec", 500],
            [None, 28223],
            ["SAXO", "-"],
            ["##Trading", None],
            ["Fecha", "Contraparte", "Monto"],
            ["16-Mar", "BANCO DE TALCA", 1000],
            ["16-Mar", "BANCO DE TALCA", 500],
        ],
        "expect": [
            {"name": "Realizadas", "columns": ["Fecha", "Monto"],                "row_count": 4},
            {"name": "Trading",    "columns": ["Fecha", "Contraparte", "Monto"], "row_count": 2},
        ],
    },

    # ── Full sheet: #Title + ##T1 + # stop cuts junk + ##T2 ──────────────────
    {
        "name": "Full sheet: #Title, ##T1, # stop cuts junk, ##T2",
        "rows": [
            ["#MONEDAS", None],
            [None, None],
            ["##Realizadas", None],
            ["Fecha", "Monto"],
            ["12-Dec", 500],
            ["15-Dec", 500],
            ["#", None],
            [None, 28223],
            ["SAXO", "-"],
            ["##Trading", None],
            ["Fecha", "Contraparte", "Monto"],
            ["16-Mar", "BANCO DE TALCA", 1000],
        ],
        "expect": [
            {"name": "Realizadas", "columns": ["Fecha", "Monto"],                "row_count": 2},
            {"name": "Trading",    "columns": ["Fecha", "Contraparte", "Monto"], "row_count": 1},
        ],
    },

    # ── # with whitespace still acts as a stop ────────────────────────────────
    {
        "name": "# with surrounding whitespace still acts as stop",
        "rows": [
            ["##TablaA", None],
            ["X", "Y"],
            [1, 2],
            ["  #  FIN  ", None],
            [99, 99],
            ["##TablaB", None],
            ["P", "Q"],
            [3, 4],
        ],
        "expect": [
            {"name": "TablaA", "columns": ["X", "Y"], "row_count": 1},
            {"name": "TablaB", "columns": ["P", "Q"], "row_count": 1},
        ],
    },

    # ── # in a no-## sheet has no effect (backward compat) ────────────────────
    {
        "name": "# in a no-## sheet is treated as data (no multi-table mode)",
        "sheet": "Info",
        "rows": [
            ["Campo", "Valor"],
            ["Trader", "Juan"],
            ["#nota", None],
            ["Desk", "Derivados"],
        ],
        "expect": [
            {"name": "Info", "columns": ["Campo", "Valor"], "row_count": 3}
        ],
    },

    # ── # discards ALL rows below it until next ##, not just itself ─────────────
    {
        "name": "# discards ALL rows below until next ## (many junk rows)",
        "rows": [
            ["##TablaA", None],
            ["Col1", "Col2"],
            ["good1", 1],
            ["good2", 2],
            ["#", None],            # stop — everything below is dead until ##
            ["junk1", "x"],
            ["junk2", "y"],
            [None, 999],
            ["looks like a header", "also looks like one"],  # NOT a header — still dead
            ["junk3", "z"],
            ["##TablaB", None],     # only ## can revive the parser
            ["P", "Q"],
            [3, 4],
        ],
        "expect": [
            {"name": "TablaA", "columns": ["Col1", "Col2"], "row_count": 2},
            {"name": "TablaB", "columns": ["P", "Q"],       "row_count": 1},
        ],
    },

    # ── Numeric value in header row is NOT treated as a column name ───────────
    {
        "name": "Numeric cell in header row is ignored (stray formula, not a column)",
        "rows": [
            ["##Sudafrica", None],
            # 'Settlement' is the last real header; None and 0 follow in hidden cols
            ["FECHA", "ticker", "Precio Cierre", "MTM", "Settlement", None, 0],
            [None, "USDZAR", 16.4753, 0, None, None, 0],
            [None, "USDZAR", 16.4753, 0, None, None, 0],
        ],
        "expect": [
            {
                "name": "Sudafrica",
                "columns": ["FECHA", "ticker", "Precio Cierre", "MTM", "Settlement"],
                "row_count": 2,
            }
        ],
    },

    # ══════════════════════════════════════════════════════════════════════════
    # YOUR NEW EDGE CASES — add below this line
    # Each entry follows the same format as above.
    # ══════════════════════════════════════════════════════════════════════════

]


if __name__ == "__main__":
    print(f"Running {len(CASES)} parser tests...\n")
    failed = run_tests(CASES)
    sys.exit(1 if failed else 0)
