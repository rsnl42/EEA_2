#!/usr/bin/env python3
"""#4  Time-use budgets: learning vs leisure on digital devices.

Table 4.21 gives, per system, hours per day on digital devices for learning and for
leisure in three contexts (at school, before/after school on weekdays, on a weekend
day): six means, plus seven hour-bands (none ... more than 7 hours) for each. The OECD
text reports the OECD-average hours; it does not compare learning with leisure
country by country, split the weekday between school and home, or look at the heavy
tails. This computes:

  - learning-to-leisure ratio per context (ratio of the two reported means; >1 means
    more learning than leisure) and for the whole weekday (school + before/after)
  - the school vs out-of-school split of the weekday: the share of weekday learning
    hours, and of weekday leisure hours, that happen at school
  - heavy-use tails: % of students above 5 hours and above 7 hours per day, per
    activity/context (sum of the top two bands, and the top band)
  - Ward clustering into time-use archetypes

Decisions worth knowing:
  * Weekday total = at school + before/after school. The OECD text does the same
    ("close to 3 hours per weekday, including 1.2 before and after school"); the
    workbook reproduces it (1.73 + 1.24 = 2.97). Weekends are a separate per-day figure.
    No 5:2 week-weighting is applied, so nothing here is a weekly total.
  * Ratios and splits are derived from two separately reported means. Their sampling
    covariance is not in the table, so they carry NO confidence intervals. The tail
    shares do: SE of (5-7h + >7h) is sqrt(se1^2+se2^2), which slightly overstates the
    true SE (categories of one question are negatively correlated), i.e. conservative.
  * Clustering uses weekday total, weekend total and the learning share of device time
    in each of the three contexts (5 z-scored features). The six raw means were tried
    first: they are unstable (bootstrap stability 0.33-0.45) and k=3 yields a
    2-system cluster, because the means mostly measure overall device intensity.
  * United States has no Table 4.21 values, so everything here covers 90 systems.

Usage:
    python analysis/04_time_use_budgets.py [--xlsx PATH] [--k N] [--out-dir DIR]
Outputs (default outputs/):
    04_time_use_metrics.csv, 04_time_use_k_selection.csv,
    04_time_use_clusters.csv, 04_time_use_cluster_profiles.csv
"""
import argparse
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import fcluster, linkage
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_samples

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from pisa_utils import OECD_ROW, Workbook, out_dir  # noqa: E402

try:
    _spec = importlib.util.spec_from_file_location("cap03", HERE / "03_capacity_bottlenecks.py")
    _cap = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_cap)
except Exception:
    _cap = None

ACT = {"L": "Learning activities", "E": "Leisure"}
CTX = {"s": "at school", "b": "before and after school", "w": "on weekends"}
BANDS = ["None", "Up to 1 hour", "More than 1 hour and up to 2 hours", "More than 2 hours and up to 3 hours",
         "More than 3 hours and up to 5 hours", "More than 5 hours and up to 7 hours", "More than 7 hours"]
FEATURES = {
    "wd_total": "weekday device time", "we_total": "weekend device time",
    "lshare_s": "learning share at school", "lshare_b": "learning share before/after school",
    "lshare_w": "learning share on weekends",
}


def extract(wb: Workbook, table_i1=None) -> pd.DataFrame:
    X = pd.DataFrame(index=wb.raw.index)
    for a in ACT:
        for c in CTX:
            X[f"{a}{c}"] = wb.est("21", f"{ACT[a]} {CTX[c]} - Hours")
            band = [wb.est("21", f"{ACT[a]} {CTX[c]} - {b}", endswith="%") for b in BANDS]
            ok = pd.concat(band, axis=1).notna().all(axis=1)
            assert ((sum(band)[ok] - 100).abs() < 0.3).all(), f"bands for {a}{c} do not sum to 100"
            p57, se57 = wb.pair("21", f"{ACT[a]} {CTX[c]} - {BANDS[5]}", endswith="%")
            p7, se7 = wb.pair("21", f"{ACT[a]} {CTX[c]} - {BANDS[6]}", endswith="%")
            X[f"{a}{c}_gt5"], X[f"{a}{c}_gt5_se"] = p57 + p7, np.hypot(se57, se7)
            X[f"{a}{c}_gt7"], X[f"{a}{c}_gt7_se"] = p7, se7
    X["wd_learn"], X["wd_leisure"] = X.Ls + X.Lb, X.Es + X.Eb
    X["wd_total"], X["we_total"] = X.wd_learn + X.wd_leisure, X.Lw + X.Ew
    for c in CTX:
        X[f"ratio_{c}"] = X[f"L{c}"] / X[f"E{c}"]
        X[f"lshare_{c}"] = X[f"L{c}"] / (X[f"L{c}"] + X[f"E{c}"])
    X["ratio_wd"] = X.wd_learn / X.wd_leisure
    X["school_share_learn"] = 100 * X.Ls / X.wd_learn  # % of weekday learning hours spent at school
    X["school_share_leisure"] = 100 * X.Es / X.wd_leisure
    X["lshare_s"], X["lshare_b"], X["lshare_w"] = 100 * X.lshare_s, 100 * X.lshare_b, 100 * X.lshare_w
    if table_i1 is not None:
        X["science"] = table_i1["science"].reindex(X.index)
    return X


