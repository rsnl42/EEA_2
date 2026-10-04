#!/usr/bin/env python3
"""#6  AI use portfolios: four school purposes x five frequency levels (Table 4.53).

Table 4.53 gives, per system, the % of students using AI for each of four purposes
(summarise a text, preliminary research, draft texts, help me learn) at five frequency
levels (never or almost never, once or twice a year / a month / a week, daily or almost
daily), plus the AI-use index. Tables 4.56-4.59 are NOT frequency distributions: each is
the "never or almost never" share for one purpose split by student/school group (4.56
summarise, 4.57 research, 4.58 draft, 4.59 learn; their "All students" column equals
4.53's never column exactly, asserted below). Those group splits are #1's territory, so
this analysis builds on 4.53 only. It computes:

  - draft texts vs help me learn: % weekly or more and % never, per system, and the gap
  - adoption vs intensity, per purpose:
      adoption  = 100 - % never or almost never (used at least once or twice a year)
      intensity = % weekly-or-more AS A SHARE OF USERS (weekly+ / adoption)
  - country typologies: Ward clustering on adoption and intensity for all four purposes

Decisions worth knowing:
  * "Draft texts" is only a proxy for offloading: the survey records how often AI is used
    for the purpose, not whether the student did the thinking. The page says so.
  * Gaps (draft minus learn) come from the same students, so sqrt(se1^2 + se2^2)
    overstates the true SE (conservative); a gap is "clear" only if its 95% interval
    excludes zero. Weekly-or-more sums two bands, likewise conservative.
    Intensity-among-users is a ratio of two reported figures and carries no CI.
  * Clustering features are the 8 adoption/intensity measures (z-scored); labels summarise
    the cluster's mean z for overall adoption and overall intensity. Tried first:
    weekly+ x4 (stability 0.63 at k=3) and level/intensity/balance summaries (0.34,
    unstable). Adoption + intensity gave the most stable k=3 (sil ~0.29, stability ~0.70).
    Even so the structure is weak: treat clusters as broad summaries.
  * 85 of 91 systems have data; the other 6 have no 4.53 values at all.

Usage:
    python analysis/06_ai_use_portfolios.py [--xlsx PATH] [--k N] [--out-dir DIR]
Outputs (default outputs/): 06_ai_metrics.csv, 06_ai_k_selection.csv,
    06_ai_clusters.csv, 06_ai_cluster_profiles.csv
"""
import argparse
import importlib.util
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import fcluster, linkage
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_samples

warnings.simplefilter("ignore", pd.errors.PerformanceWarning)
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from pisa_utils import OECD_ROW, Workbook, out_dir  # noqa: E402

try:
    _spec = importlib.util.spec_from_file_location("cap03", HERE / "03_capacity_bottlenecks.py")
    _cap = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_cap)
except Exception:
    _cap = None

PURPOSE = {  # key: (workbook keyword, display label, group-split table of the never share)
    "sum": ("To summarise a text", "Summarise a text", "56"),
    "res": ("To conduct preliminary research", "Preliminary research on a topic", "57"),
    "draft": ("To draft texts", "Draft texts for writing assignments", "58"),
    "learn": ("To help me learn", "Help me learn", "59"),
}
LEVEL = {"never": "Never or almost never - %", "yr": "once or twice a year - %", "mo": "once or twice a month - %",
         "wk": "once or twice a week - %", "day": "Every day or almost every day - %"}
SHORT = {"sum": "summarising", "res": "research", "draft": "drafting", "learn": "learning"}


def extract(wb: Workbook, table_i1=None) -> pd.DataFrame:
    X = pd.DataFrame(index=wb.raw.index)
    for p, (kw, _, grp) in PURPOSE.items():
        P, SE = {}, {}
        for lv, end in LEVEL.items():
            P[lv], SE[lv] = wb.pair("53", kw, endswith=end)
            X[f"{p}_{lv}"], X[f"{p}_{lv}_se"] = P[lv], SE[lv]
        ok = pd.concat(P.values(), axis=1).notna().all(axis=1)
        assert ((sum(P.values())[ok] - 100).abs() < 0.3).all(), f"{p}: levels do not sum to 100"
        chk = wb.est(grp, "All students", endswith="All students - %")
        assert (chk[ok] - P["never"][ok]).abs().max() < 0.05, f"table 4.{grp} is not the never share for {p}"
        X[f"{p}_wk"] = P["wk"] + P["day"]
        X[f"{p}_wk_se"] = np.hypot(SE["wk"], SE["day"])
        X[f"{p}_adopt"], X[f"{p}_adopt_se"] = 100 - P["never"], SE["never"]
        X[f"{p}_intens"] = 100 * X[f"{p}_wk"] / X[f"{p}_adopt"]
    X["gap_wk"] = X["draft_wk"] - X["learn_wk"]
    X["gap_wk_se"] = np.hypot(X["draft_wk_se"], X["learn_wk_se"])
    X["gap_never"] = X["draft_never"] - X["learn_never"]
    X["gap_never_se"] = np.hypot(X["draft_never_se"], X["learn_never_se"])
    X["idx"] = wb.est("53", "Average - Mean index")
    if table_i1 is not None:
        X["science"] = table_i1["science"].reindex(X.index)
    return X


