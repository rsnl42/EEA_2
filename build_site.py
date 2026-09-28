#!/usr/bin/env python3
"""Build the whole GitHub Pages site into docs/.

    docs/index.html                landing page linking to every dashboard
    docs/<slug>/index.html         one folder per dashboard

To add a dashboard: write a module with build(xlsx, out) -> str, a template in
templates/, and append an entry to PAGES below.

Usage:
    python build_site.py [--xlsx PATH] [--docs DIR]
"""
import argparse
import html
from pathlib import Path

import build_cross_domain
import build_dashboard
import build_infrastructure_divides
import build_policy_typologies
import build_use_guidance
from site_common import DEFAULT_XLSX, DOCS, fill, load_template, write_page

PAGES = [
    {
        "slug": "equity-gaps",
        "title": "Who uses AI and digital devices in class, and who doesn't?",
        "blurb": ("72 group gaps (gender, SES, immigrant background, education level, programme, "
                  "school location and type) across nine AI and device outcomes. Select any cell "
                  "for country-level gaps with confidence intervals and a written summary."),
        "tables": "I.B1.4.26, 43, 54 to 59, 68",
        "script": "analysis/01_equity_gaps.py",
        "build": build_dashboard.build,
    },
    {
        "slug": "infrastructure-divides",
        "title": "Do richer schools really have better tech? It depends what you ask.",
        "blurb": ("Seven school-resourcing measures, split by rich/poor, city/rural and private/public "
                  "schools. Raw device counts often favour poorer or rural schools, but reported "
                  "shortages, poor quality and readiness to teach digitally clearly favour richer and "
                  "private ones. Plain-language grid plus a per-country lookup."),
        "tables": "I.B1.4.1, 4, 5, 7, 8, 11, 15",
        "script": "analysis/02_infrastructure_divides.py",
        "build": build_infrastructure_divides.build,
    },
    {
        "slug": "use-guidance",
        "title": "Does school guidance keep pace with student AI use?",
        "blurb": ("Compares the share of students using AI for schoolwork with the share asked, in "
                  "lessons, to assess AI output, across 85 systems. Includes a comparison with "
                  "guidance on online information, a ranking, and a lookup for any system."),
        "tables": "I.B1.4.53, 55, 67, 68",
        "script": "analysis/07_use_guidance_gap.py",
        "build": build_use_guidance.build,
    },
    {
        "slug": "policy-typologies",
        "title": "How are schools governing devices and AI, and is it changing?",
        "blurb": ("A nine-item policy-intensity index, plus the four device-policy regimes compared "
                  "2022 vs 2025 with each system's shift tested against its own standard error and "
                  "classified as a fast adopter or lagging. Includes open questions on whether phone "
                  "bans track with less in-school leisure device use or less AI use."),
        "tables": "I.B1.4.47, 49",
        "script": "analysis/08_policy_typologies.py",
        "build": build_policy_typologies.build,
    },
    {
        "slug": "cross-domain",
        "title": "How do resources, capacity, time use and AI relate?",
        "blurb": ("Nine country-level composite indices built from resourcing, teacher capacity, "
                  "time use, leisure, distraction, device rules and AI use/guidance. A correlation "
                  "explorer with country-level scatterplots, plus five clustered country archetypes."),
        "tables": "I.B1.4.1, 4, 6, 11, 14, 21, 37, 43, 47, 53, 55, 67, 68",
        "script": "analysis/09_cross_domain_panel.py + 09b + 09c",
        "build": build_cross_domain.build,
    },
]


def landing_items() -> str:
    e = html.escape
    return "\n".join(
        f'<li><a class="page" href="{e(p["slug"])}/"><h2>{e(p["title"])}</h2>'
        f'<p>{e(p["blurb"])}</p><small>Tables {e(p["tables"])} &middot; script {e(p["script"])}</small></a></li>'
        for p in PAGES
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--xlsx", type=Path, default=DEFAULT_XLSX)
    ap.add_argument("--docs", type=Path, default=DOCS)
    args = ap.parse_args()

    for p in PAGES:
        out = args.docs / p["slug"] / "index.html"
        print(f"{p['slug']:14s} {out}: {p['build'](args.xlsx, out)}")
    index = args.docs / "index.html"
    write_page(index, fill(load_template("landing.html"), {"PAGES": landing_items()}))
    print(f"{'landing':14s} {index}: {len(PAGES)} dashboards linked")


if __name__ == "__main__":
    main()
