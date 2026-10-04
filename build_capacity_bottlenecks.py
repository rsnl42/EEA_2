#!/usr/bin/env python3
"""Build the "Where does school capacity actually break down?" page (analysis #3).

Usage:
    python build_capacity_bottlenecks.py           # writes docs/capacity-bottlenecks/index.html
    python build_capacity_bottlenecks.py --xlsx PATH --out PATH
"""
import argparse
import json
import math
from pathlib import Path
import pandas as pd

from site_common import DEFAULT_XLSX, DOCS, ROOT, fill, load_template, write_page

OUT_DIR = ROOT / "outputs"

ITEMS = {
    "devices_connected": "Internet-connected devices",
    "bandwidth": "Internet bandwidth/speed",
    "devices_instruction": "Devices for instruction",
    "software": "Educational software",
    "teacher_skills": "Teacher tech & pedagogical skills",
    "teacher_time": "Teacher preparation time",
    "pd_resources": "Professional development resources",
    "online_platform": "Online learning platform",
    "incentives": "Teacher digital incentives",
    "curriculum_fit": "Curriculum fit of digital tools",
    "support_staff": "Technical support staff",
    "device_power": "Computing power / performance",
}


def build(xlsx: Path = DEFAULT_XLSX, out: Path = DOCS / "capacity-bottlenecks" / "index.html") -> str:
    items_df = pd.read_csv(OUT_DIR / "03_capacity_items.csv")
    weak_df = pd.read_csv(OUT_DIR / "03_capacity_weakest_link.csv")
    clus_df = pd.read_csv(OUT_DIR / "03_capacity_clusters.csv")
    prof_df = pd.read_csv(OUT_DIR / "03_capacity_cluster_profiles.csv")

    items_map = items_df.set_index("system")
    weak_map = weak_df.set_index("system")
    clus_map = clus_df.set_index("system")

    oecd_row = items_map.loc["OECD average"] if "OECD average" in items_map.index else None
    oecd_dict = {k: (round(float(oecd_row[k]), 1) if k in oecd_row and not pd.isna(oecd_row[k]) else None) for k in ITEMS} if oecd_row is not None else {}

    systems_list = []
    for sys_name in clus_df["system"]:
        if sys_name == "OECD average":
            continue
        it = items_map.loc[sys_name] if sys_name in items_map.index else {}
        wk = weak_map.loc[sys_name] if sys_name in weak_map.index else {}
        cl = clus_map.loc[sys_name] if sys_name in clus_map.index else {}

        rec = {
            "n": sys_name,
            "cluster": int(cl.get("cluster", 1)),
            "silhouette": round(float(cl.get("silhouette", 0)), 3),
            "pc1": round(float(cl.get("pc1", 0)), 3),
            "pc2": round(float(cl.get("pc2", 0)), 3),
            "science": None if pd.isna(cl.get("science")) else round(float(cl.get("science")), 1),
            "weak_abs": str(wk.get("weakest_absolute", "")),
            "weak_abs_pct": round(float(wk.get("weakest_absolute_pct", 0)), 1) if not pd.isna(wk.get("weakest_absolute_pct")) else None,
            "weak_rel": str(wk.get("weakest_relative", "")),
            "weak_rel_z": round(float(wk.get("weakest_relative_z", 0)), 2) if not pd.isna(wk.get("weakest_relative_z")) else None,
        }
        for ik in ITEMS:
            val = it.get(ik)
            rec[ik] = round(float(val), 1) if not pd.isna(val) else None
        systems_list.append(rec)

    profiles_list = []
    for _, pr in prof_df.iterrows():
        p_dict = {
            "cluster": int(pr["cluster"]),
            "n": int(pr["n"]),
            "science_mean": round(float(pr["science_mean"]), 1) if not pd.isna(pr["science_mean"]) else None,
            "label": str(pr["label"]),
            "systems": str(pr["systems"]),
        }
        for ik in ITEMS:
            v = pr.get(ik)
            p_dict[ik] = round(float(v), 1) if not pd.isna(v) else None
        profiles_list.append(p_dict)

    dump = lambda o: json.dumps(o, separators=(",", ":"), ensure_ascii=False)

    rendered_html = fill(load_template("capacity_bottlenecks.html"), {
        "ITEMS": dump(ITEMS),
        "OECD": dump(oecd_dict),
        "ROWS": dump(systems_list),
        "PROFILES": dump(profiles_list),
    })

    write_page(out, rendered_html)
    return f"{len(systems_list)} systems, 12 capacity items, {len(rendered_html) / 1024:.0f} KB"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--xlsx", type=Path, default=DEFAULT_XLSX)
    ap.add_argument("--out", type=Path, default=DOCS / "capacity-bottlenecks" / "index.html")
    args = ap.parse_args()
    print(f"Wrote {args.out}: {build(args.xlsx, args.out)}")


if __name__ == "__main__":
    main()
