#!/usr/bin/env python3
"""Build the "How do resources, capacity, time use and AI relate?" page (#9a/#9b/#9c).

Imports 09_cross_domain_panel.py, 09b_cross_domain_synthesis.py and
09c_cross_domain_clusters.py directly (rather than reading their CSVs) so the page always
matches what those scripts would print, including the exact k=5 clustering and the exact
partial-correlation/residual numbers used in the "relationships checked further" panel.

Usage:
    python build_cross_domain.py           # writes docs/cross-domain/index.html
    python build_cross_domain.py --xlsx PATH --out PATH
"""
import argparse
import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd

from site_common import DEFAULT_XLSX, DOCS, ROOT, fill, load_template, write_page

ANALYSIS = ROOT / "analysis"
K = 5


def load_module(stem: str):
    """Import analysis/<stem>.py (its name isn't a valid module name to `import`)."""
    spec = importlib.util.spec_from_file_location(stem, ANALYSIS / f"{stem}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def notable_relationships(part: pd.DataFrame, resid: pd.DataFrame, labels: dict) -> list[dict]:
    """Turn 9b's curated partial correlations and residual pairs into short write-ups,
    computed from the numbers (not hand-written), so they stay correct if the data changes."""
    items = []
    for _, r in part.iterrows():
        x, y, z = labels[r.x], labels[r.y], labels[r.control]
        held = "holds up" if abs(r.rho_partial) >= abs(r.rho_unadjusted) * 0.6 else \
               "weakens substantially" if abs(r.rho_partial) < abs(r.rho_unadjusted) * 0.3 else "weakens somewhat"
        items.append({
            "t": f"{x} and {y}, controlling for {z}.",
            "d": f"Unadjusted rho = {r.rho_unadjusted:+.2f}; holding {_lc(z)} constant, "
                 f"it becomes {r.rho_partial:+.2f} (n={r.n}) &mdash; the relationship {held}. {r.note}",
        })
    for x, y, desc in resid_pairs_desc(resid, labels):
        items.append({"t": desc, "d": x})
    return items


def _lc(label: str) -> str:
    """Lowercase for mid-sentence use, but keep acronyms like AI capitalised."""
    return label if label.startswith("AI") else label[0].lower() + label[1:]


def resid_pairs_desc(resid: pd.DataFrame, labels: dict) -> list[tuple[str, str, str]]:
    out = []
    for col in resid.columns:
        y_key, x_key = col.replace("resid_", "").split("_on_")
        s = resid[col].dropna().sort_values()
        lo = ", ".join(f"{n} ({v:+.1f})" for n, v in s.head(4).items())
        hi = ", ".join(f"{n} ({v:+.1f})" for n, v in s.tail(4).items())
        text = (f"Furthest below what {_lc(labels[x_key])} predicts: {lo}. "
                f"Furthest above: {hi}.")
        out.append((text, y_key, f"{labels[y_key]} vs. what {_lc(labels[x_key])} predicts."))
    return out


def build(xlsx: Path, out: Path) -> str:
    panel = load_module("09_cross_domain_panel")
    synth = load_module("09b_cross_domain_synthesis")
    clus = load_module("09c_cross_domain_clusters")
    from pisa_utils import Workbook

    table_i1 = pd.read_csv(ROOT / "data" / "pisa2025_table_I1.csv", index_col=0)
    P = panel.build_raw(Workbook(xlsx), table_i1)
    C = panel.build_composites(P)

    corr = synth.correlation_matrix(C)
    part = synth.partials_table(C)
    resid = synth.residuals_table(C)
    cols, result, profiles = clus.cluster_systems(C, K)

    labels = synth.COMPOSITE_LABELS
    dump = lambda o: json.dumps(o, separators=(",", ":"), ensure_ascii=False)  # noqa: E731

    corr_rows = [{"v1": r.var1, "v2": r.var2, "rho": round(r.rho, 3), "p": round(r.p, 4), "n": int(r.n)}
                 for r in corr.itertuples()]
    rows_c = [[name, {c: (None if pd.isna(v) else round(float(v), 3)) for c, v in row.items()}]
              for name, row in C.iterrows()]
    notable = notable_relationships(part, resid, labels)

    clus_rows = []
    for name, r in result.iterrows():
        row = {"n": name, "cluster": int(r.cluster), "silhouette": round(float(r.silhouette), 3),
               "pc1": round(float(r.pc1), 2), "pc2": round(float(r.pc2), 2),
               "science": None if pd.isna(r.science) else round(float(r.science), 1)}
        row.update({c: round(float(r[c]), 3) for c in cols})
        clus_rows.append(row)

    prof_rows = []
    for c, r in profiles.iterrows():
        row = {"cluster": int(c), "n": int(r.n), "science_mean": None if pd.isna(r.science_mean) else float(r.science_mean),
               "label": r.label, "systems": r.systems}
        row.update({col: round(float(r[col]), 3) for col in cols})
        prof_rows.append(row)

    html = fill(load_template("cross_domain.html"), {
        "COMPOSITE_LABELS": dump(labels),
        "CORR": dump(corr_rows),
        "ROWS_C": dump(rows_c),
        "NOTABLE": dump(notable),
        "CLUS_ROWS": dump(clus_rows),
        "PROFILES": dump(prof_rows),
        "VAR_EXPL": dump(round(profiles.attrs["var_explained"], 3)),
    })
    write_page(out, html)
    return f"{len(corr_rows)} correlations, {len(clus_rows)} clustered systems, {len(prof_rows)} archetypes, {len(html) / 1024:.0f} KB"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--xlsx", type=Path, default=DEFAULT_XLSX)
    ap.add_argument("--out", type=Path, default=DOCS / "cross-domain" / "index.html")
    args = ap.parse_args()
    print(f"Wrote {args.out}: {build(args.xlsx, args.out)}")


if __name__ == "__main__":
    main()
