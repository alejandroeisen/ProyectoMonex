"""
excel_push.py — runs on the Work PC.

Reads live data from a running Excel instance via xlwings and POSTs it
to the Mini PC's FastAPI /internal/push endpoint.

Modes:
    Default (production): connects to the running Excel process via xlwings.
    --file path/to/file.xlsx: reads from a static file via openpyxl (dev/testing).

Usage:
    python excel_push.py                        # xlwings, run once
    python excel_push.py --loop                 # xlwings, run continuously
    python excel_push.py --file data.xlsx       # openpyxl, run once
    python excel_push.py --file data.xlsx --loop  # openpyxl, run continuously

Config (via .env in this directory):
    MINIPC_API_URL      = http://<minipc-tailscale-ip>:8000
    SYNC_API_KEY        = your-secret-key
    EXCEL_WORKBOOK_NAME = MyWorkbook.xlsx   (optional, matches partial name)
    PUSH_INTERVAL_SECONDS = 5
"""

import os
import sys
import json
import time
import logging
import argparse
import secrets
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from collections import deque
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

# ── Config ────────────────────────────────────────────────────────────────────

MINIPC_API_URL       = os.getenv("MINIPC_API_URL", "http://localhost:8000")
SYNC_API_KEY         = os.getenv("SYNC_API_KEY", "")
EXCEL_WORKBOOK_NAME  = os.getenv("EXCEL_WORKBOOK_NAME", "")   # partial match, optional
PUSH_INTERVAL        = int(os.getenv("PUSH_INTERVAL_SECONDS", "5"))
EXCLUDED_SHEETS      = {s.strip() for s in os.getenv("EXCLUDED_SHEETS", "").split(",") if s.strip()}
MAX_RETRY_QUEUE      = 5   # max failed payloads to hold in memory

# ── Logging ───────────────────────────────────────────────────────────────────

log_path = os.path.join(os.path.dirname(__file__), "excel_push.log")
logger = logging.getLogger("excel_push")
logger.setLevel(logging.DEBUG)

file_handler = RotatingFileHandler(log_path, maxBytes=2_000_000, backupCount=3)
file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-8s %(message)s"))
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-8s %(message)s"))
stream_handler.stream = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

# ── Retry queue ───────────────────────────────────────────────────────────────

retry_queue: deque = deque(maxlen=MAX_RETRY_QUEUE)


# ── Excel reading ─────────────────────────────────────────────────────────────

def serialize_value(val):
    """Convert cell values to JSON-serializable types."""
    if val is None:
        return None
    if hasattr(val, "isoformat"):   # datetime / date
        return val.isoformat()
    if isinstance(val, float) and val != val:  # NaN
        return None
    return val


def read_via_xlwings() -> list[dict] | None:
    """
    Connect to the running Excel process via xlwings and read all sheets.
    Returns a list of sheet dicts, or None if Excel is unavailable.
    """
    try:
        import xlwings as xw
    except ImportError:
        logger.error("xlwings is not installed. Run: pip install xlwings")
        return None

    try:
        app = xw.apps.active
        if app is None:
            raise RuntimeError("No active Excel app found.")
    except Exception:
        logger.warning("Excel is not running — skipping this cycle.")
        return None

    # Find the target workbook
    try:
        if EXCEL_WORKBOOK_NAME:
            wb = next(
                (b for b in app.books if EXCEL_WORKBOOK_NAME.lower() in b.name.lower()),
                None
            )
            if wb is None:
                logger.warning(
                    f"Workbook matching '{EXCEL_WORKBOOK_NAME}' not found. "
                    f"Open workbooks: {[b.name for b in app.books]}"
                )
                return None
        else:
            if not app.books:
                logger.warning("No workbooks open in Excel.")
                return None
            wb = app.books[0]
    except Exception as e:
        logger.error(f"Error accessing workbooks: {e}")
        return None

    sheets = []
    try:
        for sheet in wb.sheets:
            sheet_name = sheet.name

            if sheet_name in EXCLUDED_SHEETS:
                logger.debug(f"Skipping '{sheet_name}': excluded.")
                continue

            raw = sheet.used_range.value  # list of lists, live in-memory values

            # Normalize: xlwings returns a single value, a flat list (one row),
            # or a list of lists depending on the range size
            if raw is None:
                logger.debug(f"Skipping '{sheet_name}': empty.")
                continue
            if not isinstance(raw, list):
                raw = [[raw]]
            elif raw and not isinstance(raw[0], list):
                raw = [raw]

            if not any(v is not None for v in raw[0]):
                logger.debug(f"Skipping '{sheet_name}': no headers.")
                continue

            headers = [str(h).strip() for h in raw[0] if h is not None]
            data_rows = [r for r in raw[1:] if any(v is not None for v in r)]

            rows_serialized = [
                {headers[j]: serialize_value(row[j] if j < len(row) else None)
                 for j in range(len(headers))}
                for row in data_rows
            ]

            sheets.append({
                "name": sheet_name,
                "columns": headers,
                "rows": rows_serialized,
            })
            logger.debug(f"  Read '{sheet_name}': {len(data_rows)} rows, {len(headers)} cols")

    except Exception as e:
        logger.error(f"Error reading workbook '{wb.name}': {e}")
        return None

    return sheets


