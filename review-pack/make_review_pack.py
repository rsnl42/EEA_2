#!/usr/bin/env python3
"""Build review-pack/claims_register.csv: one row per headline number quoted by the dashboards.

Every value is read from outputs/*.csv (never typed), with the OECD table, the workbook columns
to check it against, and the script that produced it. Run the analysis scripts first.
    python make_review_pack.py
"""
import csv
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
O = ROOT / "outputs"
OUT = ROOT / "review-pack"
SHEET = "Digital & AI"
R = []


def add(dash, claim, value, tables, verify, script, caveat=""):
    R.append({"dashboard": dash, "claim": claim, "value": value, "oecd_tables": tables,
              "how_to_verify_in_workbook": verify, "produced_by": script, "caveat": caveat})


rd = lambda f, **k: pd.read_csv(O / f, **k)  # noqa: E731
f1 = lambda v: f"{v:.1f}"  # noqa: E731

# ---- #1 equity gaps
s = rd("01_equity_gap_summary.csv")
for b, o, lab in [("Student SES (advantaged - disadvantaged)", "AI-use index", "advantaged minus disadvantaged students, AI-use index"),
                  ("Student SES (advantaged - disadvantaged)", "Tasked with assessing AI-generated information", "advantaged minus disadvantaged students, % asked to assess AI output"),
                  ("Student SES (advantaged - disadvantaged)", "Not using AI to help them learn", "advantaged minus disadvantaged students, % never using AI to learn"),
                  ("Gender (boys - girls)", "AI-use index", "boys minus girls, AI-use index")]:
    r = s[(s.breakdown == b) & (s.outcome == o)].iloc[0]
    add("#1 Equity gaps", f"OECD average gap, {lab}", f"{r.oecd_gap:+.2f} (z={r.oecd_z:.1f}); clearly positive in {r.n_sig_positive}, clearly negative in {r.n_sig_negative} of {r.n_systems} systems",
        "4.54 / 4.55-4.59 / 4.68 by group", "OECD-average row, the 'Dif.' column for the group pair; per-system counts need each system's own Dif and S.E.", "analysis/01_equity_gaps.py",
        "Gap taken from the OECD's published Dif. column (orientation verified for all 72 cells); OECD gap is an average of country gaps.")

# ---- #2 infrastructure
d = rd("02_infrastructure_gap_summary.csv")
for t, dim, lab in [(7, "type", "private minus public: schools lacking digital resources (pp)"), (8, "type", "private minus public: inadequate digital resources (pp)")]:
    r = d[(d.table == t) & (d.dimension == dim)].iloc[0]
    add("#2 Infrastructure", f"OECD average gap, {lab}", f"{r.oecd_gap:+.1f} pp; favours private in {r.n_sig_expected}, public in {r.n_sig_flipped}, no clear difference in {r.n_not_sig} of {r.n_systems} systems",
        f"4.{t}", "'Private - Public dif.' column and its S.E. for each system; count |Dif/S.E.| > 1.96", "analysis/02_infrastructure_divides.py")
r = d[(d.table == 1) & (d.dimension == "ses")].iloc[0]
add("#2 Infrastructure", "Computer availability: poorer schools clearly ahead vs richer schools clearly ahead (systems)", f"{r.n_sig_flipped} vs {r.n_sig_expected} of {r.n_systems}",
    "4.1", "SES 'Dif.' and S.E. columns, mean ratio", "analysis/02_infrastructure_divides.py", "A per-student ratio: small schools can look well supplied.")

# ---- #3 capacity
it = rd("03_capacity_items.csv", index_col=0)
oecd = it.loc["OECD average"]
w = rd("03_capacity_weakest_link.csv")
cols = sorted(set(w.weakest_absolute))  # the 12 items (official_index is not an item)
low = oecd[cols].astype(float).sort_values().index[0]
add("#3 Capacity", "Lowest OECD-average sufficiency item", f"{low}: {oecd[low]:.1f}%", "4.14", "OECD-average row, the 12 'agree/strongly agree' % columns; take the minimum", "analysis/03_capacity_bottlenecks.py")
add("#3 Capacity", f"Systems where '{low}' is the weakest item (absolute)", f"{(w.weakest_absolute == low).sum()} of {len(w)}", "4.14", "For each system find the lowest of the 12 columns", "analysis/03_capacity_bottlenecks.py", "Sweden has 11 items (no curriculum-fit value) but is still ranked.")

