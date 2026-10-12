#!/usr/bin/env python3
"""Build the "Which infrastructure divides actually exist?" page (analysis #2).

Numbers come straight from analysis/02_infrastructure_divides.py's functions, so the
page and the script's CSV/console output always agree.

Usage:
    python build_infrastructure_divides.py           # writes docs/infrastructure-divides/index.html
    python build_infrastructure_divides.py --xlsx PATH --out PATH
"""
import argparse
import importlib.util
import json
import math
import sys
from pathlib import Path

from site_common import DEFAULT_XLSX, DOCS, ROOT, fill, load_template, write_page

ANALYSIS = ROOT / "analysis"


def load_analysis():
    sys.path.insert(0, str(ANALYSIS))
    spec = importlib.util.spec_from_file_location("infrastructure_divides", ANALYSIS / "02_infrastructure_divides.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def isna(v) -> bool:
    return v is None or (isinstance(v, float) and math.isnan(v))


def build(xlsx: Path, out: Path) -> str:
    idv = load_analysis()
    from pisa_utils import OECD_ROW, Workbook

    wb = Workbook(xlsx)
    long_df, summary = idv.extract(wb)
    scorecard = idv.build_scorecard(long_df)

    dump = lambda o: json.dumps(o, separators=(",", ":"), ensure_ascii=False)  # noqa: E731

    summary_rows = [
        {"table_label": r.table_label, "dimension": r.dimension,
         "oecd_gap": round(float(r.oecd_gap), 3),
         "oecd_favorability_gap": round(float(r.oecd_favorability_gap), 3),
         "oecd_se": round(float(r.oecd_se), 3),
         "oecd_z": round(float(r.oecd_z), 2), "n_systems": int(r.n_systems),
         "n_sig_expected": int(r.n_sig_expected), "n_sig_flipped": int(r.n_sig_flipped),
         "n_not_sig": int(r.n_not_sig)}
        for r in summary.itertuples()
    ]

    score = {}
    dim_cols = [c for c in scorecard.columns if ":" in c]
    for name, row in scorecard.iterrows():
        entry = {"n_expected": int(row.n_expected), "n_flipped": int(row.n_flipped),
                  "n_flat": int(row.n_flat), "n_missing": int(row.n_missing),
                  "n_tested": int(row.n_tested), "n_scored": int(row.n_scored),
                  "share_flipped": None if isna(row.share_flipped) else round(float(row.share_flipped), 3),
                  "pattern": row.pattern}
        for c in dim_cols:
            v = row[c]
            entry[c] = None if isna(v) else int(v)
        score[name] = entry

    table_labels = [v[0] for v in idv.TABLES.values()]

    html = fill(load_template("infrastructure_divides.html"), {
        "SUMMARY": dump(summary_rows),
        "SCORE": dump(score),
        "TABLES": dump(table_labels),
    })
    write_page(out, html)
    return f"{len(score)} systems, {len(summary_rows)} table x dimension cells, {len(html) / 1024:.0f} KB"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--xlsx", type=Path, default=DEFAULT_XLSX)
    ap.add_argument("--out", type=Path, default=DOCS / "infrastructure-divides" / "index.html")
    args = ap.parse_args()
    print(f"Wrote {args.out}: {build(args.xlsx, args.out)}")


if __name__ == "__main__":
    main()
