#!/usr/bin/env python3
"""#5  Leisure activity profiles: weekday (Table 4.37) vs weekend (Table 4.40).

Both tables give, for seven digital leisure activities, the % of students in six
daily-time bands (no time, <1h, 1-3h, 3-5h, 5-7h, >7h). The OECD text only discusses
2022->2025 shifts. This computes:

  - activity mixes: estimated hours/day per activity (band midpoints), per system
  - weekday-to-weekend shifts: change in estimated hours, and in the % of students
    above 3 hours a day, per activity
  - passive consumption vs creative use (grouping below)

Coverage is all-or-nothing, not scattered suppression. Only 44 of 91 systems have
values, all 42 cells each (6 bands x 7 activities, bands sum to 100); the other 47 have
none, in BOTH tables, and the same 44 appear in both. The covered systems are a skewed
sample (mean science score ~472 vs ~416 for the uncovered), so "OECD average" and
cross-country patterns here describe higher-scoring systems.

Decisions worth knowing:
  * Estimated hours use band midpoints: 0, 0.5, 2, 4, 6 and TOP=8 for ">7 hours".
    The open top band is the weak point, so the script reports how stable country
    rankings are if TOP=10 (Spearman rho per activity). Hours are an approximation;
    the % above 3 hours needs no midpoints and is the primary shift measure.
  * Activities overlap (multitasking), so the "mix" is each activity's share of the
    seven activities' estimated hours, NOT a share of total screen time. The seven
    estimates also sum to ~13 h on a weekday, far above the ~6 h total device time in
    Table 4.21: read estimated hours as a comparison tool, not as absolute time.
  * Passive consumption = browse social networks + browse the Internet for fun.
    Creative use = create or edit own digital content. These are judgement calls;
    gaming, communicating/sharing, practical information and tutorials are left in
    "other" rather than forced into either group.
  * Shift SEs: weekday and weekend come from the same students, so the independence
    SE sqrt(se_we^2 + se_wd^2) overstates the true SE (conservative). A shift is marked
    clear only if its conservative 95% interval excludes zero. The SE of a sum of bands
    is likewise conservative.

Usage:
    python analysis/05_leisure_profiles.py [--xlsx PATH] [--out-dir DIR]
Outputs (default outputs/): 05_leisure_metrics.csv (44 covered systems + the OECD average)
"""
import argparse
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

warnings.simplefilter("ignore", pd.errors.PerformanceWarning)  # wide frame built column by column
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from pisa_utils import OECD_ROW, Workbook, out_dir  # noqa: E402

ACT = {  # key: (keyword in workbook label, display label)
    "social": ("Browse social networks", "Browse social networks"),
    "web": ("Browse the Internet", "Browse the Internet for fun"),
    "comm": ("Communicate and share", "Communicate and share content"),
    "create": ("Create or edit", "Create or edit own content"),
    "info": ("Look for practical", "Look for practical information"),
    "games": ("Play video games", "Play video games"),
    "tutorial": ("Read, listen to or view", "Tutorials and how-to material"),
}
BANDS = ["No time at all", "Less than 1 hour a day", "Between 1 and 3 hours a day",
         "More than 3 hours and up to 5 hours a day", "More than 5 hours and up to 7 hours a day",
         "More than 7 hours a day\n"]  # the workbook header for this band really ends in a newline character
MID = np.array([0, 0.5, 2, 4, 6, 8.0])
TOP_ALT = 10.0
DAYS = {"wd": "37", "we": "40"}
PASSIVE, CREATIVE = ["social", "web"], ["create"]


