#!/usr/bin/env python3
"""One-off helper: extract "Table I.1 Snapshot of performance" from the PISA 2025 Volume I PDF
into data/pisa2025_table_I1.csv (mean science / reading / maths / computational problem-solving
scores, 2022-25 changes, top and low performer shares), so the analyses can use performance as
external context without re-parsing the PDF.

Only `science` (mean science score) is used by the dashboards, as context joined on system name.
The two share columns are kept as published. Their column headings in Table I.1 are "Share of top
performers (Level 5 or 6) in science, reading or mathematics" and "Share of low performers (Below Level 2)
in science, reading and mathematics".

Verified (3 Oct 2026): run end to end on the PISA 2025 Results (Volume I) PDF (377 pages; the table is on
PDF page 30). It wrote 92 rows with no unparsed row-like lines, the OECD average once, and every workbook
system matched by exact name; the CSV is identical, cell for cell (828 cells), to the table as published on
oecd.org. The table of contents also contains the title, which the parser skips (it takes the occurrence
followed by data).

Needs `pdftotext` (poppler). Usage:
    python analysis/extract_table_I1.py path/to/PISA_25.pdf [--workbook data/digital_devices_AI_chapter4.xlsx]

Safeguards (the parse takes the last 9 fields of each line as values and the rest as the name):
  * lines that look like data rows but fail the numeric test are REPORTED, never silently dropped
  * the OECD average row must be present exactly once
  * with --workbook (default: the repo workbook if present), every system in the workbook must
    be found by exact name, otherwise the script exits non-zero: an unmatched name would turn
    that system's science score into a silent NaN downstream
  * systems whose science mean is far from what reading and maths predict are printed so the
    row can be checked against the PDF by eye
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "pisa2025_table_I1.csv"
DEFAULT_XLSX = ROOT / "data" / "digital_devices_AI_chapter4.xlsx"
COLS = ["science", "reading", "maths", "cps", "d_science", "d_reading", "d_maths", "top_share", "low_share"]
NUM = re.compile(r"^(?:-?\d+(?:\.\d+)?|m)$")


def parse_table(txt: str):
    """Return (DataFrame of rows, list of skipped lines that looked like data rows)."""
    # the title also appears in the table of contents; use the occurrence followed by data
    starts = [m.start() for m in re.finditer(r"Table I\.1\. Snapshot of performance", txt)]
    start = next(i for i in starts if "OECD average" in txt[i:i + 2500])
    end = txt.index("Caution is required", start)
    rows, skipped = [], []
    for line in txt[start:end].splitlines():
        tok = line.split()
        if len(tok) < 10:
            continue
        ok = [bool(NUM.match(t)) for t in tok[-9:]]
        if all(ok):
            rows.append([" ".join(tok[:-9])] + [None if t == "m" else float(t) for t in tok[-9:]])
        elif sum(ok) >= 6:  # mostly numeric but not all: a row with a symbol such as c, w or x
            skipped.append(line.strip())
    return pd.DataFrame(rows, columns=["system"] + COLS), skipped


def check(df: pd.DataFrame, skipped: list, workbook: Path | None) -> list:
    problems = []
    if skipped:
        problems.append(f"{len(skipped)} row-like lines were not parsed (non-numeric field): {skipped[:3]}")
    if (df.system == "OECD average").sum() != 1:
        problems.append("OECD average row not found exactly once")
    if df.system.duplicated().any():
        problems.append(f"duplicate names: {df.system[df.system.duplicated()].tolist()}")
    if workbook is not None and workbook.exists():
        names = set(pd.read_excel(workbook, sheet_name="Digital & AI", index_col=0).index)
        miss = sorted(names - set(df.system))
        if miss:
            problems.append(f"workbook systems not found by exact name (science would be NaN): {miss}")
    return problems


def outliers(df: pd.DataFrame) -> pd.DataFrame:
    d = df[df.system != "OECD average"].dropna(subset=["science", "reading", "maths"])
    A = np.column_stack([np.ones(len(d)), d.reading, d.maths])
    res = d.science - A @ np.linalg.lstsq(A, d.science, rcond=None)[0]
    return d.assign(residual=res.round(1))[res.abs() > 3 * res.std()][["system", "science", "reading", "maths", "residual"]]


def main(pdf: str, workbook: Path | None) -> None:
    txt = subprocess.run(["pdftotext", "-layout", pdf, "-"], capture_output=True, text=True, check=True).stdout
    df, skipped = parse_table(txt)
    problems = check(df, skipped, workbook)
    for p in problems:
        print("PROBLEM:", p)
    if problems:
        sys.exit("Not writing the CSV: fix the problems above (or check the PDF rows) first.")
    OUT.parent.mkdir(exist_ok=True)
    df.to_csv(OUT, index=False)
    print(f"Wrote {OUT} ({len(df)} rows)")
    o = outliers(df)
    if len(o):
        print("Check these against the PDF (science far from what reading and maths predict):")
        print(o.to_string(index=False))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("pdf")
    ap.add_argument("--workbook", type=Path, default=DEFAULT_XLSX)
    a = ap.parse_args()
    main(a.pdf, a.workbook)
