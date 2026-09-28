#!/usr/bin/env python3
"""#8  Policy typologies: how schools govern digital devices, and whether it moved.

Two tables, two different questions:

  Table 4.47 (2025 only, 9 items)
      A written statement about general device use; a cell-phone ban; formal
      subject-specific guidelines; teacher-set in-class rules; rules co-set with
      students; a responsible-internet-behaviour programme; a social-network
      policy for teaching; a teacher-collaboration programme; scheduled time for
      teachers to develop digital materials together.
      -> used here to build a single policy-intensity index per system.

  Table 4.49 (2022 and 2025, 4 mutually exclusive regimes)
      Neither / cell-phone-bans-only / subject-guidelines-only / both.
      -> used here to classify systems as fast adopters or laggards, testing
      each system's 2022->2025 shift with the S.E. the workbook already reports
      for that change.

Open questions (not covered in the OECD text, which only reports the OECD-average
shift and one system-level correlation between bans and distraction): does a
phone ban associate with less in-school leisure device use, and with AI use?
These are tested here against the leisure_at_school and ai_use composites from
#9a (outputs/09_panel_composites.csv), alongside a distraction check that should
roughly reproduce the text's reported relationship.

Caveat on the z-scores: table 4.49's per-system S.E.s range from ~0.07 to ~6 pp
(median ~3.9). The smallest belong to a handful of small systems (Macao, Brunei,
Malta, Qatar, Iceland) that PISA samples close to a school census, so their
sampling error is mechanically tiny -- a modest change there can produce a huge
z. The report below cross-checks the z-ranked "fast adopter" list against a
plain magnitude ranking so that isn't mistaken for the biggest real shifts.

Usage:
    python analysis/08_policy_typologies.py [--xlsx PATH] [--out-dir DIR]
Outputs (default outputs/):
    08_policy_index.csv               9 raw items + z-score policy-intensity index, per system
    08_regime_typology.csv             2022/2025/change/S.E./z per regime + adopter_status
    08_policy_outcome_correlations.csv  policy vars x distraction/leisure_at_school/ai_use
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from pisa_utils import OECD_ROW, Z95, Workbook, out_dir  # noqa: E402

# ---------- Table 4.47: nine policy items -> intensity index ----------

ITEMS_47 = {
    "written_statement": "a written statement about the general use of digital devices",
    "phone_ban": "cell phones is not allowed",
    "subject_guidelines": "formal guidelines for the use of digital devices for teaching",
    "teacher_set_rules": "Teachers establish rules for when students may use",
    "co_set_rules": "in collaboration with students",
    "responsible_use_programme": "specific programme to prepare students for responsible",
    "social_network_policy": "specific policy about using social networks",
    "teacher_collab_programme": "promote collaboration on the use of digital devices among teachers",
    "scheduled_collab_time": "scheduled time for teachers to meet",
}


def build_policy_index(wb: Workbook) -> pd.DataFrame:
    X = pd.DataFrame(index=wb.raw.index)
    for name, kw in ITEMS_47.items():
        est, se = wb.pair("47", kw, endswith="Yes - %")
        X[name] = est
        X[f"{name}_se"] = se

    S = X.drop(OECD_ROW)
    item_cols = list(ITEMS_47)
    Z = (S[item_cols] - S[item_cols].mean()) / S[item_cols].std(ddof=0)
    coverage = Z.notna().mean(axis=1)
    X["policy_intensity"] = pd.Series(
        Z.mean(axis=1).where(coverage >= 0.5), index=S.index
    ).reindex(X.index)
    X["rank"] = X["policy_intensity"].rank(ascending=False)
    return X


# ---------- Table 4.49: four regimes, two waves -> typology ----------

REGIMES = {
    "neither": "Neither cell phone bans nor subject-specific guidelines",
    "bans_only": "Cell phone bans only",
    "guidelines_only": "Subject-specific guidelines for digital device use only",
    "both": "Both cell phone bans and subject-specific guidelines",
}
DEPTH_WEIGHT = {"neither": 0, "bans_only": 1, "guidelines_only": 1, "both": 2}


def _cols(wb: Workbook, wave_prefix: str, label: str, suffix: str) -> str:
    hits = [c for c in wb.table_columns("49")
            if c.startswith(f"[I.B1.4.49] {wave_prefix}") and label in c and c.rstrip().endswith(suffix)]
    if len(hits) != 1:
        sys.exit(f"Table 49, wave={wave_prefix!r}, label={label!r}, suffix={suffix!r}: {len(hits)} matches")
    return hits[0]


def build_regime_typology(wb: Workbook) -> pd.DataFrame:
    X = pd.DataFrame(index=wb.raw.index)
    for key, label in REGIMES.items():
        X[f"{key}_2022"] = wb.num[_cols(wb, "PISA 2022", label, "- %")]
        X[f"{key}_2025"] = wb.num[_cols(wb, "PISA 2025", label, "- %")]
        X[f"{key}_change"] = wb.num[_cols(wb, "Change", label, "- % dif.")]
        X[f"{key}_change_se"] = wb.num[_cols(wb, "Change", label, "- S.E.")]
        X[f"{key}_z"] = X[f"{key}_change"] / X[f"{key}_change_se"]
        X[f"{key}_sig"] = X[f"{key}_z"].abs() > Z95

    for wave in ("2022", "2025"):
        X[f"depth_{wave}"] = sum(w * X[f"{k}_{wave}"] for k, w in DEPTH_WEIGHT.items()) / 100
    X["depth_change"] = X["depth_2025"] - X["depth_2022"]

    O = X.loc[OECD_ROW]
    S = X.drop(OECD_ROW)

    fast = S["both_z"] > Z95
    lagging = (~fast) & (S["neither_2025"] > O["neither_2025"]) & (S["neither_z"] > -Z95)
    S["adopter_status"] = np.select(
        [fast, lagging], ["fast adopter", "lagging"], default="moderate / already regulated",
    )
    return pd.concat([S, X.loc[[OECD_ROW]].assign(adopter_status="(OECD average)")])


# ---------- Open questions: policy vars vs panel outcome composites ----------

OUTCOME_COLS = ["distraction", "leisure_at_school", "ai_use"]


def load_composites(xlsx, out: Path) -> pd.DataFrame:
    path = out / "09_panel_composites.csv"
    if path.exists():
        return pd.read_csv(path, index_col=0)
    sys.exit(f"{path} not found; run analysis/09_cross_domain_panel.py first.")


def build_outcome_frame(policy: pd.DataFrame, regime: pd.DataFrame, C: pd.DataFrame) -> pd.DataFrame:
    return policy.drop(OECD_ROW).join(
        regime.drop(OECD_ROW)[["both_2025", "neither_2025", "depth_2025", "depth_change"]]
    ).join(C[OUTCOME_COLS])


def outcome_correlations(policy: pd.DataFrame, regime: pd.DataFrame, C: pd.DataFrame) -> pd.DataFrame:
    df = build_outcome_frame(policy, regime, C)
    policy_vars = ["phone_ban", "subject_guidelines", "policy_intensity",
                   "both_2025", "neither_2025", "depth_2025", "depth_change"]
    rows = []
    for pv in policy_vars:
        for oc in OUTCOME_COLS:
            d = df[[pv, oc]].dropna()
            if len(d) < 10:
                continue
            rho, p = stats.spearmanr(d[pv], d[oc])
            rows.append({"policy_var": pv, "outcome": oc, "rho": round(float(rho), 3),
                         "p": round(float(p), 4), "n": len(d)})
    return pd.DataFrame(rows)


def report(policy: pd.DataFrame, regime: pd.DataFrame, corr: pd.DataFrame) -> None:
    O = regime.loc[OECD_ROW]
    print("Table 4.47 -> policy-intensity index")
    S = policy.drop(OECD_ROW)
    print(f"  systems with full 9-item coverage: {(S[list(ITEMS_47)].notna().all(axis=1)).sum()} of {len(S)}")
    for name, kw in ITEMS_47.items():
        print(f"  {name:26s} OECD={O_item(policy, name):5.1f}%  median={S[name].median():5.1f}%")
    print("\n  Highest policy intensity:")
    print(S.nlargest(6, "policy_intensity")[["policy_intensity"]].round(2).to_string())
    print("\n  Lowest policy intensity:")
    print(S.nsmallest(6, "policy_intensity")[["policy_intensity"]].round(2).to_string())

    print("\nTable 4.49 -> OECD-average shift, 2022 -> 2025")
    for k in DEPTH_WEIGHT:
        z = O[f"{k}_z"]
        star = "*" if abs(z) > Z95 else " "
        print(f"  {k:16s} {O[f'{k}_2022']:5.1f}% -> {O[f'{k}_2025']:5.1f}%  "
              f"({O[f'{k}_change']:+5.1f} pp, z={z:5.1f}{star})")
    print(f"  regulatory depth (0=neither,2=both) {O['depth_2022']:.2f} -> {O['depth_2025']:.2f} "
          f"({O['depth_change']:+.2f})")

    print("\nAdopter classification (per-system 2022->2025 shift, tested against its own S.E.)")
    print(regime.drop(OECD_ROW)["adopter_status"].value_counts().to_string())
    fast = regime[regime.adopter_status == "fast adopter"].sort_values("both_z", ascending=False)
    print(f"\nFast adopters ({len(fast)}), by z-score on the 'both' shift:")
    print(fast[["both_2022", "both_2025", "both_change", "both_z"]].round(1).head(10).to_string())
    print("\n  ...same list, ranked by raw pp change instead (z-ranking is skewed by a few "
          "near-census systems with tiny S.E.s -- see module docstring):")
    print(fast.sort_values("both_change", ascending=False)
          [["both_2022", "both_2025", "both_change", "both_z"]].round(1).head(10).to_string())
    lag = regime[regime.adopter_status == "lagging"].sort_values("neither_2025", ascending=False)
    print(f"\nLagging ({len(lag)}), by 2025 'neither' share:")
    print(lag[["neither_2022", "neither_2025", "neither_change", "neither_z"]].round(1).head(10).to_string())

    print("\nOpen questions: policy stance vs outcome composites (Spearman rank correlation)")
    print(corr.to_string(index=False))


def O_item(policy: pd.DataFrame, name: str) -> float:
    return float(policy.loc[OECD_ROW, name])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--xlsx", type=Path, default=None)
    ap.add_argument("--out-dir", type=Path, default=None)
    args = ap.parse_args()

    wb = Workbook(args.xlsx)
    out = out_dir(args.out_dir)

    policy = build_policy_index(wb)
    regime = build_regime_typology(wb)
    C = load_composites(args.xlsx, out)
    corr = outcome_correlations(policy, regime, C)

    report(policy, regime, corr)

    policy.round(3).to_csv(out / "08_policy_index.csv", index_label="system")
    regime.round(3).to_csv(out / "08_regime_typology.csv", index_label="system")
    corr.to_csv(out / "08_policy_outcome_correlations.csv", index=False)
    for name in ("08_policy_index.csv", "08_regime_typology.csv", "08_policy_outcome_correlations.csv"):
        print(f"\nWrote {out / name}")


if __name__ == "__main__":
    main()