def name_cluster(z: pd.Series) -> str:
    """Label from z-scores (a real zero point); never from raw hours or percentages."""
    parts = [f"{'high' if z[f] > 0 else 'low'} {FEATURES[f]}"
             for f in z.abs().sort_values(ascending=False).index[:2] if abs(z[f]) >= 0.3]
    return ", ".join(parts) or "close to average on every feature"


def cluster_systems(X: pd.DataFrame, k: int):
    S = X.drop(OECD_ROW)[list(FEATURES)].dropna()
    Z = (S - S.mean()) / S.std(ddof=0)
    lab = fcluster(linkage(Z.values, "ward"), k, "maxclust")
    pcs = PCA(n_components=2, random_state=0).fit_transform(Z.values)
    res = S.copy()
    res["cluster"], res["silhouette"] = lab, silhouette_samples(Z.values, lab).round(3)
    res["pc1"], res["pc2"] = pcs[:, 0], pcs[:, 1]
    if "science" in X.columns:
        res["science"] = X["science"].reindex(res.index)
    zm = Z.assign(cluster=lab).groupby("cluster")[list(FEATURES)].mean()
    prof = res.groupby("cluster")[list(FEATURES)].mean()
    prof["n"] = res.groupby("cluster").size()
    if "science" in res.columns:
        prof["science_mean"] = res.groupby("cluster")["science"].mean().round(0)
    prof["label"] = zm.apply(name_cluster, axis=1)
    prof["systems"] = res.groupby("cluster").apply(lambda d: ", ".join(sorted(d.index)))
    return res, prof, Z


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--xlsx", type=Path, default=None)
    ap.add_argument("--k", type=int, default=4)
    ap.add_argument("--out-dir", type=Path, default=None)
    args = ap.parse_args()
    wb, out = Workbook(args.xlsx), out_dir(args.out_dir)
    p = HERE.parent / "data" / "pisa2025_table_I1.csv"
    X = extract(wb, pd.read_csv(p, index_col=0) if p.exists() else None)

    S = X.drop(OECD_ROW)
    print("Coverage:", S[list(ACT[a][0] + c for a in ACT for c in CTX)].notna().all(axis=1).sum(), "of", len(S))
    print("Systems missing Table 4.21:", S.index[S.Ls.isna()].tolist())
    o = X.loc[OECD_ROW]
    print(f"OECD weekday: learning {o.wd_learn:.2f} h, leisure {o.wd_leisure:.2f} h, total {o.wd_total:.2f} "
          f"(report: ~3 learning, ~6 total); weekend total {o.we_total:.2f} (report: ~5)")
    print("OECD learning:leisure ratio at school / before-after / weekend:",
          *(f"{o[f'ratio_{c}']:.2f}" for c in CTX))
    print("OECD >5h / >7h, leisure on weekends:", f"{o.Ew_gt5:.1f}% / {o.Ew_gt7:.1f}%")

    _, _, Z = cluster_systems(X, args.k)
    if _cap and hasattr(_cap, "select_k"):
        ksel = _cap.select_k(Z.values)
        print("\nk selection:\n", ksel.to_string(index=False))
        ksel.to_csv(out / "04_time_use_k_selection.csv", index=False)
    res, prof, _ = cluster_systems(X, args.k)
    print(f"\nUsing k={args.k}:\n", prof[["n", "label"]].to_string())

    X.round(3).to_csv(out / "04_time_use_metrics.csv", index_label="system")
    ksel.to_csv(out / "04_time_use_k_selection.csv", index=False)
    res.round(3).to_csv(out / "04_time_use_clusters.csv", index_label="system")
    prof.round(3).to_csv(out / "04_time_use_cluster_profiles.csv", index_label="cluster")
    print(f"\nWrote 4 CSVs to {out}")


if __name__ == "__main__":
    main()
