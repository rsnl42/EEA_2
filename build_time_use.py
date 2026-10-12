#!/usr/bin/env python3
"""Build the time-use budgets page (analysis #4) from analysis/04_time_use_budgets.py.

Usage:
    python build_time_use.py                    # writes docs/time-use/index.html
    python build_time_use.py --xlsx PATH --out PATH
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
K = 4
KEEP = (["Ls", "Lb", "Lw", "Es", "Eb", "Ew", "wd_total", "we_total", "ratio_s", "ratio_b", "ratio_w", "ratio_wd",
         "school_share_learn", "school_share_leisure"]
        + [f"{a}{c}_{t}{s}" for a in "LE" for c in "sbw" for t in ("gt5", "gt7") for s in ("", "_se")])


def load_analysis():
    sys.path.insert(0, str(ANALYSIS))
    spec = importlib.util.spec_from_file_location("time_use", ANALYSIS / "04_time_use_budgets.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def clean(v, nd=2):
    return None if v is None or (isinstance(v, float) and math.isnan(v)) else round(float(v), nd)


def build(xlsx=DEFAULT_XLSX, out=DOCS / "time-use" / "index.html") -> str:
    ta = load_analysis()
    wb = ta.Workbook(xlsx)
    t1 = ROOT / "data" / "pisa2025_table_I1.csv"
    X = ta.extract(wb, pd.read_csv(t1, index_col=0) if t1.exists() else None)
    res, prof, _ = ta.cluster_systems(X, K)
    dump = lambda o: json.dumps(o, separators=(",", ":"), ensure_ascii=False)  # noqa: E731

    S = X.drop(ta.OECD_ROW)
    have = S.index[S[["Ls", "Lb", "Lw", "Es", "Eb", "Ew"]].notna().all(axis=1)]
    all_systems = list(S.index)
    rows = [{"n": n, **{k: clean(S.loc[n, k]) for k in KEEP}} for n in all_systems]
    oecd = {k: clean(X.loc[ta.OECD_ROW, k]) for k in KEEP}
    clus = [{"n": n, "cluster": int(r.cluster), "pc1": round(float(r.pc1), 2), "pc2": round(float(r.pc2), 2)}
            for n, r in res.iterrows()]
    profs = [{"cluster": int(c), "n": int(r.n), "label": r.label,
              "science_mean": clean(r.get("science_mean"), 0)} for c, r in prof.iterrows()]

    missing = [n for n in S.index if n not in have]
    excl = ""
    if missing:
        who = "; ".join(html_escape(n) for n in missing)
        excl = (f" {len(have)} of {len(S)} systems have full time-use data. {who} has no time-use "
                f"figures in Table I.B1.4.21 (all items marked M in the country lookup).")
    stats = {"n": len(have), "oecd": oecd}
    html = fill(load_template("time_use.html"), {
        "ROWS": dump(rows), "OECD": dump(oecd), "CLUS": dump(clus), "PROF": dump(profs),
        "STATS": dump(stats), "EXCL": excl,
    })
    write_page(Path(out), html)
    return f"{len(rows)} systems, {len(profs)} clusters, {len(html) / 1024:.0f} KB"


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--xlsx", type=Path, default=DEFAULT_XLSX)
    ap.add_argument("--out", type=Path, default=DOCS / "time-use" / "index.html")
    a = ap.parse_args()
    print(f"Wrote {a.out}: {build(a.xlsx, a.out)}")
