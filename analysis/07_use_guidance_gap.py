#!/usr/bin/env python3
"""#7  The AI use-guidance gap.

Does school guidance on judging AI output keep pace with how many students use AI?

Measures (all country-level, from the chapter-4 workbook):
  use_any   % of students who used AI for at least one of the four schoolwork
            purposes (100 - table 4.55 "never used AI for any purpose")
  idx       AI-use index, mean (table 4.53)
  wk_*      % using AI at least weekly, per purpose (table 4.53)
  guid      % tasked at least sometimes with assessing AI-generated information
            (table 4.68 = 100 - "never" in table 4.67)
  guid_reg  % tasked often or very often (table 4.67)
  online    % tasked at least sometimes with assessing information found online
            (table 4.67), the non-AI benchmark
  lag       online - guid   (how much less schools ask students to judge AI output)
  gap       use_any - guid  (share using AI minus share taught to assess it)

Caveat: guid and use_any are country shares from different questions, not the same
students, so `gap` describes the system, not "users who got no guidance".

Usage:
    python analysis/07_use_guidance_gap.py [--xlsx PATH] [--out-dir DIR]
Outputs (default outputs/): 07_use_guidance_metrics.csv, 07_use_guidance_gap.png
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).parent))
from pisa_utils import OECD_ROW, Z95, Workbook, out_dir  # noqa: E402

PURPOSES = {
    "sum": "To summarise",
    "res": "To conduct preliminary",
    "draft": "To draft",
    "learn": "To help me learn",
}


def build_metrics(wb: Workbook) -> pd.DataFrame:
    X = pd.DataFrame(index=wb.raw.index)
    never_any, X["use_any_se"] = wb.pair("55", "All students")
    X["use_any"] = 100 - never_any
    X["idx"], X["idx_se"] = wb.pair("53", "Average - Mean index")
    for key, kw in PURPOSES.items():
        X[f"wk_{key}"] = (
            wb.est("53", kw, endswith="About once or twice a week - %")
            + wb.est("53", kw, endswith="Every day or almost every day - %")
        )
    X["guid"], X["guid_se"] = wb.pair("68", "All students")

    ai = lambda e: wb.est("67", "Artificial Intelligence", endswith=e)  # noqa: E731
    web = lambda e: wb.est("67", "information found online", endswith=e)  # noqa: E731
    X["guid_reg"] = ai("Often - %") + ai("Very often - %")
    X["online"] = 100 - web("Never or almost never - %")

    # Consistency check: 4.68 should equal 100 - "never" for the AI item in 4.67
    check = (X["guid"] - (100 - ai("Never or almost never - %"))).abs().max()
    if check > 0.05:
        sys.exit(f"Table 4.68 does not match 4.67 (max diff {check:.2f}); check definitions.")

    X["lag"] = X["online"] - X["guid"]
    X["gap"] = X["use_any"] - X["guid"]
    return X


def classify(v, se, ref):
    z = (v - ref) / se
    return "above" if z > Z95 else "below" if z < -Z95 else "similar"


def add_positions(S: pd.DataFrame, O: pd.Series) -> pd.DataFrame:
    S = S.copy()
    S["use_vs_oecd"] = [classify(v, s, O["use_any"]) for v, s in zip(S.use_any, S.use_any_se)]
    S["guid_vs_oecd"] = [classify(v, s, O["guid"]) for v, s in zip(S.guid, S.guid_se)]
    hi_use, hi_guid = S.use_any >= O["use_any"], S.guid >= O["guid"]
    S["quadrant"] = np.select(
        [hi_use & hi_guid, hi_use & ~hi_guid, ~hi_use & hi_guid],
        ["high use, high guidance", "high use, low guidance", "low use, high guidance"],
        default="low use, low guidance",
    )
    # both axes significantly different from the OECD average, in the "mismatch" direction
    S["sig_mismatch"] = (S.use_vs_oecd == "above") & (S.guid_vs_oecd == "below")
    S["sig_low_low"] = (S.use_vs_oecd == "below") & (S.guid_vs_oecd == "below")
    S["sig_low_high"] = (S.use_vs_oecd == "below") & (S.guid_vs_oecd == "above")
    return S


def ols(y, cols, S):
    A = np.column_stack([np.ones(len(S))] + [S[c] for c in cols])
    b, *_ = np.linalg.lstsq(A, S[y].values, rcond=None)
    resid = S[y].values - A @ b
    r2 = 1 - (resid ** 2).sum() / ((S[y] - S[y].mean()) ** 2).sum()
    return b, r2, resid


def prepare(wb: Workbook):
    """Return (X, S, O): all metrics, the systems with complete data (with quadrant
    flags and the residual of guidance on use), and the OECD-average row."""
    X = build_metrics(wb)
    O = X.loc[OECD_ROW]
    S = add_positions(X.drop(OECD_ROW).dropna(subset=["use_any", "guid", "online"]), O)
    S["resid"] = ols("guid", ["use_any"], S)[2]
    return X, S, O


def summary_stats(S: pd.DataFrame, O: pd.Series) -> dict:
    """Headline statistics used by the dashboard page (same numbers `report` prints)."""
    rho = {f"{a}~{b}": round(float(stats.spearmanr(S[a], S[b])[0]), 2)
           for a, b in [("use_any", "guid"), ("idx", "guid"), ("wk_learn", "guid"),
                        ("wk_draft", "guid"), ("wk_sum", "guid"), ("wk_res", "guid"),
                        ("online", "guid"), ("use_any", "lag")]}
    b, r2_use, _ = ols("guid", ["use_any"], S)
    _, r2_online, _ = ols("guid", ["online"], S)
    _, r2_both, _ = ols("guid", ["use_any", "online"], S)
    partial = np.corrcoef(ols("guid", ["online"], S)[2], ols("use_any", ["online"], S)[2])[0, 1]
    return {
        "n": int(len(S)),
        "oecd": {k: round(float(O[k]), 1) for k in ["use_any", "guid", "online", "lag", "gap", "wk_learn", "guid_reg"]},
        "rho": rho,
        "r2": {"use": round(r2_use, 2), "online": round(r2_online, 2), "both": round(r2_both, 2)},
        "partial": round(float(partial), 2),
        "ols": {"a": round(float(b[0]), 3), "b": round(float(b[1]), 3)},
        "resid_sd": round(float(S["resid"].std(ddof=2)), 1),
        "lag_pos": int((S.lag > 0).sum()), "lag_gt20": int((S.lag > 20).sum()),
        "lag_median": round(float(S.lag.median()), 1),
    }


def report(X: pd.DataFrame) -> pd.DataFrame:
    O = X.loc[OECD_ROW]
    S = X.drop(OECD_ROW).dropna(subset=["use_any", "guid", "online"])
    S = add_positions(S, O)
    print(f"Systems with complete data: {len(S)} (of {len(X) - 1})\n")

    print("OECD average")
    for k, lab in [("use_any", "used AI for >=1 purpose"), ("wk_learn", "AI weekly+ to help learn"),
                   ("guid", "tasked to assess AI output"), ("guid_reg", "  ...often/very often"),
                   ("online", "tasked to assess online info"), ("lag", "lag (online - AI)"),
                   ("gap", "gap (use - guidance)")]:
        print(f"  {lab:32s}{O[k]:6.1f}   systems: median {S[k].median():5.1f}  range {S[k].min():5.1f} to {S[k].max():5.1f}")

    print("\nSpearman rank correlations across systems")
    for a, b in [("use_any", "guid"), ("idx", "guid"), ("wk_learn", "guid"), ("wk_draft", "guid"),
                 ("wk_sum", "guid"), ("wk_res", "guid"), ("use_any", "guid_reg"),
                 ("online", "guid"), ("use_any", "lag")]:
        r, p = stats.spearmanr(S[a], S[b])
        print(f"  {a:9s} vs {b:9s} rho = {r:5.2f}   p = {p:.4f}")

    print("\nRegression of AI guidance (guid)")
    for cols in (["use_any"], ["online"], ["use_any", "online"]):
        b, r2, _ = ols("guid", cols, S)
        print(f"  ~ {' + '.join(cols):16s} R2 = {r2:.2f}   coefs = {np.round(b, 2).tolist()}")
    r_g = ols("guid", ["online"], S)[2]
    r_u = ols("use_any", ["online"], S)[2]
    print(f"  partial corr(use_any, guid | online) = {np.corrcoef(r_g, r_u)[0, 1]:.2f}")

    b, r2, resid = ols("guid", ["use_any"], S)
    S["resid"] = resid
    print(f"  residual SD from guid ~ use_any = {resid.std(ddof=2):.1f} pp")

    print("\nQuadrants vs OECD average (point estimates)")
    print(S["quadrant"].value_counts().to_string())
    for col, lab in [("sig_mismatch", "Significantly higher use AND lower guidance"),
                     ("sig_low_low", "Significantly lower use AND lower guidance"),
                     ("sig_low_high", "Significantly lower use AND higher guidance")]:
        names = S.index[S[col]].tolist()
        print(f"\n{lab} ({len(names)}):\n  " + ", ".join(names))

    print("\nGuidance below what use predicts (largest negative residuals)")
    print(S.nsmallest(8, "resid")[["use_any", "guid", "resid"]].round(1).to_string())
    print("\nGuidance above what use predicts")
    print(S.nlargest(6, "resid")[["use_any", "guid", "resid"]].round(1).to_string())

    print(f"\nLag (online - AI guidance): AI guidance is lower in {(S.lag > 0).sum()} of {len(S)} systems; "
          f"more than 20 pp lower in {(S.lag > 20).sum()}.")
    print(S.nlargest(6, "lag")[["online", "guid", "lag"]].round(1).to_string())
    print(S.nsmallest(3, "lag")[["online", "guid", "lag"]].round(1).to_string())
    return S


def plot(S: pd.DataFrame, O: pd.Series, path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    colors = {"high use, high guidance": "#8a8f99", "high use, low guidance": "#e34948",
              "low use, low guidance": "#eda100", "low use, high guidance": "#2a78d6"}
    fig, axes = plt.subplots(1, 2, figsize=(14, 6.2))

    ax = axes[0]
    for q, c in colors.items():
        d = S[S.quadrant == q]
        ax.scatter(d.use_any, d.guid, s=28, color=c, label=f"{q} ({len(d)})", alpha=0.9)
    ax.axvline(O["use_any"], color="#7b8494", ls="--", lw=1)
    ax.axhline(O["guid"], color="#7b8494", ls="--", lw=1)
    b, _, _ = ols("guid", ["use_any"], S)
    xs = np.array([S.use_any.min(), S.use_any.max()])
    ax.plot(xs, b[0] + b[1] * xs, color="#14181f", lw=1)
    offsets = [(5, 3), (-6, 8), (5, -11)]  # rotate label offsets to limit overlaps
    for i, n in enumerate(list(S.nsmallest(5, "resid").index) + list(S.nlargest(4, "resid").index)):
        ax.annotate(n.replace(" (China)", "").replace(" (17 of 27)", ""),
                    (S.loc[n, "use_any"], S.loc[n, "guid"]), fontsize=8,
                    xytext=offsets[i % 3], textcoords="offset points",
                    ha="right" if offsets[i % 3][0] < 0 else "left")
    ax.set(xlabel="% who used AI for at least one purpose", ylabel="% tasked with assessing AI output",
           title="AI use vs guidance (dashed = OECD average; line = OLS fit)")
    ax.legend(fontsize=8, loc="lower right", frameon=False)

    ax = axes[1]
    lo, hi = S[["online", "guid"]].min().min() - 2, S[["online", "guid"]].max().max() + 2
    ax.plot([lo, hi], [lo, hi], color="#7b8494", ls="--", lw=1)
    ax.scatter(S.online, S.guid, s=28, color="#2a78d6", alpha=0.85)
    ax.scatter([O["online"]], [O["guid"]], s=70, color="#14181f", marker="D", label="OECD average")
    for i, n in enumerate(list(S.nlargest(5, "lag").index) + list(S.nsmallest(2, "lag").index)):
        ax.annotate(n.replace(" (China)", ""), (S.loc[n, "online"], S.loc[n, "guid"]),
                    fontsize=8, xytext=offsets[i % 3], textcoords="offset points",
                    ha="right" if offsets[i % 3][0] < 0 else "left")
    ax.set(xlim=(lo, hi), ylim=(lo, hi), xlabel="% tasked with assessing information found online",
           ylabel="% tasked with assessing AI output",
           title="Is AI guidance as common as online-information guidance? (below the line = less)")
    ax.legend(fontsize=8, loc="upper left", frameon=False)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--xlsx", type=Path, default=None)
    ap.add_argument("--out-dir", type=Path, default=None)
    ap.add_argument("--no-plot", action="store_true")
    args = ap.parse_args()

    wb = Workbook(args.xlsx)
    X = build_metrics(wb)
    S = report(X)
    out = out_dir(args.out_dir)
    S.round(3).to_csv(out / "07_use_guidance_metrics.csv", index_label="system")
    print(f"\nWrote {out / '07_use_guidance_metrics.csv'}")
    if not args.no_plot:
        plot(S, X.loc[OECD_ROW], out / "07_use_guidance_gap.png")
        print(f"Wrote {out / '07_use_guidance_gap.png'}")


if __name__ == "__main__":
    main()
