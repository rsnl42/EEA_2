#!/usr/bin/env python3
"""#9c  Cross-domain clustering: country archetypes.

Clusters education systems on the 9 composite indices from 9a (resources, capacity,
time use x2, leisure x2, distraction, rules, AI use, AI guidance — science is held out
as context, not a clustering input). Ward hierarchical clustering on standardised
composites, restricted to the ~83 systems with a value on every composite.

Choosing k: this workbook has no obvious "natural" number of country archetypes, so k is
chosen by comparing, across k=2..8: silhouette score (higher = better separated), agreement
between Ward and an independent k-means run (Adjusted Rand Index, a check that the grouping
isn't an artefact of one algorithm), and bootstrap stability (resampling 80% of systems 200
times). None of these single out one k decisively -- silhouette is uniformly low (0.14-0.18)
at every k, meaning these are gradients, not tight, well-separated groups, and both agreement
and stability rise again at k=8 as it fragments into small, mutually-agreed-upon splinters.
k=5 is a middle-of-the-pack choice on all three metrics (not the top scorer on any). It was
picked over the alternatives just below and above it: at k=4, one 43-system cluster mixes two
groups that 9b's correlations suggest are conceptually distinct -- high-resource systems and
high-capacity/high-AI-guidance systems (resources and capacity correlate only moderately,
rho=0.60) -- and k=5 is where that cluster splits into those two. At k=6 the next split
divides that high-capacity/high-AI-guidance group again, separating a small high-resource,
low-AI-use Nordic/Anglophone group from the rest, which is a real but finer distinction than
k=5's; k=5 was kept as the coarser, more parsimonious summary. k=2 or k=3 collapse most of
the structure explored in 9b; k=7/8 mostly fragment further without a materially higher
silhouette. The four-system "low AI use and guidance" outlier group (B-S-J-Z, Ireland,
Japan, United Kingdom) is stable from k=4 onward. Treat cluster membership as a broad summary,
not a firm classification -- don't over-interpret any single system's assignment, especially
one with low per-system silhouette (in the output) or that moves between the sub-groups
visible at k=6/k=7.

This is unsupervised description, not a validated typology: with p=9 features and n~83,
some grouping is expected even in unstructured data, and cluster identity for any one
borderline system can flip under a different k or a different subset of indicators.

Usage:
    python analysis/09c_cross_domain_clusters.py [--xlsx PATH] [--k N] [--out-dir DIR]
Outputs (default outputs/):
    09c_k_selection.csv     silhouette / ARI / bootstrap stability for each candidate k
    09c_clusters.csv        system, cluster, per-system silhouette, PC1/PC2 (for plotting)
    09c_cluster_profiles.csv cluster means on each composite + science + size
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import fcluster, linkage
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score, silhouette_samples, silhouette_score

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from pisa_utils import out_dir  # noqa: E402
from importlib.util import module_from_spec, spec_from_file_location  # noqa: E402

CANDIDATE_KS = range(2, 9)
N_BOOTSTRAP = 200
BOOTSTRAP_FRACTION = 0.8


def load_composites(xlsx: Path | None, out: Path) -> pd.DataFrame:
    path = out / "09_panel_composites.csv"
    if path.exists():
        return pd.read_csv(path, index_col=0)
    print(f"{path} not found; rebuilding the panel from the workbook.")
    from pisa_utils import Workbook
    spec = spec_from_file_location("cross_domain_panel", HERE / "09_cross_domain_panel.py")
    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)
    table_i1 = pd.read_csv(HERE.parent / "data" / "pisa2025_table_I1.csv", index_col=0)
    P = mod.build_raw(Workbook(xlsx), table_i1)
    return mod.build_composites(P)


def bootstrap_stability(Zs: np.ndarray, k: int, base_labels: np.ndarray, seed: int = 0) -> float:
    """Mean ARI between the full clustering and clusterings of random 80% subsamples,
    each compared only on the systems present in both."""
    rng = np.random.default_rng(seed)
    n = len(Zs)
    aris = []
    for _ in range(N_BOOTSTRAP):
        idx = rng.choice(n, size=int(n * BOOTSTRAP_FRACTION), replace=False)
        sub_labels = fcluster(linkage(Zs[idx], "ward"), k, "maxclust")
        aris.append(adjusted_rand_score(base_labels[idx], sub_labels))
    return float(np.mean(aris))


def select_k(Zs: np.ndarray) -> pd.DataFrame:
    rows = []
    for k in CANDIDATE_KS:
        ward = fcluster(linkage(Zs, "ward"), k, "maxclust")
        km = KMeans(n_clusters=k, n_init=20, random_state=0).fit(Zs).labels_
        rows.append({
            "k": k,
            "silhouette_ward": round(silhouette_score(Zs, ward), 3),
            "silhouette_kmeans": round(silhouette_score(Zs, km), 3),
            "ari_ward_vs_kmeans": round(adjusted_rand_score(ward, km), 3),
            "bootstrap_stability": round(bootstrap_stability(Zs, k, ward), 3),
            "sizes": ",".join(map(str, np.sort(np.bincount(ward)[1:])[::-1])),
        })
    return pd.DataFrame(rows)


def name_cluster(row: pd.Series, cols: list[str]) -> str:
    """A short descriptive label from each cluster's two most extreme composite means."""
    ranked = row[cols].sort_values(key=lambda s: -s.abs())
    parts = []
    for name in ranked.index[:2]:
        val = row[name]
        if abs(val) < 0.3:
            continue
        direction = "high" if val > 0 else "low"
        words = name.replace("_", " ").split()
        words = ["AI" if w == "ai" else w for w in words]
        parts.append(f"{direction} {' '.join(words)}")
    return ", ".join(parts) if parts else "middling on every composite"


