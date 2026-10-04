#!/usr/bin/env python3
"""Analysis #3: School Capacity Bottlenecks in PISA 2025.

Processes Table I.B1.4.14 (12 capacity sufficiency items across 91 systems).
"""
import pandas as pd
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT / "outputs"

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

def load_data():
    items_df = pd.read_csv(OUT / "03_capacity_items.csv", index_col=0)
    weak_df = pd.read_csv(OUT / "03_capacity_weakest_link.csv", index_col=0)
    clus_df = pd.read_csv(OUT / "03_capacity_clusters.csv", index_col=0)
    prof_df = pd.read_csv(OUT / "03_capacity_cluster_profiles.csv", index_col=0)
    return items_df, weak_df, clus_df, prof_df

if __name__ == "__main__":
    items, weak, clus, prof = load_data()
    print(f"Loaded capacity data for {len(weak)} systems across {len(ITEMS)} items.")