def extract(wb: Workbook, top: float = 8.0, table_i1=None) -> pd.DataFrame:
    mid = MID.copy()
    mid[-1] = top
    X = pd.DataFrame(index=wb.raw.index)
    for day, tbl in DAYS.items():
        for a, (kw, _) in ACT.items():
            P, SE = zip(*[wb.pair(tbl, kw, endswith=f"{b} - %") for b in BANDS])
            P, SE = pd.concat(P, axis=1), pd.concat(SE, axis=1)
            ok = P.notna().all(axis=1)
            assert ((P.sum(axis=1)[ok] - 100).abs() < 0.3).all(), f"{day}/{a}: bands do not sum to 100"
            X[f"{a}_{day}_hrs"] = (P.values * mid).sum(axis=1) / 100
            X.loc[~ok, f"{a}_{day}_hrs"] = np.nan
            X[f"{a}_{day}_any"] = 100 - P.iloc[:, 0]
            X[f"{a}_{day}_gt3"] = P.iloc[:, 3:].sum(axis=1, min_count=3)
            X[f"{a}_{day}_gt3_se"] = np.sqrt((SE.iloc[:, 3:] ** 2).sum(axis=1, min_count=3))
    for a in ACT:
        X[f"{a}_shift_hrs"] = X[f"{a}_we_hrs"] - X[f"{a}_wd_hrs"]
        X[f"{a}_shift_gt3"] = X[f"{a}_we_gt3"] - X[f"{a}_wd_gt3"]
        X[f"{a}_shift_gt3_se"] = np.hypot(X[f"{a}_we_gt3_se"], X[f"{a}_wd_gt3_se"])
    for day in DAYS:
        tot = X[[f"{a}_{day}_hrs" for a in ACT]].sum(axis=1, min_count=len(ACT))
        X[f"total_{day}_hrs"] = tot
        for a in ACT:
            X[f"{a}_{day}_mix"] = 100 * X[f"{a}_{day}_hrs"] / tot
        X[f"passive_{day}_hrs"] = X[[f"{a}_{day}_hrs" for a in PASSIVE]].sum(axis=1, min_count=len(PASSIVE))
        X[f"creative_{day}_hrs"] = X[[f"{a}_{day}_hrs" for a in CREATIVE]].sum(axis=1, min_count=len(CREATIVE))
        X[f"pc_ratio_{day}"] = X[f"passive_{day}_hrs"] / X[f"creative_{day}_hrs"]
        X[f"creative_{day}_any"] = X["create_" + day + "_any"]
    if table_i1 is not None:
        X["science"] = table_i1["science"].reindex(X.index)
    return X


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--xlsx", type=Path, default=None)
    ap.add_argument("--out-dir", type=Path, default=None)
    args = ap.parse_args()
    wb, out = Workbook(args.xlsx), out_dir(args.out_dir)
    p = HERE.parent / "data" / "pisa2025_table_I1.csv"
    X = extract(wb, 8.0, pd.read_csv(p, index_col=0) if p.exists() else None)
    S = X.drop(OECD_ROW)
    cov = S["social_wd_hrs"].notna()
    print(f"Coverage: {int(cov.sum())} of {len(S)} systems have data; same set weekday and weekend: "
          f"{bool((cov == S['social_we_hrs'].notna()).all())}")
    if "science" in S:
        print(f"Mean science, covered vs uncovered: {S.science[cov].mean():.0f} vs {S.science[~cov].mean():.0f}")
    o = X.loc[OECD_ROW]
    print("\nOECD estimated hours/day (weekday -> weekend), shift in % above 3h:")
    for a, (_, lab) in ACT.items():
        print(f"  {lab:34s} {o[f'{a}_wd_hrs']:.2f} -> {o[f'{a}_we_hrs']:.2f}   >3h shift {o[f'{a}_shift_gt3']:+.1f} pp")
    print(f"OECD passive:creative hours ratio weekday {o.pc_ratio_wd:.1f}, weekend {o.pc_ratio_we:.1f}")

    Xalt = extract(wb, TOP_ALT).drop(OECD_ROW)
    print("\nRank stability if top band = 10h instead of 8h (Spearman rho, weekday / weekend hours):")
    for a, (_, lab) in ACT.items():
        r = [spearmanr(S.loc[cov, f"{a}_{d}_hrs"], Xalt.loc[cov, f"{a}_{d}_hrs"])[0] for d in DAYS]
        print(f"  {lab:34s} {r[0]:.3f} / {r[1]:.3f}")
    clear = {a: int((S.loc[cov, f"{a}_shift_gt3"].abs() > 1.96 * S.loc[cov, f"{a}_shift_gt3_se"]).sum()) for a in ACT}
    print("\nSystems (of", int(cov.sum()), ") with a clear weekday->weekend shift in % above 3h:", clear)

    X[X["social_wd_hrs"].notna()].round(3).to_csv(out / "05_leisure_metrics.csv", index_label="system")
    print(f"\nWrote {out / '05_leisure_metrics.csv'}")


if __name__ == "__main__":
    main()
