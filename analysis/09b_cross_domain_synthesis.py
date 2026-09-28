#!/usr/bin/env python3
"""#9b  Cross-domain synthesis: how do the composite indices relate to each other?

Reads the composite indices from 09a (outputs/09_panel_composites.csv, or rebuilds the
panel if missing) and computes:
  - the full pairwise Spearman correlation matrix across the 9 composites + science
  - a curated set of partial correlations, to check whether a relationship survives
    controlling for an obvious confound (e.g. does resources associate with science
    once capacity is held constant?)
  - the largest positive and negative residuals from a same-domain composite's fit on
    a related one (e.g. countries with more capacity than their resources predict)

All correlations are Spearman (rank-based): composites are z-scores of skewed raw
indicators (see 9a), so rank correlation is the safer default over Pearson. Pairwise
deletion is used throughout, so the same-cell n varies; the report and CSV both carry n.

This is a country-level (ecological) analysis of up to 91 systems. A correlation
between two system-level averages says nothing about the relationship at the student
level, and with ~36 pairwise tests some correlations will be significant by chance.
No GDP/wealth control is available in this workbook, so any correlation involving
`resources` or `science` may partly reflect overall national income.

Usage:
    python analysis/09b_cross_domain_synthesis.py [--xlsx PATH] [--out-dir DIR]
Outputs (default outputs/):
    09b_correlations.csv         every composite pair: rho, p, n
    09b_partial_correlations.csv curated partial correlations: rho, n
    09b_residuals.csv            for each curated pair, each system's residual from the OLS fit
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from pisa_utils import Workbook, out_dir  # noqa: E402

COMPOSITE_LABELS = {
    "resources": "Resources", "capacity": "Capacity", "learning_time_school": "Learning time (school)",
    "leisure_at_school": "Leisure (school)", "leisure_outside_school": "Leisure (outside school)",
    "distraction": "Distraction", "rules": "Device rules", "ai_use": "AI use", "ai_guidance": "AI guidance",
    "science": "Science performance",
}

# Partial correlations worth checking specifically, each as (x, y, control, why).
# rho(x,y|z) uses the standard rank-based partial-correlation formula.
PARTIALS = [
    ("resources", "science", "capacity",
     "Does resourcing associate with science performance beyond what capacity explains?"),
    ("capacity", "science", "resources",
     "Does school capacity associate with science performance beyond raw resources?"),
    ("ai_use", "ai_guidance", "resources",
     "Does AI use still track AI guidance once resourcing is held constant? (#7 found this at the raw level)"),
    ("ai_use", "ai_guidance", "capacity",
     "Same check, controlling for capacity instead of resources"),
    ("leisure_at_school", "distraction", "rules",
     "Does in-school leisure device use still associate with distraction once device rules are held constant?"),
    ("resources", "ai_use", "science",
     "Is the resources-AI use relationship just a performance effect?"),
]

# Residual pairs worth surfacing: (predictor, outcome, description)
RESIDUAL_PAIRS = [
    ("resources", "capacity", "Systems with more/less reported capacity than their resources predict"),
    ("ai_use", "ai_guidance", "Systems with more/less AI guidance than their AI-use level predicts"),
]


def load_composites(xlsx: Path | None, out: Path) -> pd.DataFrame:
    path = out / "09_panel_composites.csv"
    if path.exists():
        return pd.read_csv(path, index_col=0)
    print(f"{path} not found; rebuilding the panel from the workbook.")
    import importlib.util
    spec = importlib.util.spec_from_file_location("cross_domain_panel", HERE / "09_cross_domain_panel.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    table_i1 = pd.read_csv(HERE.parent / "data" / "pisa2025_table_I1.csv", index_col=0)
    P = mod.build_raw(Workbook(xlsx), table_i1)
    return mod.build_composites(P)


def correlation_matrix(C: pd.DataFrame) -> pd.DataFrame:
    rows = []
    cols = list(C.columns)
    for i, a in enumerate(cols):
        for b in cols[i + 1:]:
            d = C[[a, b]].dropna()
            if len(d) < 8:
                continue
            r, p = stats.spearmanr(d[a], d[b])
            rows.append({"var1": a, "var2": b, "n": len(d), "rho": round(float(r), 3), "p": round(float(p), 4)})
    return pd.DataFrame(rows).sort_values("rho", key=lambda s: -s.abs()).reset_index(drop=True)


def rank_partial(x: pd.Series, y: pd.Series, z: pd.Series) -> tuple[float, int]:
    """Spearman partial correlation of x and y controlling for z (ranks + Pearson formula)."""
    d = pd.concat([x, y, z], axis=1).dropna()
    r = d.rank().corr(method="pearson")
    rxy, rxz, ryz = r.iloc[0, 1], r.iloc[0, 2], r.iloc[1, 2]
    denom = np.sqrt((1 - rxz ** 2) * (1 - ryz ** 2))
    return (float("nan") if denom == 0 else round((rxy - rxz * ryz) / denom, 3)), len(d)


def partials_table(C: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for x, y, z, why in PARTIALS:
        rho0 = stats.spearmanr(*C[[x, y]].dropna().T.values)[0] if len(C[[x, y]].dropna()) else float("nan")
        rho_p, n = rank_partial(C[x], C[y], C[z])
        rows.append({"x": x, "y": y, "control": z, "rho_unadjusted": round(float(rho0), 3),
                     "rho_partial": rho_p, "n": n, "note": why})
    return pd.DataFrame(rows)


def ols_resid(y: pd.Series, x: pd.Series) -> pd.Series:
    d = pd.concat([x, y], axis=1).dropna()
    b = np.polyfit(d.iloc[:, 0], d.iloc[:, 1], 1)
    return d.iloc[:, 1] - (b[0] * d.iloc[:, 0] + b[1])


def residuals_table(C: pd.DataFrame) -> pd.DataFrame:
    frames = []
    for x, y, _ in RESIDUAL_PAIRS:
        r = ols_resid(C[y], C[x]).rename(f"resid_{y}_on_{x}")
        frames.append(r)
    return pd.concat(frames, axis=1)


def report(C: pd.DataFrame, corr: pd.DataFrame, part: pd.DataFrame, resid: pd.DataFrame) -> None:
    n_sys = len(C)
    print(f"Systems in the composite panel: {n_sys}\n")
    print("Coverage per composite:")
    print(C.notna().sum().to_string())

    print(f"\nAll pairwise Spearman correlations ({len(corr)} pairs), strongest first:")
    for _, r in corr.iterrows():
        flag = "*" if r.p < 0.05 else " "
        print(f"  {flag} {COMPOSITE_LABELS[r.var1]:24s} vs {COMPOSITE_LABELS[r.var2]:24s} "
              f"rho={r.rho:+.2f}  p={r.p:.4f}  n={r.n}")
    n_sig = int((corr.p < 0.05).sum())
    print(f"  {n_sig} of {len(corr)} pairs significant at p<0.05 "
          f"(expect ~{0.05 * len(corr):.1f} by chance alone)")

    print("\nCurated partial correlations")
    for _, r in part.iterrows():
        print(f"  {COMPOSITE_LABELS[r.x]} vs {COMPOSITE_LABELS[r.y]} | control {COMPOSITE_LABELS[r.control]}: "
              f"unadjusted rho={r.rho_unadjusted:+.2f} -> partial rho={r.rho_partial:+.2f}  (n={r.n})")
        print(f"      {r.note}")

    print("\nResidual outliers")
    for x, y, desc in RESIDUAL_PAIRS:
        col = f"resid_{y}_on_{x}"
        s = resid[col].dropna().sort_values()
        print(f"  {desc}")
        print(f"    Lower than predicted: {', '.join(f'{n} ({v:+.2f})' for n, v in s.head(5).items())}")
        print(f"    Higher than predicted: {', '.join(f'{n} ({v:+.2f})' for n, v in s.tail(5).items())}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--xlsx", type=Path, default=None)
    ap.add_argument("--out-dir", type=Path, default=None)
    args = ap.parse_args()

    out = out_dir(args.out_dir)
    C = load_composites(args.xlsx, out)
    corr = correlation_matrix(C)
    part = partials_table(C)
    resid = residuals_table(C)
    report(C, corr, part, resid)

    corr.to_csv(out / "09b_correlations.csv", index=False)
    part.to_csv(out / "09b_partial_correlations.csv", index=False)
    resid.round(3).to_csv(out / "09b_residuals.csv", index_label="system")
    print(f"\nWrote {out / '09b_correlations.csv'}, {out / '09b_partial_correlations.csv'}, "
          f"{out / '09b_residuals.csv'}")


if __name__ == "__main__":
    main()
