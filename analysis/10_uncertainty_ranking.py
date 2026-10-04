#!/usr/bin/env python3
"""#10  Uncertainty-aware ranking: confidence intervals, rank ranges, significance tests
and inverse-variance weighting, for ten headline indicators.

Every Chapter 4 country table publishes a standard error next to each estimate, but the
report ranks and compares systems on the point estimates alone. For each indicator this
computes, over the systems that have both an estimate and a standard error:

  - 95% confidence intervals (est +/- 1.96 SE)
  - a rank range: 20,000 draws of each system's estimate from Normal(est, SE^2), ranked
    each time; the 2.5th and 97.5th percentiles of each system's rank (systems are
    independent samples, so independent draws are appropriate)
  - pairwise z-tests, z = (a - b) / sqrt(se_a^2 + se_b^2); how many of the n(n-1)/2
    pairs, and how many neighbours in the ranking, can actually be told apart, both
    unadjusted (|z| > 1.96) and Bonferroni-adjusted for the n-1 comparisons made when one
    system is compared with all others
  - pooled means: unweighted, fixed-effect inverse-variance (weight 1/SE^2), and
    DerSimonian-Laird random-effects (weight 1/(SE^2 + tau^2)), with Cochran's Q / I^2

What to watch for (the reason this page exists):
  * The weights are only as good as the SEs. School-level tables (capacity, resources,
    computers) have near-zero SEs for systems that survey almost every school (Luxembourg,
    Macao, Malta, Brunei Darussalam, ...): sampling error is ~0, so those systems look
    certain and dominate any inverse-variance mean. A published SE is sampling error
    only; it says nothing about measurement or definitional differences.
  * I^2 is ~99-100% for every indicator: nearly all variation between systems is real,
    not sampling noise. The fixed-effect model (one common true value) is therefore
    wrong for "the average system", and inverse-variance weighting should not be used
    for that. Random-effects weights are shown because they behave sensibly here.
  * z-tests assume independent systems and normal estimates, and say nothing about
    whether a difference matters in practice. 4,000+ pairwise tests per indicator means
    some unadjusted "significant" pairs are false positives; the Bonferroni column is
    deliberately strict.
  * Rank 1 = highest value. For "never used AI" that is the LEAST AI use.

Usage:
    python analysis/10_uncertainty_ranking.py [--xlsx PATH] [--out-dir DIR]
Outputs (default outputs/): 10_uncertainty_ranks.csv, 10_uncertainty_summary.csv
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from pisa_utils import OECD_ROW, Workbook, out_dir  # noqa: E402

N_SIM, SEED = 20000, 20261002
FOCUS = ["Malta", "Luxembourg", "Macao (China)"]
# key: (label, table, keyword, endswith, format, source). endswith None = first matching column.
IND = {
    "ai_index": ("AI-use index (mean)", "53", "Average - Mean index", None, "idx", "students"),
    "ai_never": ("Never used AI for any purpose (%)", "55", "All students", "All students - %", "pct", "students"),
    "no_draft": ("Never use AI to draft texts (%)", "58", "All students", "All students - %", "pct", "students"),
    "no_learn": ("Never use AI to help them learn (%)", "59", "All students", "All students - %", "pct", "students"),
    "assess_ai": ("Asked to assess AI output (%)", "68", "All students", "All students - %", "pct", "students"),
    "distraction": ("Peers distracted by digital devices in most or every science lesson (%)", "43", "All students", "All students - %", "pct", "students"),
    "capacity": ("School capacity to teach digitally (index)", "14", "Average - Mean index", None, "idx", "schools"),
    "lack_res": ("Schools lacking digital resources (%)", "7", "Average - %", None, "pct", "schools"),
    "poor_res": ("Schools with inadequate digital resources (%)", "8", "Average - %", None, "pct", "schools"),
    "computers": ("Computer availability (mean ratio)", "1", "Average - Mean ratio", None, "ratio", "schools"),
}


def pooled(e: pd.Series, s: pd.Series) -> dict:
    w = 1 / s**2
    mu = (w * e).sum() / w.sum()
    Q, df = (w * (e - mu) ** 2).sum(), len(e) - 1
    tau2 = max(0.0, (Q - df) / (w.sum() - (w**2).sum() / w.sum()))
    wr = 1 / (s**2 + tau2)
    sh = (w / w.sum()).sort_values(ascending=False)
    return {
        "mean_unweighted": e.mean(), "mean_fe": mu, "se_fe": np.sqrt(1 / w.sum()),
        "mean_re": (wr * e).sum() / wr.sum(), "se_re": np.sqrt(1 / wr.sum()), "tau": np.sqrt(tau2),
        "I2": max(0.0, (Q - df) / Q) * 100, "n_eff": w.sum() ** 2 / (w**2).sum(),
        "top_name": sh.index[0], "top_share": 100 * sh.iloc[0],
        "top3": [(n, round(100 * v, 1)) for n, v in sh.head(3).items()],
        "focus": {f: round(100 * sh.get(f, np.nan), 1) for f in FOCUS if f in sh.index},
        "shares": {n: round(100 * v, 2) for n, v in sh.items()},
    }


def analyse(wb: Workbook, key: str, seed: int = SEED):
    label, tbl, kw, end, fmt, src = IND[key]
    e, s = wb.pair(tbl, kw, endswith=end) if end else wb.pair(tbl, kw)
    e, s = e.drop(OECD_ROW), s.drop(OECD_ROW)
    ok = e.notna() & s.notna()
    e, s = e[ok], s[ok]
    assert (s > 0).all(), f"{key}: non-positive SE"
    n = len(e)
    rng = np.random.default_rng(seed)
    draws = rng.normal(e.values, s.values, size=(N_SIM, n))
    rk = (-draws).argsort(axis=1).argsort(axis=1) + 1  # rank 1 = highest value
    D = pd.DataFrame({
        "est": e, "se": s, "lo": e - 1.96 * s, "hi": e + 1.96 * s,
        "rank": e.rank(ascending=False, method="min").astype(int),
        "rank_lo": np.percentile(rk, 2.5, axis=0), "rank_hi": np.percentile(rk, 97.5, axis=0),
        "rank_med": np.median(rk, axis=0),
    })
    est, se = e.values, s.values
    Z = np.abs(est[:, None] - est[None, :]) / np.sqrt(se[:, None] ** 2 + se[None, :] ** 2)
    iu = np.triu_indices(n, 1)
    zb = norm.isf(0.025 / (n - 1))
    order = np.argsort(-est)
    adj = Z[order[:-1], order[1:]]
    stats = {
        "n": n, "z_bonf": zb,
        "pairs_sig": 100 * (Z[iu] > 1.96).mean(), "pairs_sig_bonf": 100 * (Z[iu] > zb).mean(),
        "adjacent_sig": 100 * (adj > 1.96).mean(), "adjacent_sig_bonf": 100 * (adj > zb).mean(),
        "median_rank_width": float((D.rank_hi - D.rank_lo).median()),
        "contain": 100 * ((D["rank"] >= D.rank_lo) & (D["rank"] <= D.rank_hi)).mean(),
        "tiny_se": [nm for nm in D.index if D.se[nm] < 0.1 * D.se.median()],
        **pooled(e, s),
    }
    return D, stats, (label, fmt, src, tbl)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--xlsx", type=Path, default=None)
    ap.add_argument("--out-dir", type=Path, default=None)
    args = ap.parse_args()
    wb, out = Workbook(args.xlsx), out_dir(args.out_dir)
    long, summ = [], []
    for k in IND:
        D, st, (label, fmt, src, tbl) = analyse(wb, k)
        print(f"\n{label} [{src}, table 4.{tbl}] n={st['n']}")
        print(f"  pairs distinguishable: {st['pairs_sig']:.0f}% unadjusted, {st['pairs_sig_bonf']:.0f}% Bonferroni (|z|>{st['z_bonf']:.2f}); "
              f"neighbours in ranking: {st['adjacent_sig']:.0f}% / {st['adjacent_sig_bonf']:.0f}%; median 95% rank range width {st['median_rank_width']:.0f}")
        print(f"  mean: unweighted {st['mean_unweighted']:.2f}, inverse-variance {st['mean_fe']:.2f}, random-effects {st['mean_re']:.2f}; "
              f"I2={st['I2']:.0f}%, effective n={st['n_eff']:.1f}; top IV weight: {st['top_name']} {st['top_share']:.0f}%")
        if st["tiny_se"]:
            print("  near-census (SE < 10% of median):", st["tiny_se"])
        assert st["contain"] > 90, f"{k}: rank ranges do not contain the observed rank"
        long.append(D.assign(indicator=k).reset_index(names="system"))
        summ.append({"indicator": k, "label": label, **{a: b for a, b in st.items() if a not in ("shares", "top3", "focus", "tiny_se")},
                     "tiny_se": "; ".join(st["tiny_se"])})
    pd.concat(long).round(4).to_csv(out / "10_uncertainty_ranks.csv", index=False)
    pd.DataFrame(summ).round(4).to_csv(out / "10_uncertainty_summary.csv", index=False)
    print(f"\nWrote 2 CSVs to {out}")


if __name__ == "__main__":
    main()
