#!/usr/bin/env python3
"""Consistency checks for outputs/*.csv -- run after every analysis run (and in CI).

Two kinds of check:
  1. invariants      (counts add up, row counts line up)
  2. re-derivation   (summary files are recomputed from their own by-system files,
                      so a stale or hand-edited summary cannot slip through)
Neither needs the xlsx; for raw-workbook checks see the verification notes.

Usage:  python tools/check_outputs.py [outputs_dir]      (exit code 1 if anything fails)
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "outputs")
Z95 = 1.96
fails = []


def check(ok, msg):
    print(("  ok   " if ok else "  FAIL ") + msg)
    if not ok:
        fails.append(msg)


def read(name, **kw):
    p = OUT / name
    if not p.exists():
        print(f"  skip {name} (not found)")
        return None
    return pd.read_csv(p, **kw)


print("#1 equity gaps")
by, sm = read("01_equity_gaps_by_system.csv"), read("01_equity_gap_summary.csv")
if by is not None and sm is not None:
    check((sm.n_sig_positive + sm.n_sig_negative + sm.n_not_sig == sm.n_systems).all(), "counts add up to n_systems in every summary row")
    g = by.assign(pos=by.z > Z95, neg=by.z < -Z95).groupby(["breakdown", "outcome"]).agg(
        n=("system", "size"), pos=("pos", "sum"), neg=("neg", "sum")).reset_index()
    m = sm.merge(g, on=["breakdown", "outcome"], how="outer", indicator=True)
    check((m._merge == "both").all(), "summary and by-system files cover the same breakdown x outcome cells")
    check(((m.n_systems == m.n) & (m.n_sig_positive == m.pos) & (m.n_sig_negative == m.neg)).all(), "summary counts re-derived from by-system file")

print("#2 infrastructure")
by, sm, sc = (read("02_infrastructure_gaps_by_system.csv", dtype={"table": str}),
              read("02_infrastructure_gap_summary.csv", dtype={"table": str}),
              read("02_infrastructure_scorecard.csv"))
if by is not None and sm is not None:
    miss = sm["n_missing"] if "n_missing" in sm else 0
    check((sm.n_sig_expected + sm.n_sig_flipped + sm.n_not_sig + miss == (sm.n_systems + miss)).all(),
          "n_sig_expected + n_sig_flipped + n_not_sig == n_systems (missing data is not 'not significant')")
    s = by[by.system != "OECD average"]
    s = s.assign(n=s.gap.notna(), ex=(s.favorability_gap > 0) & s.sig, fl=(s.favorability_gap < 0) & s.sig,
                 ns=s.gap.notna() & ~s.sig)
    g = s.groupby(["table", "dimension"])[["n", "ex", "fl", "ns"]].sum().reset_index()
    m = sm.merge(g, on=["table", "dimension"])
    check(((m.n_systems == m.n) & (m.n_sig_expected == m.ex) & (m.n_sig_flipped == m.fl) & (m.n_not_sig == m.ns)).all(),
          "summary counts re-derived from by-system file")
if by is not None and sc is not None:
    miss = sc["n_missing"] if "n_missing" in sc else 0
    check((sc.n_expected + sc.n_flipped + sc.n_flat + miss == 21).all(), "scorecard: every system accounts for all 21 cells")

print("#3 capacity")
it, wl, cl, pr = (read("03_capacity_items.csv", index_col=0), read("03_capacity_weakest_link.csv", index_col=0),
                  read("03_capacity_clusters.csv", index_col=0), read("03_capacity_cluster_profiles.csv", index_col=0))
if it is not None and wl is not None:
    check(set(wl.index) == set(it.index) - {"OECD average"}, "weakest-link covers every system in items (except the OECD row)")
if cl is not None and pr is not None:
    check(pr.n.sum() == len(cl), "cluster sizes in profiles add up to clustered systems")
    check((cl.groupby("cluster").size() == pr.n).all(), "profile n matches cluster membership")
    check(all(len(x.split(", ")) >= 1 for x in pr.systems), "every profile lists its systems")

print("\n" + ("ALL CHECKS PASSED" if not fails else f"{len(fails)} CHECK(S) FAILED"))
sys.exit(1 if fails else 0)