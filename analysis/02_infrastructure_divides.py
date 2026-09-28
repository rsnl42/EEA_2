#!/usr/bin/env python3
"""#2  Which infrastructure divides actually exist.

Tables 4.1, 4.4, 4.5, 4.7, 4.8, 4.11 and 4.15 each split a school-resourcing measure
three ways -- by school socio-economic profile (advantaged vs disadvantaged), by
school location (city vs rural) and by type of school (private vs public) -- and each
reports a "Dif." (gap) and its S.E. for all three splits. The OECD text gives the
OECD-average gap and a handful of country call-outs per table; it doesn't cross-tabulate
the seven tables against each other, or check whether a system's gaps point the same
way across resource types and across dimensions.

That's what this script does: for every system, table and dimension, it tests whether
the gap is significant (|Dif. / S.E.| > 1.96), flips the sign for the two "lack of" /
"inadequate" tables (7 and 8) so that positive always means "the traditionally
better-off group -- advantaged, city, private -- is better resourced", and then counts,
per system, how many of the (up to) 21 gaps point the expected way, how many point the
other way, and how many aren't significant. A system where most gaps flip against the
expected direction looks like compensatory resourcing (extra kit sent to schools that
have less of everything else); a system where they don't agree with each other at all
looks like there's no single "digital divide", just several unrelated ones.

Usage:
    python analysis/02_infrastructure_divides.py [--xlsx PATH] [--out-dir DIR]
Outputs (default outputs/):
    02_infrastructure_gaps_by_system.csv   one row per system x table x dimension
    02_infrastructure_gap_summary.csv       one row per table x dimension (OECD gap, counts)
    02_infrastructure_scorecard.csv         one row per system (21-gap sign scorecard)
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from pisa_utils import OECD_ROW, Z95, Workbook, out_dir  # noqa: E402

# table -> (short label, unit suffix used in the workbook, True if higher-is-worse)
TABLES = {
    "1": ("Computer availability", "Mean ratio", False),
    "4": ("Tablet availability", "Mean ratio", False),
    "5": ("E-book reader availability", "Mean ratio", False),
    "7": ("Lack of digital resources", "%", True),
    "8": ("Inadequate/poor-quality digital resources", "%", True),
    "11": ("Internet-connected computers for teachers", "Mean ratio", False),
    "15": ("Capacity to enhance teaching with digital devices", "Mean index", False),
}
DIMENSIONS = {
    "ses": ("By school socio-economic profile1", "Disadvantaged schools", "Advantaged schools",
            "Advantaged -disadvantaged schools"),
    "location": ("By school location", "Rural area or village \n(fewer than 3 000 people)",
                 "City \n(over 100 000 people)", "City - rural area"),
    "type": ("By type of school", "Public", "Private", "Private - public"),
}


def extract(wb: Workbook) -> tuple[pd.DataFrame, pd.DataFrame]:
    long_rows = []
    for table, (label, unit, worse) in TABLES.items():
        for dim, (section, lo_name, hi_name, diff_name) in DIMENSIONS.items():
            lo = wb.num[f"[I.B1.4.{table}] {section} - {lo_name} - {unit}"]
            hi = wb.num[f"[I.B1.4.{table}] {section} - {hi_name} - {unit}"]
            gap = wb.num[f"[I.B1.4.{table}] {section} - {diff_name} - Dif."]
            se = wb.num[f"[I.B1.4.{table}] {section} - {diff_name} - S.E."]
            fav = -gap if worse else gap  # positive = traditionally better-off group is better resourced
            z = gap / se
            cell = pd.DataFrame({
                "system": wb.raw.index, "table": table, "table_label": label, "dimension": dim,
                "lo_value": lo.values, "hi_value": hi.values, "gap": gap.values, "se": se.values,
                "z": z.values, "sig": (z.abs() > Z95).values, "favorability_gap": fav.values,
            })
            long_rows.append(cell)
    long_df = pd.concat(long_rows, ignore_index=True)

    summary_rows = []
    for table, (label, unit, worse) in TABLES.items():
        for dim in DIMENSIONS:
            sub = long_df[(long_df.table == table) & (long_df.dimension == dim)]
            o = sub[sub.system == OECD_ROW].iloc[0]
            s = sub[sub.system != OECD_ROW]
            summary_rows.append({
                "table": table, "table_label": label, "dimension": dim,
                "oecd_gap": o.gap, "oecd_favorability_gap": o.favorability_gap, "oecd_se": o.se, "oecd_z": o.z,
                "n_systems": s.gap.notna().sum(),
                "n_sig_expected": int(((s.favorability_gap > 0) & s.sig).sum()),
                "n_sig_flipped": int(((s.favorability_gap < 0) & s.sig).sum()),
                "n_not_sig": int((~s.sig).sum()),
            })
    summary = pd.DataFrame(summary_rows)
    return long_df, summary


def build_scorecard(long_df: pd.DataFrame) -> pd.DataFrame:
    S = long_df[long_df.system != OECD_ROW].copy()
    S["sign"] = np.select([S.sig & (S.favorability_gap > 0), S.sig & (S.favorability_gap < 0)], [1, -1], default=0)
    wide = S.pivot_table(index="system", columns=["dimension", "table_label"], values="sign", aggfunc="first")
    wide.columns = [f"{dim}:{lbl}" for dim, lbl in wide.columns]

    counts = S.groupby("system")["sign"].agg(
        n_expected=lambda s: (s == 1).sum(), n_flipped=lambda s: (s == -1).sum(),
        n_flat=lambda s: (s == 0).sum(),
    )
    counts["n_scored"] = counts.n_expected + counts.n_flipped
    counts["share_flipped"] = (counts.n_flipped / counts.n_scored).where(counts.n_scored > 0)

    def label(row):
        if row.n_scored < 3:
            return "too few significant gaps to say"
        if row.share_flipped >= 0.6:
            return "mostly flipped (looks compensatory)"
        if row.share_flipped <= 0.2:
            return "mostly as expected"
        return "mixed / no single divide"

    counts["pattern"] = counts.apply(label, axis=1)
    return counts.join(wide)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--xlsx", type=Path, default=None)
    ap.add_argument("--out-dir", type=Path, default=None)
    args = ap.parse_args()

    wb = Workbook(args.xlsx)
    out = out_dir(args.out_dir)
    long_df, summary = extract(wb)
    scorecard = build_scorecard(long_df)

    print("OECD-average gaps (favorability: + = advantaged/city/private better resourced)")
    print(summary.round(2).to_string(index=False))
    print("\nScorecard pattern counts:")
    print(scorecard.pattern.value_counts().to_string())
    print("\nMost 'flipped' systems (share of significant gaps pointing the other way):")
    print(scorecard.sort_values("share_flipped", ascending=False)
          [["n_expected", "n_flipped", "n_flat", "share_flipped", "pattern"]].head(10).round(2).to_string())

    long_df.round(3).to_csv(out / "02_infrastructure_gaps_by_system.csv", index=False)
    summary.round(3).to_csv(out / "02_infrastructure_gap_summary.csv", index=False)
    scorecard.round(2).to_csv(out / "02_infrastructure_scorecard.csv")
    for name in ("02_infrastructure_gaps_by_system.csv", "02_infrastructure_gap_summary.csv",
                 "02_infrastructure_scorecard.csv"):
        print(f"\nWrote {out / name}")


if __name__ == "__main__":
    main()