FEATS = [f"{p}_{m}" for m in ("adopt", "intens") for p in PURPOSE]
def name_cluster(z: pd.Series) -> str:
    """Label from z-scores (a real zero point), never raw percentages: overall adoption
    (mean z of the four adoption features) and overall intensity among users."""
    word = lambda v: "high" if v > 0.3 else "low" if v < -0.3 else "average"  # noqa: E731
    ad = z[[f"{q}_adopt" for q in PURPOSE]].mean()
    it = z[[f"{q}_intens" for q in PURPOSE]].mean()
    return f"{word(ad)} adoption, {word(it)} intensity among users"


def cluster_systems(X: pd.DataFrame, k: int):
    S = X.drop(OECD_ROW)[FEATS].dropna()
    Z = (S - S.mean()) / S.std(ddof=0)
    lab = fcluster(linkage(Z.values, "ward"), k, "maxclust")
    pcs = PCA(n_components=2, random_state=0).fit_transform(Z.values)
    res = S.copy()
    res["cluster"], res["silhouette"] = lab, silhouette_samples(Z.values, lab).round(3)
    res["pc1"], res["pc2"] = pcs[:, 0], pcs[:, 1]
    if "science" in X.columns:
        res["science"] = X["science"].reindex(res.index)
    zm = Z.assign(cluster=lab).groupby("cluster")[FEATS].mean()
    prof = res.groupby("cluster")[FEATS].mean()
    prof["n"] = res.groupby("cluster").size()
    if "science" in res.columns:
        prof["science_mean"] = res.groupby("cluster")["science"].mean().round(0)
    prof["label"] = zm.apply(name_cluster, axis=1)
    prof["systems"] = res.groupby("cluster").apply(lambda d: ", ".join(sorted(d.index)))
    return res, prof, Z


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--xlsx", type=Path, default=None)
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--out-dir", type=Path, default=None)
    args = ap.parse_args()
    wb, out = Workbook(args.xlsx), out_dir(args.out_dir)
    p = HERE.parent / "data" / "pisa2025_table_I1.csv"
    X = extract(wb, pd.read_csv(p, index_col=0) if p.exists() else None)
    S, o = X.drop(OECD_ROW), X.loc[OECD_ROW]
    have = S["draft_wk"].notna()
    print(f"Coverage: {int(have.sum())} of {len(S)} systems; missing: {S.index[~have].tolist()}")
    print("\nOECD average, % never / % weekly+ / adoption / intensity among users:")
    for q, (_, lab, _) in PURPOSE.items():
        print(f"  {lab:38s} {o[f'{q}_never']:5.1f} / {o[f'{q}_wk']:5.1f} / {o[f'{q}_adopt']:5.1f} / {o[f'{q}_intens']:5.1f}")
    d = S.loc[have]
    clear_d = int((d.gap_wk > 1.96 * d.gap_wk_se).sum())
    clear_l = int((d.gap_wk < -1.96 * d.gap_wk_se).sum())
    print(f"\nDraft minus learn, % weekly+: OECD {o.gap_wk:+.1f} pp. Clearly more drafting than learning in "
          f"{clear_d} systems, clearly more learning than drafting in {clear_l}, unclear in {len(d) - clear_d - clear_l}.")
    print("Systems where drafting is at least as common as learning (weekly+):", d.index[d.gap_wk >= 0].tolist())

    _, _, Z = cluster_systems(X, args.k)
    ksel = _cap.select_k(Z.values)
    print("\nk selection:\n", ksel.to_string(index=False))
    res, prof, _ = cluster_systems(X, args.k)
    print(f"\nUsing k={args.k}:\n", prof[["n", "label"]].to_string())

    X[X["draft_wk"].notna()].round(3).to_csv(out / "06_ai_metrics.csv", index_label="system")
    ksel.to_csv(out / "06_ai_k_selection.csv", index=False)
    res.round(3).to_csv(out / "06_ai_clusters.csv", index_label="system")
    prof.round(3).to_csv(out / "06_ai_cluster_profiles.csv", index_label="cluster")
    print(f"\nWrote 4 CSVs to {out}")


if __name__ == "__main__":
    main()
