#!/usr/bin/env python3
"""#9a  Cross-domain country panel.

Builds one row per education system with indicators spanning resources, teacher
capacity, time use, leisure activity, distraction, school rules, and AI use and
guidance, plus science performance as external context (from Volume I Table I.1,
not the chapter-4 workbook). This is the panel #9b (correlations/synthesis) and
#9c (clustering) build on; it does not itself compute correlations or clusters.

Each raw indicator keeps its native unit (ratio, %, hours, index points) so it can
be read on its own. Composite z-score indices average same-direction indicators
after standardising, requiring at least `MIN_COVERAGE` of the group's indicators
per system; indicators known to run the opposite way (e.g. resource *shortages*)
are sign-flipped before averaging so that higher composite = "more resourced",
"more capacity", etc.

Usage:
    python analysis/09_cross_domain_panel.py [--xlsx PATH] [--table-i1 PATH] [--out-dir DIR]
Outputs (default outputs/):
    09_panel_raw.csv         one row per system, raw indicators + science context
    09_panel_composites.csv  one row per system, standardised composite indices
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from pisa_utils import OECD_ROW, Workbook, out_dir  # noqa: E402

MIN_COVERAGE = 0.5  # a composite needs values for at least this share of its indicators

# name -> (domain, description, unit)
INDICATORS = {
    "computers_per_student": ("Resources", "Computers available for students (ratio)", "ratio"),
    "tablets_per_student": ("Resources", "Tablets available for students (ratio)", "ratio"),
    "computers_per_teacher": ("Resources", "Internet-connected computers available per teacher (ratio)", "ratio"),
    "short_quantity": ("Resources", "School reports a lack of digital resources (some extent or a lot)", "pp"),
    "short_quality": ("Resources", "School reports inadequate/poor-quality digital resources (some extent or a lot)", "pp"),
    "capacity_index": ("Capacity", "Digital capacity index (school-reported)", "index"),
    "cap_bandwidth": ("Capacity", "School reports sufficient Internet bandwidth (agree/strongly agree)", "pp"),
    "cap_teacher_skills": ("Capacity", "School reports teachers have the skills to integrate digital devices", "pp"),
    "cap_teacher_time": ("Capacity", "School reports teachers have time to prepare digital lessons", "pp"),
    "cap_support_staff": ("Capacity", "School reports sufficient support staff for technical problems", "pp"),
    "learn_hours_school": ("Time use", "Digital learning activities at school (hours/day)", "hours"),
    "learn_hours_outside": ("Time use", "Digital learning activities before/after school + weekends (hours/day, averaged)", "hours"),
    "learn_none_school": ("Time use", "No digital learning activities at school", "pp"),
    "leisure_hours_school": ("Time use", "Digital leisure at school (hours/day)", "hours"),
    "leisure_hours_outside": ("Time use", "Digital leisure before/after school + weekends (hours/day, averaged)", "hours"),
    "social_weekday_3h": ("Leisure", "Social media >=3 hours/day on a weekday", "pp"),
    "games_weekday_3h": ("Leisure", "Video games >=3 hours/day on a weekday", "pp"),
    "distraction": ("Distraction", "Students report digital distraction in class", "pp"),
    "phone_ban": ("Rules", "School: cell phones not allowed on premises", "pp"),
    "subject_guidelines": ("Rules", "School: formal guidelines for digital devices in specific subjects", "pp"),
    "teacher_set_rules": ("Rules", "Teachers establish rules for in-class device use", "pp"),
    "co_set_rules": ("Rules", "Rules set in collaboration with students", "pp"),
    "responsible_use_programme": ("Rules", "School has a programme for responsible Internet behaviour", "pp"),
    "ai_use_any": ("AI", "Used AI for at least one schoolwork purpose", "pp"),
    "ai_use_index": ("AI", "AI-use index (mean)", "index"),
    "ai_guidance": ("AI", "Tasked with assessing AI-generated information", "pp"),
    "online_guidance": ("AI", "Tasked with assessing information found online", "pp"),
}

# composite name -> (domain label, [(indicator, sign)]); sign -1 flips a "bad-direction" indicator
COMPOSITES = {
    "resources": ("Resources", [("computers_per_student", 1), ("tablets_per_student", 1),
                                  ("computers_per_teacher", 1), ("short_quantity", -1), ("short_quality", -1)]),
    "capacity": ("Capacity", [("capacity_index", 1), ("cap_bandwidth", 1), ("cap_teacher_skills", 1),
                                ("cap_teacher_time", 1), ("cap_support_staff", 1)]),
    "learning_time_school": ("Time use", [("learn_hours_school", 1), ("learn_none_school", -1)]),
    "leisure_at_school": ("Time use", [("leisure_hours_school", 1)]),
    "leisure_outside_school": ("Time use", [("leisure_hours_outside", 1)]),
    "distraction": ("Distraction", [("distraction", 1)]),
    "rules": ("Rules", [("phone_ban", 1), ("subject_guidelines", 1), ("teacher_set_rules", 1), ("co_set_rules", 1)]),
    "ai_use": ("AI", [("ai_use_any", 1), ("ai_use_index", 1)]),
    "ai_guidance": ("AI", [("ai_guidance", 1)]),
}


def build_raw(wb: Workbook, table_i1: pd.DataFrame) -> pd.DataFrame:
    e = wb.est
    P = pd.DataFrame(index=wb.raw.index)

    P["computers_per_student"] = e("1", "Average - Mean ratio")
    P["tablets_per_student"] = e("4", "Average - Mean ratio")
    P["computers_per_teacher"] = e("11", "Average - Mean ratio")
    shortage = lambda item: (e("6", item, endswith="To some extent - %")  # noqa: E731
                              + e("6", item, endswith="A lot - %"))
    P["short_quantity"] = shortage("A lack of digital resources")
    P["short_quality"] = shortage("Inadequate or poor-quality")

    P["capacity_index"] = e("14", "Average - Mean index")
    agree = lambda item: (e("14", item, endswith="Agree - %")  # noqa: E731
                           + e("14", item, endswith="Strongly agree - %"))
    P["cap_bandwidth"] = agree("Internet bandwidth or speed is sufficient")
    P["cap_teacher_skills"] = agree("necessary technical and pedagogical skills")
    P["cap_teacher_time"] = agree("sufficient time to prepare lessons")
    P["cap_support_staff"] = agree("sufficient supporting staff")

    hrs = lambda label: e("21", f"{label} - Hours")  # noqa: E731
    P["learn_hours_school"] = hrs("Learning activities at school")
    P["learn_hours_outside"] = (hrs("Learning activities before and after school")
                                 + hrs("Learning activities on weekends")) / 2
    P["learn_none_school"] = e("21", "Learning activities at school - None - %")
    P["leisure_hours_school"] = hrs("Leisure at school")
    P["leisure_hours_outside"] = (hrs("Leisure before and after school") + hrs("Leisure on weekends")) / 2

    heavy = lambda table, item: 100 - (  # noqa: E731
        e(table, item, endswith="No time at all - %")
        + e(table, item, endswith="Less than 1 hour a day - %")
        + e(table, item, endswith="Between 1 and 3 hours a day - %")
    )
    P["social_weekday_3h"] = heavy("37", "Browse social networks")
    P["games_weekday_3h"] = heavy("37", "Play video games")

    P["distraction"] = e("43", "All students")

    yes = lambda item: e("47", item, endswith="Yes - %")  # noqa: E731
    P["phone_ban"] = yes("cell phones is not allowed")
    P["subject_guidelines"] = yes("formal guidelines for the use of digital devices for teaching")
    P["teacher_set_rules"] = yes("Teachers establish rules for when students may use")
    P["co_set_rules"] = yes("in collaboration with students")
    P["responsible_use_programme"] = yes("specific programme to prepare students for responsible")

    P["ai_use_any"] = 100 - e("55", "All students")
    P["ai_use_index"] = e("53", "Average - Mean index")
    P["ai_guidance"] = e("68", "All students")
    P["online_guidance"] = 100 - e("67", "information found online", endswith="Never or almost never - %")

    missing = [c for c in INDICATORS if c not in P.columns]
    if missing:
        sys.exit(f"Internal error: no column built for {missing}")

    P = P.join(table_i1[["science", "d_science"]], how="left")
    return P[list(INDICATORS) + ["science", "d_science"]]


def build_composites(P: pd.DataFrame) -> pd.DataFrame:
    S = P.drop(OECD_ROW)
    Z = (S - S.mean()) / S.std(ddof=0)
    out = {}
    for name, (_, parts) in COMPOSITES.items():
        cols = pd.concat([sign * Z[ind] for ind, sign in parts], axis=1)
        coverage = cols.notna().mean(axis=1)
        out[name] = cols.mean(axis=1).where(coverage >= MIN_COVERAGE)
    C = pd.DataFrame(out, index=S.index)
    C["science"] = S["science"]
    return C


def report(P: pd.DataFrame, C: pd.DataFrame) -> None:
    S = P.drop(OECD_ROW)
    print(f"Systems: {len(S)} (of {len(P) - 1} plus OECD average)\n")
    print("Coverage (systems with a value) and OECD average, per raw indicator")
    for name, (domain, desc, unit) in INDICATORS.items():
        n = S[name].notna().sum()
        oecd = P.loc[OECD_ROW, name]
        print(f"  [{domain:10s}] {name:26s} n={n:2d}/{len(S)}  OECD={oecd:6.1f} {unit:6s} {desc}")
    print(f"  [context  ] science{'':19s} n={S['science'].notna().sum():2d}/{len(S)}  "
          f"OECD={P.loc[OECD_ROW, 'science']:6.1f} points  Mean science score (Table I.1)")

    print("\nComposite indices (standardised; higher = more of the named thing)")
    for name, (domain, parts) in COMPOSITES.items():
        cov = C[name].notna().sum()
        cols = ", ".join(f"{'-' if s < 0 else ''}{i}" for i, s in parts)
        print(f"  [{domain:10s}] {name:24s} n={cov:2d}/{len(S)}  from: {cols}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--xlsx", type=Path, default=None)
    ap.add_argument("--table-i1", type=Path, default=HERE.parent / "data" / "pisa2025_table_I1.csv")
    ap.add_argument("--out-dir", type=Path, default=None)
    args = ap.parse_args()

    if not args.table_i1.exists():
        sys.exit(f"{args.table_i1} not found. Run analysis/extract_table_I1.py PISA_25.pdf first.")
    table_i1 = pd.read_csv(args.table_i1, index_col=0)

    wb = Workbook(args.xlsx)
    P = build_raw(wb, table_i1)
    C = build_composites(P)
    report(P, C)

    out = out_dir(args.out_dir)
    P.round(3).to_csv(out / "09_panel_raw.csv", index_label="system")
    C.round(3).to_csv(out / "09_panel_composites.csv", index_label="system")
    print(f"\nWrote {out / '09_panel_raw.csv'} and {out / '09_panel_composites.csv'}")


if __name__ == "__main__":
    main()
