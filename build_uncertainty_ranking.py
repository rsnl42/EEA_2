#!/usr/bin/env python3
"""Build the uncertainty-aware ranking page (analysis #10) from analysis/10_uncertainty_ranking.py.

Usage:
    python build_uncertainty_ranking.py              # writes docs/uncertainty-ranking/index.html
    python build_uncertainty_ranking.py --xlsx PATH --out PATH
"""
import argparse
import importlib.util
import json
import sys
from pathlib import Path

from site_common import DEFAULT_XLSX, DOCS, ROOT, fill, load_template, write_page

ANALYSIS = ROOT / "analysis"


def load_analysis():
    sys.path.insert(0, str(ANALYSIS))
    spec = importlib.util.spec_from_file_location("uncertainty", ANALYSIS / "10_uncertainty_ranking.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def build(xlsx=DEFAULT_XLSX, out=DOCS / "uncertainty-ranking" / "index.html") -> str:
    ua = load_analysis()
    wb = ua.Workbook(xlsx)
    data = {}
    for key in ua.IND:
        D, st, (label, fmt, src, tbl) = ua.analyse(wb, key)
        rows = [[n, round(float(r.est), 4), round(float(r.se), 5), int(r["rank"]), int(r.rank_lo),
                 int(r.rank_hi), int(r.rank_med)] for n, r in D.sort_values("est", ascending=False).iterrows()]
        shares = dict(list(st["shares"].items())[:8])
        for f, v in st["focus"].items():
            shares.setdefault(f, v)
        stats = {k: (round(float(v), 4) if isinstance(v, (int, float)) else v) for k, v in st.items()
                 if k in ("n", "z_bonf", "pairs_sig", "pairs_sig_bonf", "adjacent_sig", "adjacent_sig_bonf",
                          "median_rank_width", "mean_unweighted", "mean_fe", "se_fe", "mean_re", "se_re", "tau",
                          "I2", "n_eff", "top_name", "top_share", "tiny_se")}
        data[key] = {"label": label, "fmt": fmt, "src": src, "table": tbl, "rows": rows, "stats": stats,
                     "shares": shares, "focus": st["focus"]}
    html = fill(load_template("uncertainty_ranking.html"), {
        "DATA": json.dumps(data, separators=(",", ":"), ensure_ascii=False),
        "ORDER": json.dumps(list(ua.IND)), "NSIM": f"{ua.N_SIM:,}",
    })
    write_page(Path(out), html)
    return f"{len(data)} indicators, {len(html) / 1024:.0f} KB"


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--xlsx", type=Path, default=DEFAULT_XLSX)
    ap.add_argument("--out", type=Path, default=DOCS / "uncertainty-ranking" / "index.html")
    a = ap.parse_args()
    print(f"Wrote {a.out}: {build(a.xlsx, a.out)}")
