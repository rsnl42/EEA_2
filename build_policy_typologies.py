#!/usr/bin/env python3
"""Build the "How are schools governing devices and AI?" page (analysis #8).

The numbers come straight from analysis/08_policy_typologies.py's functions, so
the page and the script's CSV/console output always agree.

Usage:
    python build_policy_typologies.py           # writes docs/policy-typologies/index.html
    python build_policy_typologies.py --xlsx PATH --out PATH
"""
import argparse
import importlib.util
import json
import sys
from pathlib import Path

from site_common import DEFAULT_XLSX, DOCS, ROOT, fill, load_template, write_page

ANALYSIS = ROOT / "analysis"


def load_analysis():
    """Import analysis/08_policy_typologies.py (its name isn't a valid module name)."""
    sys.path.insert(0, str(ANALYSIS))
    spec = importlib.util.spec_from_file_location("policy_typologies", ANALYSIS / "08_policy_typologies.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def build(xlsx: Path, out: Path) -> str:
    pt = load_analysis()
    from pisa_utils import OECD_ROW, Workbook

    wb = Workbook(xlsx)
    out_dir_ = pt.out_dir()
    policy = pt.build_policy_index(wb)
    regime = pt.build_regime_typology(wb)
    C = pt.load_composites(xlsx, out_dir_)
    df = pt.build_outcome_frame(policy, regime, C)

    dump = lambda o: json.dumps(o, separators=(",", ":"), ensure_ascii=False)  # noqa: E731

    S = regime.drop(OECD_ROW)
    O = regime.loc[OECD_ROW]
    regime_cols = ["neither_2022", "neither_2025", "neither_change", "neither_z", "neither_sig",
                   "bans_only_2022", "bans_only_2025", "bans_only_change", "bans_only_z", "bans_only_sig",
                   "guidelines_only_2022", "guidelines_only_2025", "guidelines_only_change",
                   "guidelines_only_z", "guidelines_only_sig",
                   "both_2022", "both_2025", "both_change", "both_z", "both_sig",
                   "depth_2022", "depth_2025", "adopter_status"]
    def row_value(c, v):
        if c == "adopter_status":
            return v
        if pd_isna(v):
            return None
        if c.endswith("_sig"):
            return bool(v)
        return round(float(v), 3)

    regime_rows = [
        {"n": name, **{c: row_value(c, row[c]) for c in regime_cols}}
        for name, row in S.iterrows()
    ]

    P = policy.drop(OECD_ROW)
    policy_rows = [
        {"n": name, "policy_intensity": None if pd_isna(row["policy_intensity"]) else round(float(row["policy_intensity"]), 3)}
        for name, row in P.iterrows()
    ]

    corr_rows = pt.outcome_correlations(policy, regime, C)
    open_q = []
    for outcome in pt.OUTCOME_COLS:
        stat = corr_rows[(corr_rows.policy_var == "phone_ban") & (corr_rows.outcome == outcome)].iloc[0]
        d = df[["phone_ban", outcome]].dropna()
        points = [{"n": n, "x": round(float(x), 2), "y": round(float(y), 3)}
                  for n, x, y in zip(d.index, d["phone_ban"], d[outcome])]
        open_q.append({"outcome": outcome, "rho": round(float(stat.rho), 2), "p": round(float(stat.p), 4),
                        "n": int(stat.n), "points": points})

    stats = {
        "n_systems": int(len(S)),
        "n_fast": int((S.adopter_status == "fast adopter").sum()),
        "n_lag": int((S.adopter_status == "lagging").sum()),
        "depth_change": round(float(O["depth_change"]), 2),
        "rho_ban_distraction": next(o["rho"] for o in open_q if o["outcome"] == "distraction"),
        "oecd": {"depth_2022": round(float(O["depth_2022"]), 2), "depth_2025": round(float(O["depth_2025"]), 2)},
    }

    html = fill(load_template("policy_typologies.html"), {
        "STATS": dump(stats),
        "REGIME_ROWS": dump(regime_rows),
        "POLICY_ROWS": dump(policy_rows),
        "OPEN_Q": dump(open_q),
    })
    write_page(out, html)
    return f"{len(regime_rows)} systems, {len(html) / 1024:.0f} KB"


def pd_isna(v) -> bool:
    import math
    try:
        return v is None or (isinstance(v, float) and math.isnan(v))
    except Exception:
        return False


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--xlsx", type=Path, default=DEFAULT_XLSX)
    ap.add_argument("--out", type=Path, default=DOCS / "policy-typologies" / "index.html")
    args = ap.parse_args()
    print(f"Wrote {args.out}: {build(args.xlsx, args.out)}")


if __name__ == "__main__":
    main()
