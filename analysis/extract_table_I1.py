#!/usr/bin/env python3
"""One-off helper: extract "Table I.1 Snapshot of performance" from the PISA 2025 Volume I PDF
into data/pisa2025_table_I1.csv (mean science / reading / maths / computational problem-solving
scores, 2022-25 changes, top and low performer shares), so the analyses can use performance as
external context without re-parsing the PDF.

Needs `pdftotext` (poppler). Usage:
    python analysis/extract_table_I1.py path/to/PISA_25.pdf
"""
import re
import subprocess
import sys
from pathlib import Path

import pandas as pd

OUT = Path(__file__).resolve().parents[1] / "data" / "pisa2025_table_I1.csv"
COLS = ["science", "reading", "maths", "cps", "d_science", "d_reading", "d_maths", "top_share", "low_share"]
NUM = re.compile(r"^(?:-?\d+(?:\.\d+)?|m)$")


def main(pdf: str) -> None:
    txt = subprocess.run(["pdftotext", "-layout", pdf, "-"], capture_output=True, text=True, check=True).stdout
    # the title also appears in the table of contents; use the occurrence followed by data
    starts = [m.start() for m in re.finditer(r"Table I\.1\. Snapshot of performance", txt)]
    start = next(i for i in starts if "OECD average" in txt[i:i + 2500])
    end = txt.index("Caution is required", start)
    rows = []
    for line in txt[start:end].splitlines():
        tok = line.split()
        if len(tok) < 10 or not all(NUM.match(t) for t in tok[-9:]):
            continue
        name = " ".join(tok[:-9])
        rows.append([name] + [None if t == "m" else float(t) for t in tok[-9:]])
    df = pd.DataFrame(rows, columns=["system"] + COLS)
    OUT.parent.mkdir(exist_ok=True)
    df.to_csv(OUT, index=False)
    print(f"Wrote {OUT} ({len(df)} rows)")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
