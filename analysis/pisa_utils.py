"""Shared helpers for the PISA 2025 chapter-4 analysis scripts.

The workbook has one row per education system (plus 'OECD average') and one
column per statistic, named "[I.B1.4.<table>] <label>". Every estimate column
is immediately followed by its standard-error column, which these helpers rely
on (and check).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

SHEET = "Digital & AI"
OECD_ROW = "OECD average"
REPO = Path(__file__).resolve().parents[1]
DEFAULT_XLSX = REPO / "data" / "digital_devices_AI_chapter4.xlsx"
Z95 = 1.96


class Workbook:
    def __init__(self, xlsx: Path | str | None = None):
        path = Path(xlsx) if xlsx else DEFAULT_XLSX
        if not path.exists():
            sys.exit(f"Workbook not found: {path}")
        self.raw = pd.read_excel(path, sheet_name=SHEET, index_col=0)
        if OECD_ROW not in self.raw.index:
            sys.exit(f"Row '{OECD_ROW}' not found in {path}")
        # 'm' (missing), 'c' (suppressed) etc. become NaN
        self.num = self.raw.apply(pd.to_numeric, errors="coerce")
        self.columns = list(self.raw.columns)

    @property
    def systems(self) -> list[str]:
        return [n for n in self.raw.index if n != OECD_ROW]

    def table_columns(self, table: str) -> list[str]:
        prefix = f"[I.B1.4.{table}]"
        cols = [c for c in self.columns if str(c).startswith(prefix)]
        if not cols:
            sys.exit(f"No columns found for table I.B1.4.{table}")
        return cols

    def pair(self, table: str, *keywords: str, endswith: str | None = None):
        """Return (estimate, s.e.) Series for the single column of `table`
        whose label contains every keyword (and optionally ends with
        `endswith`). Fails loudly if zero or several columns match."""
        cols = self.table_columns(table)
        hits = [
            i for i, c in enumerate(cols)
            if "S.E." not in c
            and all(k in c for k in keywords)
            and (endswith is None or c.rstrip().endswith(endswith))
        ]
        if len(hits) != 1:
            sys.exit(f"Table {table}, keywords {keywords}, endswith={endswith!r}: "
                     f"{len(hits)} matches (expected 1)")
        i = hits[0]
        if i + 1 >= len(cols) or "S.E." not in cols[i + 1]:
            sys.exit(f"Table {table}: no S.E. column after {cols[i]!r}")
        return self.num[cols[i]], self.num[cols[i + 1]]

    def est(self, table: str, *keywords: str, endswith: str | None = None) -> pd.Series:
        return self.pair(table, *keywords, endswith=endswith)[0]


def stars(z: float) -> str:
    return "*" if abs(z) > Z95 else ""


def out_dir(path: Path | str | None = None) -> Path:
    d = Path(path) if path else REPO / "outputs"
    d.mkdir(parents=True, exist_ok=True)
    return d
