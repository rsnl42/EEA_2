#!/usr/bin/env python3
"""Build the leisure activity profiles page (analysis #5) from analysis/05_leisure_profiles.py.

Usage:
    python build_leisure_profiles.py                # writes docs/leisure-profiles/index.html
    python build_leisure_profiles.py --xlsx PATH --out PATH
"""
import argparse
import importlib.util
import json
import math
import sys
from html import escape as html_escape
from pathlib import Path

import pandas as pd

from site_common import DEFAULT_XLSX, DOCS, ROOT, fill, load_template, write_page

ANALYSIS = ROOT / "analysis"


def load_analysis():
    sys.path.insert(0, str(ANALYSIS))
    spec = importlib.util.spec_from_file_location("leisure", ANALYSIS / "05_leisure_profiles.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def clean(v, nd=4):  # keep 4 decimals: the page rounds once, at display time
    return None if v is None or (isinstance(v, float) and math.isnan(v)) else round(float(v), nd)


def build(xlsx=DEFAULT_XLSX, out=DOCS / "leisure-profiles" / "index.html") -> str:
    la = load_analysis()
    wb = la.Workbook(xlsx)
    t1 = ROOT / "data" / "pisa2025_table_I1.csv"
    X = la.extract(wb, 8.0, pd.read_csv(t1, index_col=0) if t1.exists() else None)
    keys = [c for c in X.columns if c != "science"]
    S = X.drop(la.OECD_ROW)
    have = S.index[S["social_wd_hrs"].notna()]
    rows = [{"n": n, **{k: clean(S.loc[n, k]) for k in keys}} for n in have]
    oecd = {k: clean(X.loc[la.OECD_ROW, k]) for k in keys}
    acts = [{"key": a, "label": lab} for a, (_, lab) in la.ACT.items()]

    note = (f" Only {len(have)} of {len(S)} systems have data in these tables: the others have none at all, "
            "on both weekdays and weekends, rather than a few suppressed cells.")
    if "science" in S.columns:
        miss = S.index.difference(have)
        note += (f" The {len(have)} covered systems average {S.science[have].mean():.0f} in science against "
                 f"{S.science[miss].mean():.0f} for the rest, so patterns here describe higher-scoring systems.")
    stats = {"n": len(have), "total": len(S)}
    html = fill(load_template("leisure_profiles.html"), {
        "ROWS": json.dumps(rows, separators=(",", ":"), ensure_ascii=False),
        "OECD": json.dumps(oecd, separators=(",", ":")),
        "ACTS": json.dumps(acts, ensure_ascii=False), "STATS": json.dumps(stats),
        "COVERAGE": html_escape(note),
    })
    write_page(Path(out), html)
    return f"{len(rows)} systems, {len(html) / 1024:.0f} KB"


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--xlsx", type=Path, default=DEFAULT_XLSX)
    ap.add_argument("--out", type=Path, default=DOCS / "leisure-profiles" / "index.html")
    a = ap.parse_args()
    print(f"Wrote {a.out}: {build(a.xlsx, a.out)}")