# ---- #4 time use
t4 = rd("04_time_use_metrics.csv", index_col=0)
o4 = t4.loc["OECD average"]
add("#4 Time use", "OECD weekday hours: learning vs leisure on devices", f"{o4.wd_learn:.2f} h vs {o4.wd_leisure:.2f} h (weekday total {o4.wd_total:.2f} h; weekend day {o4.we_total:.2f} h)", "4.21",
    "OECD row: add 'at school' + 'before and after school' hours for learning, and for leisure", "analysis/04_time_use_budgets.py", "Sum of two reported means; the OECD text adds them the same way.")
add("#4 Time use", "OECD learning-to-leisure ratio: at school / before-after school / weekend", f"{o4.ratio_s:.2f} / {o4.ratio_b:.2f} / {o4.ratio_w:.2f}", "4.21", "Learning mean hours divided by leisure mean hours, per context", "analysis/04_time_use_budgets.py", "Ratio of two means; no confidence interval.")
add("#4 Time use", "OECD % of students above 5 hours on a weekend day, leisure", f"{o4.Ew_gt5:.1f}%", "4.21", "OECD row: '5-7 hours' % plus 'more than 7 hours' %, leisure on weekends", "analysis/04_time_use_budgets.py")
S4 = t4.drop("OECD average")
add("#4 Time use", "Highest learning-to-leisure ratio at school", f"{S4.ratio_s.idxmax()}: {S4.ratio_s.max():.2f}", "4.21", "Divide learning-at-school mean by leisure-at-school mean for every system", "analysis/04_time_use_budgets.py")

# ---- #5 leisure
t5 = rd("05_leisure_metrics.csv", index_col=0)
o5 = t5.loc["OECD average"]; S5 = t5.drop("OECD average")
acts = ["social", "web", "comm", "create", "info", "games", "tutorial"]
big = max(acts, key=lambda a: o5[f"{a}_shift_gt3"])
clear = int((S5[f"{big}_shift_gt3"].abs() > 1.96 * S5[f"{big}_shift_gt3_se"]).sum())
add("#5 Leisure", f"Largest OECD weekday-to-weekend rise in students above 3 h: {big}", f"{o5[f'{big}_shift_gt3']:+.1f} pp; clear in {clear} of {len(S5)} systems", "4.37 and 4.40",
    "For the activity: sum the three top bands (3-5h, 5-7h, >7h) in each table, subtract weekday from weekend", "analysis/05_leisure_profiles.py", "Interval is conservative (same students in both tables).")
add("#5 Leisure", "OECD shift above 3 h, creating or editing own content", f"{o5['create_shift_gt3']:+.1f} pp", "4.37 and 4.40", "As above for 'create or edit' ", "analysis/05_leisure_profiles.py")
add("#5 Leisure", "OECD passive-to-creative estimated-hours ratio, weekday", f"{o5.pc_ratio_wd:.1f} : 1", "4.37", "Midpoint-hours (0, 0.5, 2, 4, 6, 8) of social + web browsing divided by create/edit", "analysis/05_leisure_profiles.py",
    "Judgement call on grouping; hours are midpoint approximations and overlapping activities sum to far more than a day.")
add("#5 Leisure", "Coverage", f"{len(S5)} of 91 systems (all-or-nothing, same set in both tables)", "4.37 and 4.40", "Count systems with non-blank cells", "analysis/05_leisure_profiles.py", "Covered systems average higher in science than uncovered.")

# ---- #6 AI portfolios
t6 = rd("06_ai_metrics.csv", index_col=0)
o6 = t6.loc["OECD average"]; S6 = t6.drop("OECD average")
add("#6 AI portfolios", "OECD % weekly or more: help me learn vs draft texts", f"{o6.learn_wk:.1f}% vs {o6.draft_wk:.1f}% (gap {o6.gap_wk:+.1f} pp)", "4.53", "OECD row: 'once or twice a week' + 'every day' for each purpose", "analysis/06_ai_use_portfolios.py")
add("#6 AI portfolios", "Systems where weekly-or-more use for learning exceeds drafting", f"{int((S6.gap_wk < 0).sum())} of {len(S6)}; gap range {S6.gap_wk.min():.1f} to {S6.gap_wk.max():.1f} pp", "4.53", "Per system, weekly+ drafting minus weekly+ learning", "analysis/06_ai_use_portfolios.py", "Drafting is only a proxy for offloading.")
pr = rd("06_ai_cluster_profiles.csv", index_col=0)
add("#6 AI portfolios", "Three patterns: sizes and mean science", "; ".join(f"pattern {c}: n={int(r.n)}, science {r.science_mean:.0f}, {r.label}" for c, r in pr.iterrows()), "4.53 + Table I.1", "Cluster membership is in outputs/06_ai_clusters.csv", "analysis/06_ai_use_portfolios.py", "Weak structure (silhouette ~0.29): patterns differ mainly in level.")