def cluster_systems(C: pd.DataFrame, k: int = 5):
    """Cluster the composite panel `C` (as returned by 09a's build_composites) into `k`
    groups. Returns (cols, result, profiles): the composite columns used, a per-system
    frame (composites + cluster + silhouette + pc1/pc2 + science), and a per-cluster
    profile frame (composite means + n + science_mean + label + systems). Used both by
    this script's CLI and by the dashboard page builder, so the two always agree."""
    cols = [c for c in C.columns if c != "science"]
    D = C[cols].dropna()
    Zs = ((D - D.mean()) / D.std(ddof=0)).values

    labels = fcluster(linkage(Zs, "ward"), k, "maxclust")
    sil = silhouette_samples(Zs, labels)

    Zc = Zs - Zs.mean(axis=0)
    U, s, _ = np.linalg.svd(Zc, full_matrices=False)
    pcs = U[:, :2] * s[:2]
    var_explained = (s ** 2 / (s ** 2).sum())[:2]

    result = D.copy()
    result["cluster"] = labels
    result["silhouette"] = sil.round(3)
    result["pc1"], result["pc2"] = pcs[:, 0].round(2), pcs[:, 1].round(2)
    result["science"] = C["science"].reindex(D.index)

    profiles = result.groupby("cluster")[cols].mean().round(2)
    profiles["n"] = result.groupby("cluster").size()
    profiles["science_mean"] = result.groupby("cluster")["science"].mean().round(0)
    # Label from STANDARDISED cluster means, the same unit-variance scale the clustering used.
    # Composites are averages of several z-scores, so their raw SDs differ (0.56 to 1.0) and
    # ranking raw means would favour the high-variance composites.
    zmeans = pd.DataFrame(Zs, index=D.index, columns=cols).assign(cluster=labels).groupby("cluster")[cols].mean()
    profiles["label"] = zmeans.apply(lambda r: name_cluster(r, cols), axis=1)
    profiles["systems"] = result.groupby("cluster").apply(lambda g: ", ".join(sorted(g.index)))
    profiles.attrs["var_explained"] = float(var_explained.sum())
    return cols, result, profiles


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--xlsx", type=Path, default=None)
    ap.add_argument("--k", type=int, default=5, help="clusters to report in detail (still scans 2-8 for the selection table)")
    ap.add_argument("--out-dir", type=Path, default=None)
    args = ap.parse_args()

    out = out_dir(args.out_dir)
    C = load_composites(args.xlsx, out)
    cols = [c for c in C.columns if c != "science"]
    D = C[cols].dropna()
    Zs = ((D - D.mean()) / D.std(ddof=0)).values
    print(f"Clustering {len(D)} systems (of {len(C)}) with complete data on all {len(cols)} composites: {cols}\n")

    ksel = select_k(Zs)
    print("Candidate k: silhouette (Ward / k-means), agreement between the two methods (ARI), "
          "and bootstrap stability (mean ARI across 200 resamples of 80% of systems)")
    print(ksel.to_string(index=False))

    k = args.k
    cols, result, profiles = cluster_systems(C, k)
    print(f"\nUsing k={k} (see selection table above for why). "
          f"Mean silhouette: {result['silhouette'].mean():.3f}")
    print(f"\nCluster profiles (standardised composite means; PC1+PC2 explain "
          f"{profiles.attrs['var_explained']:.0%} of variance, shown for reference only):")
    for c, row in profiles.iterrows():
        print(f"\n  Cluster {c} (n={int(row.n)}): {row.label}")
        print(f"    science mean: {row.science_mean:.0f}")
        print("    " + ", ".join(f"{col}={row[col]:+.2f}" for col in cols))
        print(f"    systems: {row.systems}")

    ksel.to_csv(out / "09c_k_selection.csv", index=False)
    result.round(3).to_csv(out / "09c_clusters.csv", index_label="system")
    profiles.drop(columns="systems").to_csv(out / "09c_cluster_profiles.csv")
    print(f"\nWrote {out / '09c_k_selection.csv'}, {out / '09c_clusters.csv'}, "
          f"{out / '09c_cluster_profiles.csv'}")


if __name__ == "__main__":
    main()
