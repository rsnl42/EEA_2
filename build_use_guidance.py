#!/usr/bin/env python3
"""Build the "Does school guidance keep pace with AI use?" page (analysis #7).

The numbers come from analysis/07_use_guidance_gap.py (prepare + summary_stats), so
the page and the script's CSV/console output always agree.

Usage:
    python build_use_guidance.py           # writes docs/use-guidance/index.html
    python build_use_guidance.py --xlsx PATH --out PATH
"""
import argparse
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

from site_common import DEFAULT_XLSX, DOCS, ROOT, fill, load_template, write_page

ANALYSIS = ROOT / "analysis"
QUADRANTS = ["high use, high guidance", "high use, low guidance",
             "low use, low guidance", "low use, high guidance"]


def load_analysis():
    """Import analysis/07_use_guidance_gap.py (its name isn't a valid module name)."""
    sys.path.insert(0, str(ANALYSIS))
    spec = importlib.util.spec_from_file_location("use_guidance_gap", ANALYSIS / "07_use_guidance_gap.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def build(xlsx: Path, out: Path) -> str:
    ug = load_analysis()
    from pisa_utils import Workbook

    X, S, O = ug.prepare(Workbook(xlsx))
    flag = np.select([S.sig_mismatch, S.sig_low_low, S.sig_low_high], [1, 2, 3], default=0)
    rows = [
        [name, round(r.use_any, 4), round(r.guid, 4), round(r.online, 4),
         QUADRANTS.index(r.quadrant), round(r.resid, 4), int(f)]
        for (name, r), f in zip(S.iterrows(), flag)
    ]
    dump = lambda o: json.dumps(o, separators=(",", ":"), ensure_ascii=False)  # noqa: E731
    html = fill(load_template("use_guidance.html"),
                {"ROWS": dump(rows), "STATS": dump(ug.summary_stats(S, O))})
    write_page(out, html)
    return f"{len(rows)} systems, {len(html) / 1024:.0f} KB"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--xlsx", type=Path, default=DEFAULT_XLSX)
    ap.add_argument("--out", type=Path, default=DOCS / "use-guidance" / "index.html")
    args = ap.parse_args()
    print(f"Wrote {args.out}: {build(args.xlsx, args.out)}")


if __name__ == "__main__":
    main()
