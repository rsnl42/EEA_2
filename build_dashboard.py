#!/usr/bin/env python3
"""Build the PISA 2025 equity-gap dashboard as a static HTML page.

Reads the Chapter 4 workbook, pulls every group-gap estimate (and its S.E.)
for the nine outcomes x eight breakdowns shown on the dashboard, and injects
them into templates/equity_gaps.html. The output is one self-contained file
that can be served from GitHub Pages (or any static host).

Usage:
    python build_dashboard.py            # writes docs/equity-gaps/index.html
    python build_dashboard.py --xlsx PATH --out PATH

(Use build_site.py to build the whole site, landing page included.)
"""
import argparse
import json
import re
import sys
from pathlib import Path

import pandas as pd

from site_common import DEFAULT_XLSX, DOCS, fill, load_template, write_page

SHEET = "Digital & AI"
OECD_ROW = "OECD average"

# Source tables, in the column order used by the dashboard (must match the
# `cols` array in the template): never used AI, AI-use index, not using AI to
# summarise / research / draft / learn, tasked with assessing AI output,
# digital distraction, no device use for learning at school.
TABLES = ["55", "54", "56", "57", "58", "59", "68", "43", "26"]

# Breakdowns, in row order. Each entry: a keyword that must appear in the
# column header and the "first group - second group" pair the gap is computed
# as. The template hard-codes these group names, so the build fails loudly if
# the workbook ever changes order or orientation.
DIMENSIONS = [
    ("Gender", "Boys - Girls"),
    ("Socio-economic status", "Advantaged - Disadvantaged"),
    ("Immigrant background", "Immigrant - Non-immigrant"),
    ("Education level", "ISCED 3 - ISCED 2"),
    ("Programme orientation", "General - Vocational"),
    ("School socio-economic", "Advantaged - Disadvantaged schools"),
    ("School location", "City - Rural area"),
    ("Type of school", "Private - Public"),
]

GAP_COL = re.compile(r"(Dif\.|dif\.)$")


def load(xlsx: Path) -> pd.DataFrame:
    df = pd.read_excel(xlsx, sheet_name=SHEET, index_col=0)
    if OECD_ROW not in df.index:
        sys.exit(f"Row '{OECD_ROW}' not found in {xlsx}")
    return df


def table_columns(df: pd.DataFrame, code: str) -> list[str]:
    prefix = f"[I.B1.4.{code}]"
    cols = [c for c in df.columns if str(c).startswith(prefix)]
    if not cols:
        sys.exit(f"No columns found for table I.B1.4.{code}")
    return cols


def extract(df: pd.DataFrame):
    """Return (system names, D, O).

    D[dimension][outcome] = [[name_index, gap, se], ...] for every system with
    data; O[dimension][outcome] = [gap, se] for the OECD average.
    """
    num = df.apply(pd.to_numeric, errors="coerce")
    names = [n for n in df.index if n != OECD_ROW]
    index_of = {n: i for i, n in enumerate(names)}

    D = [[None] * len(TABLES) for _ in DIMENSIONS]
    O = [[None] * len(TABLES) for _ in DIMENSIONS]

    for j, code in enumerate(TABLES):
        cols = table_columns(df, code)
        gap_idx = [i for i, c in enumerate(cols) if GAP_COL.search(c)]
        if len(gap_idx) != len(DIMENSIONS):
            sys.exit(
                f"Table I.B1.4.{code}: expected {len(DIMENSIONS)} gap columns, "
                f"found {len(gap_idx)}"
            )
        for d, (keyword, pair) in enumerate(DIMENSIONS):
            i = gap_idx[d]
            header, next_header = cols[i], cols[i + 1] if i + 1 < len(cols) else ""
            if keyword not in header or pair not in header:
                sys.exit(
                    f"Table I.B1.4.{code}: column {header!r} does not match "
                    f"expected breakdown {keyword!r} / {pair!r}"
                )
            if "S.E." not in next_header:
                sys.exit(f"Table I.B1.4.{code}: no S.E. column after {header!r}")

            pair_df = pd.DataFrame({"g": num[header], "s": num[next_header]}).dropna()
            oecd = pair_df.loc[OECD_ROW]
            rest = pair_df.drop(OECD_ROW)
            rest = rest[rest["s"] > 0]  # need a usable standard error
            # keep 4 decimals: index-point S.E.s are ~0.01-0.05, so 2 dp would distort z-scores
            D[d][j] = [
                [index_of[n], round(float(r.g), 4), round(float(r.s), 4)]
                for n, r in rest.iterrows()
            ]
            O[d][j] = [round(float(oecd.g), 4), round(float(oecd.s), 4)]
    return names, D, O


def dump(obj) -> str:
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=False)


def build(xlsx: Path, out: Path) -> str:
    """Build the equity-gaps page from the workbook and write it to `out`."""
    names, D, O = extract(load(xlsx))
    html = fill(load_template("equity_gaps.html"),
                {"NAMES": dump(names), "D": dump(D), "O": dump(O)})
    write_page(out, html)
    n_points = sum(len(D[d][j]) for d in range(len(DIMENSIONS)) for j in range(len(TABLES)))
    return (f"{len(DIMENSIONS) * len(TABLES)} cells, {n_points} system-level gaps, "
            f"{len(names)} systems, {len(html) / 1024:.0f} KB")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--xlsx", type=Path, default=DEFAULT_XLSX)
    ap.add_argument("--out", type=Path, default=DOCS / "equity-gaps" / "index.html")
    args = ap.parse_args()
    print(f"Wrote {args.out}: {build(args.xlsx, args.out)}")


if __name__ == "__main__":
    main()