def read_via_openpyxl(file_path: str) -> list[dict] | None:
    """
    Read from a static .xlsx file. Used in dev/testing mode.
    """
    try:
        import openpyxl
        wb = openpyxl.load_workbook(file_path, data_only=True)
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        return None
    except Exception as e:
        logger.error(f"Could not open file '{file_path}': {e}")
        return None

    sheets = []
    for sheet_name in wb.sheetnames:
        if sheet_name in EXCLUDED_SHEETS:
            logger.debug(f"Skipping '{sheet_name}': excluded.")
            continue

        ws = wb[sheet_name]
        all_rows = list(ws.iter_rows(values_only=True))

        if not all_rows or not any(v is not None for v in all_rows[0]):
            logger.debug(f"Skipping '{sheet_name}': empty or no headers.")
            continue

        headers = [str(h).strip() for h in all_rows[0] if h is not None]
        data_rows = [r for r in all_rows[1:] if any(v is not None for v in r)]

        rows_serialized = [
            {headers[j]: serialize_value(row[j] if j < len(row) else None)
             for j in range(len(headers))}
            for row in data_rows
        ]

        sheets.append({
            "name": sheet_name,
            "columns": headers,
            "rows": rows_serialized,
        })
        logger.debug(f"  Read '{sheet_name}': {len(data_rows)} rows, {len(headers)} cols")

    return sheets


# ── HTTP push ─────────────────────────────────────────────────────────────────

def push_to_api(sheets: list[dict]) -> bool:
    """
    POST sheet data to the Mini PC's FastAPI endpoint.
    Returns True on success.
    """
    if not SYNC_API_KEY:
        logger.error("SYNC_API_KEY is not set in .env — cannot push.")
        return False

    url = f"{MINIPC_API_URL.rstrip('/')}/internal/push"
    payload = {"sheets": sheets, "pushed_at": datetime.now(timezone.utc).isoformat()}
    headers = {"X-API-Key": SYNC_API_KEY, "Content-Type": "application/json"}

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        if resp.status_code == 200:
            result = resp.json()
            logger.info(
                f"Push OK — {result.get('sheets_synced', '?')} sheets, "
                f"{result.get('total_rows', '?')} rows"
            )
            return True
        elif resp.status_code == 401:
            logger.error("Push rejected: invalid API key.")
            return False
        else:
            logger.warning(f"Push failed: HTTP {resp.status_code} — {resp.text[:200]}")
            return False
    except requests.exceptions.ConnectionError:
        logger.warning(f"Mini PC unreachable at {MINIPC_API_URL} — queuing for retry.")
        return False
    except requests.exceptions.Timeout:
        logger.warning("Push timed out — queuing for retry.")
        return False
    except Exception as e:
        logger.error(f"Unexpected push error: {e}")
        return False


def flush_retry_queue():
    """Try to send any previously failed payloads."""
    if not retry_queue:
        return
    logger.info(f"Retrying {len(retry_queue)} queued payload(s)...")
    still_failing = []
    while retry_queue:
        queued = retry_queue.popleft()
        if not push_to_api(queued):
            still_failing.append(queued)
    for item in still_failing:
        retry_queue.append(item)


# ── Main cycle ────────────────────────────────────────────────────────────────

def read_with_timeout(file_path: str | None, timeout: int = 15) -> list[dict] | None:
    """Run the Excel read in a thread with a timeout. Returns None if Excel is busy."""
    fn = (lambda: read_via_openpyxl(file_path)) if file_path else read_via_xlwings
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(fn)
        try:
            return future.result(timeout=timeout)
        except FuturesTimeout:
            logger.warning("Excel read timed out (Excel may be busy or showing a dialog) — skipping cycle.")
            return None


def run_cycle(file_path: str | None):
    """Read Excel and push. Queues on failure."""
    logger.info("--- Sync cycle starting ---")

    t0 = time.perf_counter()
    sheets = read_with_timeout(file_path)
    read_ms = (time.perf_counter() - t0) * 1000
    logger.info(f"Excel read: {read_ms:.0f}ms")

    if sheets is None:
        logger.warning("No data read — skipping push.")
        return

    if not sheets:
        logger.warning("All sheets were empty — skipping push.")
        return

    flush_retry_queue()

    t1 = time.perf_counter()
    success = push_to_api(sheets)
    push_ms = (time.perf_counter() - t1) * 1000
    logger.info(f"HTTP push: {push_ms:.0f}ms | total cycle: {(read_ms + push_ms):.0f}ms")

    if not success:
        retry_queue.append(sheets)
        logger.warning(f"Queued for retry. Queue size: {len(retry_queue)}")


def run_loop(file_path: str | None, interval: int):
    mode = f"file: {file_path}" if file_path else "xlwings (live Excel)"
    logger.info(f"Starting push loop — interval: {interval}s — mode: {mode}")
    while True:
        run_cycle(file_path)
        logger.info(f"Sleeping {interval}s...\n")
        time.sleep(interval)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Excel → Mini PC push script")
    parser.add_argument("--file", metavar="PATH", help="Use openpyxl on a file instead of win32com")
    parser.add_argument("--loop", action="store_true", help="Run continuously")
    args = parser.parse_args()

    if args.loop:
        run_loop(args.file, PUSH_INTERVAL)
    else:
        run_cycle(args.file)
