#!/usr/bin/env python3
"""Build the AI use portfolios page (analysis #6) from analysis/06_ai_use_portfolios.py.

Usage:
    python build_ai_portfolios.py                 # writes docs/ai-portfolios/index.html
    python build_ai_portfolios.py --xlsx PATH --out PATH
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
K = 3


def load_analysis():
    sys.path.insert(0, str(ANALYSIS))
    spec = importlib.util.spec_from_file_location("ai_portfolios", ANALYSIS / "06_ai_use_portfolios.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def clean(v, nd=4):  # keep 4 decimals: the page rounds once, at display time
    return None if v is None or (isinstance(v, float) and math.isnan(v)) else round(float(v), nd)


def build(xlsx=DEFAULT_XLSX, out=DOCS / "ai-portfolios" / "index.html") -> str:
    ai = load_analysis()
    wb = ai.Workbook(xlsx)
    t1 = ROOT / "data" / "pisa2025_table_I1.csv"
    X = ai.extract(wb, pd.read_csv(t1, index_col=0) if t1.exists() else None)
    res, prof, _ = ai.cluster_systems(X, K)
    S = X.drop(ai.OECD_ROW)
    have = S.index[S["draft_wk"].notna()]
    keys = [c for c in X.columns if c != "science"]
    rows = [{"n": n, "cl": int(res.cluster[n]) if n in res.index else None, **{k: clean(S.loc[n, k]) for k in keys}}
            for n in have]
    oecd = {k: clean(X.loc[ai.OECD_ROW, k]) for k in keys}
    clus = [{"n": n, "cluster": int(r.cluster), "pc1": round(float(r.pc1), 2), "pc2": round(float(r.pc2), 2)}
            for n, r in res.iterrows()]
    profs = [{"cluster": int(c), "n": int(r.n), "label": r.label, "science_mean": clean(r.get("science_mean"), 0)}
             for c, r in prof.iterrows()]
    pur = [{"key": q, "label": lab} for q, (_, lab, _) in ai.PURPOSE.items()]

    miss = [n for n in S.index if n not in have]
    note = ""
    if miss:
        note = (f" {len(have)} of {len(S)} systems are covered; no Table 4.53 values exist for "
                f"{'; '.join(html_escape(n) for n in miss)}.")
    html = fill(load_template("ai_portfolios.html"), {
        "ROWS": json.dumps(rows, separators=(",", ":"), ensure_ascii=False),
        "OECD": json.dumps(oecd, separators=(",", ":")), "CLUS": json.dumps(clus, separators=(",", ":")),
        "PROF": json.dumps(profs, ensure_ascii=False), "PUR": json.dumps(pur, ensure_ascii=False),
        "COVERAGE": note,
    })
    write_page(Path(out), html)
    return f"{len(rows)} systems, {len(profs)} clusters, {len(html) / 1024:.0f} KB"


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--xlsx", type=Path, default=DEFAULT_XLSX)
    ap.add_argument("--out", type=Path, default=DOCS / "ai-portfolios" / "index.html")
    a = ap.parse_args()
    print(f"Wrote {a.out}: {build(a.xlsx, a.out)}")
