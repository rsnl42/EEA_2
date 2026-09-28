#!/usr/bin/env python3
"""#1  Equity gaps beyond SES.

For each of 9 outcomes x 8 breakdowns (72 comparisons) this computes the OECD-average
gap (first group minus second group) and, across systems, how many show a significant
gap in each direction (|gap / S.E.| > 1.96).

It reuses the extraction and layout checks in build_dashboard.py, so the analysis and
the dashboard always read the same numbers.

Usage:
    python analysis/01_equity_gaps.py [--xlsx PATH] [--out-dir DIR]
Outputs (default outputs/):
    01_equity_gap_summary.csv      one row per outcome x breakdown
    01_equity_gaps_by_system.csv   one row per outcome x breakdown x system (gap, S.E., CI)
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
from build_dashboard import DIMENSIONS, TABLES, extract, load  # noqa: E402
from pisa_utils import Z95, out_dir  # noqa: E402

OUTCOMES = [
    "Never used AI for any purpose", "AI-use index", "Not using AI to summarise",
    "Not using AI for research", "Not using AI to draft text", "Not using AI to help them learn",
    "Tasked with assessing AI-generated information", "Digital distraction in class",
    "Not using digital devices for learning at school",
]
BREAKDOWNS = [
    "Gender (boys - girls)", "Student SES (advantaged - disadvantaged)",
    "Immigrant background (immigrant - non-immigrant)", "Education level (ISCED 3 - ISCED 2)",
    "Programme orientation (general - vocational)", "School SES (advantaged - disadvantaged schools)",
    "School location (city - rural)", "Type of school (private - public)",
]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--xlsx", type=Path, default=HERE.parent / "data" / "digital_devices_AI_chapter4.xlsx")
    ap.add_argument("--out-dir", type=Path, default=None)
    args = ap.parse_args()

    names, D, O = extract(load(args.xlsx))
    summary, by_system = [], []
    for d, dim in enumerate(BREAKDOWNS):
        for j, outcome in enumerate(OUTCOMES):
            cell = pd.DataFrame(D[d][j], columns=["i", "gap", "se"])
            cell["system"] = [names[i] for i in cell.i]
            cell["z"] = cell.gap / cell.se
            cell["lo"], cell["hi"] = cell.gap - Z95 * cell.se, cell.gap + Z95 * cell.se
            cell["breakdown"], cell["outcome"] = dim, outcome
            by_system.append(cell.drop(columns="i"))
            og, ose = O[d][j]
            summary.append({
                "breakdown": dim, "outcome": outcome, "unit": "index points" if j == 1 else "pp",
                "oecd_gap": og, "oecd_se": ose, "oecd_z": round(og / ose, 2) if ose > 0 else float("nan"),
                "n_systems": len(cell),
                "n_sig_positive": int((cell.z > Z95).sum()),
                "n_sig_negative": int((cell.z < -Z95).sum()),
                "n_not_sig": int((cell.z.abs() <= Z95).sum()),
                "median_gap": round(float(cell.gap.median()), 2),
                "largest_positive": cell.loc[cell.gap.idxmax(), "system"],
                "largest_positive_gap": float(cell.gap.max()),
                "largest_negative": cell.loc[cell.gap.idxmin(), "system"],
                "largest_negative_gap": float(cell.gap.min()),
            })

    S = pd.DataFrame(summary)
    B = pd.concat(by_system, ignore_index=True)[
        ["breakdown", "outcome", "system", "gap", "se", "z", "lo", "hi"]]
    out = out_dir(args.out_dir)
    S.to_csv(out / "01_equity_gap_summary.csv", index=False)
    B.round(3).to_csv(out / "01_equity_gaps_by_system.csv", index=False)

    pd.set_option("display.width", 200, "display.max_colwidth", 44)
    print(S[["breakdown", "outcome", "oecd_gap", "oecd_z", "n_systems", "n_sig_positive",
             "n_sig_negative"]].to_string(index=False))
    print(f"\nWrote {out / '01_equity_gap_summary.csv'} and {out / '01_equity_gaps_by_system.csv'}")
    print(f"Note: with ~85 tests per row, expect roughly {0.025 * 85:.0f} false positives per direction.")


if __name__ == "__main__":
    main()