# ---- #7 use vs guidance
m7 = rd("07_use_guidance_metrics.csv")
q = m7.quadrant.value_counts().to_dict()
rho = m7[["use_any", "guid"]].corr(method="spearman").iloc[0, 1]
add("#7 Use vs guidance", "Quadrant counts (use and guidance vs OECD average)", "; ".join(f"{k}: {v}" for k, v in q.items()), "4.55 and 4.68", "Per system compare 100 minus 'never used AI' (4.55) and the share asked to assess AI output (4.68) with the OECD row", "analysis/07_use_guidance_gap.py", "Each system is compared with the OECD average using only its own S.E.")
add("#7 Use vs guidance", "Spearman correlation between AI use and guidance across systems", f"{rho:.2f} (n={len(m7)})", "4.55 and 4.68", "Rank both columns across systems and correlate", "analysis/07_use_guidance_gap.py", "Country-level association, not causal.")

# ---- #8 policy
pc = rd("08_policy_outcome_correlations.csv")
top = pc.reindex(pc.rho.abs().sort_values(ascending=False).index).head(3)
add("#8 Policy", "Strongest country-level policy/outcome correlations", "; ".join(f"{r.policy_var} vs {r.outcome}: rho={r.rho:.2f}, p{'<0.001' if r.p < 0.001 else '=' + format(r.p, '.3f')}, n={int(r.n)}" for r in top.itertuples()), "4.47 policy items; outcome tables listed in the script", "Rank-correlate the policy % across systems with the outcome %", "analysis/08_policy_typologies.py",
    f"{len(pc)} correlations tested; about {0.05 * len(pc):.0f} would reach p<0.05 by chance.")

# ---- #9 cross-domain
c9 = rd("09b_correlations.csv")
sig = int((c9.p < 0.05).sum())
rs = c9[(c9.var1.isin(["resources", "science"])) & (c9.var2.isin(["resources", "science"]))].iloc[0]
ai = c9[((c9.var1 == "ai_use") & (c9.var2 == "science")) | ((c9.var2 == "ai_use") & (c9.var1 == "science"))].iloc[0]
add("#9 Cross-domain", "Resources vs science (Spearman across systems)", f"{rs.rho:+.2f} (n={int(rs.n)})", "composite indicators (see the script) + Table I.1", "Composite is the mean of z-scored indicators; see COMPOSITES in analysis/09_cross_domain_panel.py", "analysis/09b_cross_domain_synthesis.py", "Association across systems; science is context, not an input.")
add("#9 Cross-domain", "AI use vs science (Spearman)", f"{ai.rho:+.2f} (n={int(ai.n)})", "composite indicators (see the script) + Table I.1", "As above", "analysis/09b_cross_domain_synthesis.py", "Higher-scoring systems report less AI use; do not read as AI lowering scores.")
add("#9 Cross-domain", "Pairs significant at p<0.05", f"{sig} of {len(c9)} (about {0.05 * len(c9):.0f} expected by chance)", "composites", "Spearman p-values", "analysis/09b_cross_domain_synthesis.py", "No multiple-comparison correction on the page.")

# ---- #10 uncertainty
TBL = {"ai_index": "4.53", "ai_never": "4.55", "no_draft": "4.58", "no_learn": "4.59", "assess_ai": "4.68", "distraction": "4.43",
       "capacity": "4.14", "lack_res": "4.7", "poor_res": "4.8", "computers": "4.1"}
u = rd("10_uncertainty_summary.csv")
for r in u.itertuples():
    add("#10 Uncertainty", f"{r.label}: neighbours in the ranking that differ significantly", f"{r.adjacent_sig:.0f}% unadjusted ({r.adjacent_sig_bonf:.0f}% Bonferroni); typical 95% rank range {r.median_rank_width:.0f} places wide; all pairs {r.pairs_sig:.0f}%",
        TBL[r.indicator], "est +/- 1.96 S.E.; z = (a-b)/sqrt(se_a^2+se_b^2)", "analysis/10_uncertainty_ranking.py", f"top inverse-variance weight: {r.top_name} {r.top_share:.0f}%; effective n {r.n_eff:.1f}")

OUT.mkdir(exist_ok=True)
with open(OUT / "claims_register.csv", "w", newline="", encoding="utf-8") as fh:
    w_ = csv.DictWriter(fh, fieldnames=list(R[0])); w_.writeheader(); w_.writerows(R)
print(f"Wrote {OUT / 'claims_register.csv'} ({len(R)} claims)")
for r in R:
    print(f"- [{r['dashboard']}] {r['claim']}: {r['value']}"[:330])
