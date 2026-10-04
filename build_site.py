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

import build_ai_portfolios
import build_cross_domain
import build_dashboard
import build_capacity_bottlenecks
import build_infrastructure_divides
import build_leisure_profiles
import build_policy_typologies
import build_time_use
import build_uncertainty_ranking
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
        "category": "Equity & Access",
        "badge_class": "tag-equity",
        "cat_code": "equity",
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
        "category": "Tech Resources",
        "badge_class": "tag-infra",
        "cat_code": "infra",
    },
    {
        "slug": "capacity-bottlenecks",
        "title": "Where does school capacity actually break down?",
        "blurb": ("12 items behind the single capacity index \u2014 bandwidth, devices, software, "
                  "teacher skills and time, PD, incentives, curriculum fit, support staff and more. "
                  "Ranks each country\u2019s weakest link two ways (absolute and relative to its own "
                  "profile) and groups countries into four recurring bottleneck shapes."),
        "tables": "I.B1.4.14",
        "script": "analysis/03_capacity_bottlenecks.py",
        "build": build_capacity_bottlenecks.build,
        "category": "Tech Resources",
        "badge_class": "tag-infra",
        "cat_code": "infra",
    },
    {
        "slug": "time-use",
        "title": "How do students split their device time between learning and leisure?",
        "blurb": ("Hours per day on devices for learning vs leisure at school, before/after school and on "
                  "weekends. Compares the learning-to-leisure ratio country by country, splits the weekday "
                  "between school and home, shows the heavy-use tails (over 5 or 7 hours) and groups "
                  "countries into four time-use archetypes."),
        "tables": "I.B1.4.21",
        "script": "analysis/04_time_use_budgets.py",
        "build": build_time_use.build,
        "category": "Equity & Access",
        "badge_class": "tag-equity",
        "cat_code": "equity",
    },
    {
        "slug": "leisure-profiles",
        "title": "What do students do online for fun, and how does it change at weekends?",
        "blurb": ("Seven digital leisure activities (gaming, social media, creating content, tutorials and "
                  "more) on weekdays and weekends. Compares activity mixes across countries, measures the "
                  "weekday-to-weekend shift, and contrasts passive consumption with creative use. Only 44 "
                  "systems have data in these tables."),
        "tables": "I.B1.4.37, 40",
        "script": "analysis/05_leisure_profiles.py",
        "build": build_leisure_profiles.build,
        "category": "Equity & Access",
        "badge_class": "tag-equity",
        "cat_code": "equity",
    },
    {
        "slug": "ai-portfolios",
        "title": "Do students use AI to draft or to learn?",
        "blurb": ("Four school purposes (summarising, research, drafting, helping me learn) by five frequency "
                  "levels. Compares drafting, a rough proxy for offloading, with learning country by country, "
                  "separates adoption from intensity among users, and groups 85 systems into three patterns."),
        "tables": "I.B1.4.53 (56 to 59 map to its never-use share)",
        "script": "analysis/06_ai_use_portfolios.py",
        "build": build_ai_portfolios.build,
        "category": "Policy & Guidance",
        "badge_class": "tag-guidance",
        "cat_code": "policy",
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
        "category": "Policy & Guidance",
        "badge_class": "tag-guidance",
        "cat_code": "policy",
    },
    {
        "slug": "policy-typologies",
        "title": "How are schools governing devices and AI, and is it changing?",
        "blurb": ("A nine-item policy-intensity index, plus the four device-policy regimes compared "
                  "2022 vs 2025 with each system\u2019s shift tested against its own standard error and "
                  "classified as a fast adopter or lagging. Includes open questions on whether phone "
                  "bans track with less in-school leisure device use or less AI use."),
        "tables": "I.B1.4.47, 49",
        "script": "analysis/08_policy_typologies.py",
        "build": build_policy_typologies.build,
        "category": "Policy & Governance",
        "badge_class": "tag-policy",
        "cat_code": "policy",
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
        "category": "Cross-Domain Analytics",
        "badge_class": "tag-analytics",
        "cat_code": "analytics",
    },
    {
        "slug": "uncertainty-ranking",
        "title": "How much of a country ranking is real?",
        "blurb": ("Puts the published standard errors back in: 95% intervals, rank ranges, pairwise significance "
                  "tests and inverse-variance weighting for ten headline indicators. Most pairs of systems "
                  "differ, but almost no neighbours in a ranking do, and the near-census systems (Luxembourg, "
                  "Macao, Malta) can dominate any precision-weighted average."),
        "tables": "I.B1.4.1, 7, 8, 14, 43, 53, 55, 58, 59, 68",
        "script": "analysis/10_uncertainty_ranking.py",
        "build": build_uncertainty_ranking.build,
        "category": "Cross-Domain Analytics",
        "badge_class": "tag-analytics",
        "cat_code": "analytics",
    },
]


def landing_items() -> str:
    e = html.escape
    return "\n".join(
        f'<li class="card-item" data-cat="{p["cat_code"]}">'
        f'<a class="dashboard-card" href="{e(p["slug"])}/">'
        f'<div class="card-header-row">'
        f'<span class="tag {p["badge_class"]}">{e(p["category"])}</span>'
        f'<span class="arrow-action">Explore &rarr;</span>'
        f'</div>'
        f'<h2>{e(p["title"])}</h2>'
        f'<p>{e(p["blurb"])}</p>'
        f'<div class="card-footer-meta">'
        f'<span>OECD Tables {e(p["tables"])}</span>'
        f'</div>'
        f'</a></li>'
        for p in PAGES
    )


def hero_content() -> str:
    findings_html = """<div class="findings-col">
  <a class="finding-card" href="equity-gaps/">
    <span class="finding-label">Equity &amp; Access Gap</span>
    <span class="finding-num">63 / 85 Systems</span>
    <p class="finding-insight">Boys are significantly more likely than girls to report never using AI for schoolwork across 63 school systems.</p>
    <span class="finding-link">Explore Equity Gaps &rarr;</span>
  </a>
  <a class="finding-card" href="use-guidance/">
    <span class="finding-label">Policy &amp; Guidance Lag</span>
    <span class="finding-num">37.7 pp Gap</span>
    <p class="finding-insight">Average gap between students using AI for schoolwork vs. receiving classroom guidance on evaluating AI output.</p>
    <span class="finding-link">Explore Guidance Gap &rarr;</span>
  </a>
</div>"""

    # Multi-chart SVG data config for rotation
    chart_html = """<div class="chart-card" id="hero-chart-card">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;">
    <div>
      <h3 id="hero-chart-title">Student AI Use vs. Lesson Guidance</h3>
      <p class="chart-sub" id="hero-chart-sub">System-level comparison across 85 OECD systems (% of students)</p>
    </div>
    <button id="next-chart-btn" style="background:var(--surface);border:1px solid var(--line);border-radius:6px;padding:3px 8px;font-size:11px;color:var(--sec);cursor:pointer;white-space:nowrap;" title="Cycle to next chart">🔀 Next</button>
  </div>
  <div id="hero-chart-svg-wrap">
    <svg viewBox="0 0 320 150" xmlns="http://www.w3.org/2000/svg">
      <style>
        text.lbl{font-size:9.5px;font-family:sans-serif;paint-order:stroke fill;stroke:var(--bg);stroke-width:3px;stroke-linejoin:round;}
        text.axis{font-size:9px;font-family:sans-serif;fill:var(--sec);}
      </style>
      <line x1="40" y1="20" x2="300" y2="20" stroke="var(--line)" stroke-dasharray="2,2" />
      <line x1="40" y1="65" x2="300" y2="65" stroke="var(--line)" stroke-dasharray="2,2" />
      <line x1="40" y1="110" x2="300" y2="110" stroke="var(--line)" />
      <line x1="40" y1="20" x2="40" y2="110" stroke="var(--line)" />
      
      <text class="axis" x="35" y="24" text-anchor="end">80%</text>
      <text class="axis" x="35" y="69" text-anchor="end">40%</text>
      <text class="axis" x="35" y="114" text-anchor="end">0%</text>
      
      <text class="axis" x="40" y="124">0%</text>
      <text class="axis" x="170" y="124" text-anchor="middle">50%</text>
      <text class="axis" x="300" y="124" text-anchor="end">100%</text>
      <text class="axis" x="170" y="138" fill="var(--mut)" text-anchor="middle">Student AI Use (%)</text>
      
      <line x1="40" y1="110" x2="300" y2="20" stroke="var(--line)" stroke-width="1.5" stroke-dasharray="4,4" />
      
      <circle cx="288" cy="38" r="4" fill="var(--hi)" />
      <text class="lbl" x="282" y="28" font-weight="600" fill="var(--ink)" text-anchor="end">Singapore</text>
      
      <circle cx="253" cy="78" r="4" fill="var(--hi)" />
      <text class="lbl" x="261" y="81" fill="var(--sec)" text-anchor="start">China (B-S-J-Z)</text>
      
      <circle cx="196" cy="83" r="5" fill="var(--lo)" />
      <text class="lbl" x="196" y="73" font-weight="600" fill="var(--lo)" text-anchor="middle">OECD Avg</text>
      
      <circle cx="183" cy="94" r="3.5" fill="var(--hi)" />
      <text class="lbl" x="175" y="105" fill="var(--sec)" text-anchor="end">Denmark</text>
      
      <circle cx="150" cy="90" r="2.5" fill="var(--sec)" opacity="0.4" />
      <circle cx="210" cy="70" r="2.5" fill="var(--sec)" opacity="0.4" />
      <circle cx="230" cy="65" r="2.5" fill="var(--sec)" opacity="0.4" />
      <circle cx="175" cy="85" r="2.5" fill="var(--sec)" opacity="0.4" />
      <circle cx="260" cy="50" r="2.5" fill="var(--sec)" opacity="0.4" />
      <circle cx="120" cy="95" r="2.5" fill="var(--sec)" opacity="0.4" />
    </svg>
  </div>
  <div class="chart-footer">
    <span id="hero-chart-note">Dashed line = 1:1 Guidance Parity</span>
    <a id="hero-chart-link" href="use-guidance/" style="color:var(--hi);font-weight:500;text-decoration:none;">View Guidance Gap &rarr;</a>
  </div>
</div>

<script>
(function(){
  var HERO_CHARTS = [
    {
      title: "Student AI Use vs. Lesson Guidance",
      sub: "System-level comparison across 85 OECD systems (% of students)",
      note: "Dashed line = 1:1 Guidance Parity",
      linkText: "View Guidance Gap &rarr;",
      linkHref: "use-guidance/",
      svg: `<svg viewBox="0 0 320 150" xmlns="http://www.w3.org/2000/svg">
        <style>
          text.lbl{font-size:9.5px;font-family:sans-serif;paint-order:stroke fill;stroke:var(--bg);stroke-width:3px;stroke-linejoin:round;}
          text.axis{font-size:9px;font-family:sans-serif;fill:var(--sec);}
        </style>
        <line x1="40" y1="20" x2="300" y2="20" stroke="var(--line)" stroke-dasharray="2,2" />
        <line x1="40" y1="65" x2="300" y2="65" stroke="var(--line)" stroke-dasharray="2,2" />
        <line x1="40" y1="110" x2="300" y2="110" stroke="var(--line)" />
        <line x1="40" y1="20" x2="40" y2="110" stroke="var(--line)" />
        <text class="axis" x="35" y="24" text-anchor="end">80%</text>
        <text class="axis" x="35" y="69" text-anchor="end">40%</text>
        <text class="axis" x="35" y="114" text-anchor="end">0%</text>
        <text class="axis" x="40" y="124">0%</text>
        <text class="axis" x="170" y="124" text-anchor="middle">50%</text>
        <text class="axis" x="300" y="124" text-anchor="end">100%</text>
        <text class="axis" x="170" y="138" fill="var(--mut)" text-anchor="middle">Student AI Use (%)</text>
        <line x1="40" y1="110" x2="300" y2="20" stroke="var(--line)" stroke-width="1.5" stroke-dasharray="4,4" />
        <circle cx="288" cy="38" r="4" fill="var(--hi)" />
        <text class="lbl" x="282" y="28" font-weight="600" fill="var(--ink)" text-anchor="end">Singapore</text>
        <circle cx="253" cy="78" r="4" fill="var(--hi)" />
        <text class="lbl" x="261" y="81" fill="var(--sec)" text-anchor="start">China (B-S-J-Z)</text>
        <circle cx="196" cy="83" r="5" fill="var(--lo)" />
        <text class="lbl" x="196" y="73" font-weight="600" fill="var(--lo)" text-anchor="middle">OECD Avg</text>
        <circle cx="183" cy="94" r="3.5" fill="var(--hi)" />
        <text class="lbl" x="175" y="105" fill="var(--sec)" text-anchor="end">Denmark</text>
        <circle cx="150" cy="90" r="2.5" fill="var(--sec)" opacity="0.4" />
        <circle cx="210" cy="70" r="2.5" fill="var(--sec)" opacity="0.4" />
        <circle cx="230" cy="65" r="2.5" fill="var(--sec)" opacity="0.4" />
        <circle cx="175" cy="85" r="2.5" fill="var(--sec)" opacity="0.4" />
        <circle cx="260" cy="50" r="2.5" fill="var(--sec)" opacity="0.4" />
        <circle cx="120" cy="95" r="2.5" fill="var(--sec)" opacity="0.4" />
      </svg>`
    },
    {
      title: "School Phone Bans vs. In-School Leisure Use",
      sub: "Do strict phone rules correlate with reduced leisure device use? (% of students)",
      note: "Trend line: Stronger bans track lower leisure device use",
      linkText: "View Policy Governance &rarr;",
      linkHref: "policy-typologies/",
      svg: `<svg viewBox="0 0 320 150" xmlns="http://www.w3.org/2000/svg">
        <style>
          text.lbl{font-size:9.5px;font-family:sans-serif;paint-order:stroke fill;stroke:var(--bg);stroke-width:3px;stroke-linejoin:round;}
          text.axis{font-size:9px;font-family:sans-serif;fill:var(--sec);}
        </style>
        <line x1="40" y1="20" x2="300" y2="20" stroke="var(--line)" stroke-dasharray="2,2" />
        <line x1="40" y1="65" x2="300" y2="65" stroke="var(--line)" stroke-dasharray="2,2" />
        <line x1="40" y1="110" x2="300" y2="110" stroke="var(--line)" />
        <line x1="40" y1="20" x2="40" y2="110" stroke="var(--line)" />
        <text class="axis" x="35" y="24" text-anchor="end">80%</text>
        <text class="axis" x="35" y="69" text-anchor="end">40%</text>
        <text class="axis" x="35" y="114" text-anchor="end">0%</text>
        <text class="axis" x="40" y="124">0%</text>
        <text class="axis" x="170" y="124" text-anchor="middle">50%</text>
        <text class="axis" x="300" y="124" text-anchor="end">100%</text>
        <text class="axis" x="170" y="138" fill="var(--mut)" text-anchor="middle">% Schools with Phone Bans</text>
        <line x1="50" y1="45" x2="280" y2="95" stroke="var(--lo)" stroke-width="1.5" stroke-dasharray="3,3" />
        <circle cx="269" cy="88" r="4" fill="var(--hi)" />
        <text class="lbl" x="261" y="88" font-weight="600" fill="var(--ink)" text-anchor="end">UK (88%)</text>
        <circle cx="279" cy="98" r="4" fill="var(--hi)" />
        <text class="lbl" x="285" y="110" fill="var(--sec)" text-anchor="start">Japan (92%)</text>
        <circle cx="168" cy="63" r="5" fill="var(--lo)" />
        <text class="lbl" x="168" y="52" font-weight="600" fill="var(--lo)" text-anchor="middle">OECD Avg</text>
        <circle cx="131" cy="47" r="3.5" fill="var(--hi)" />
        <text class="lbl" x="123" y="44" fill="var(--sec)" text-anchor="end">Spain (35%)</text>
        <circle cx="140" cy="55" r="2.5" fill="var(--sec)" opacity="0.4" />
        <circle cx="190" cy="70" r="2.5" fill="var(--sec)" opacity="0.4" />
        <circle cx="220" cy="78" r="2.5" fill="var(--sec)" opacity="0.4" />
        <circle cx="110" cy="40" r="2.5" fill="var(--sec)" opacity="0.4" />
      </svg>`
    },
    {
      title: "Weekday vs. Weekend Device Time",
      sub: "Average student hours/day spent on digital devices for leisure",
      note: "Dashed line = Equal weekday/weekend hours",
      linkText: "View Time Use Budgets &rarr;",
      linkHref: "time-use/",
      svg: `<svg viewBox="0 0 320 150" xmlns="http://www.w3.org/2000/svg">
        <style>
          text.lbl{font-size:9.5px;font-family:sans-serif;paint-order:stroke fill;stroke:var(--bg);stroke-width:3px;stroke-linejoin:round;}
          text.axis{font-size:9px;font-family:sans-serif;fill:var(--sec);}
        </style>
        <line x1="40" y1="20" x2="300" y2="20" stroke="var(--line)" stroke-dasharray="2,2" />
        <line x1="40" y1="65" x2="300" y2="65" stroke="var(--line)" stroke-dasharray="2,2" />
        <line x1="40" y1="110" x2="300" y2="110" stroke="var(--line)" />
        <line x1="40" y1="20" x2="40" y2="110" stroke="var(--line)" />
        <text class="axis" x="35" y="24" text-anchor="end">8h</text>
        <text class="axis" x="35" y="69" text-anchor="end">4h</text>
        <text class="axis" x="35" y="114" text-anchor="end">0h</text>
        <text class="axis" x="40" y="124">0h</text>
        <text class="axis" x="170" y="124" text-anchor="middle">4h</text>
        <text class="axis" x="300" y="124" text-anchor="end">8h</text>
        <text class="axis" x="170" y="138" fill="var(--mut)" text-anchor="middle">Weekday Device Hours</text>
        <line x1="40" y1="110" x2="300" y2="20" stroke="var(--line)" stroke-width="1.5" stroke-dasharray="4,4" />
        <circle cx="186" cy="40" r="4" fill="var(--hi)" />
        <text class="lbl" x="194" y="42" font-weight="600" fill="var(--ink)" text-anchor="start">Korea (6.2h WE)</text>
        <circle cx="163" cy="52" r="4" fill="var(--hi)" />
        <text class="lbl" x="155" y="48" fill="var(--sec)" text-anchor="end">Finland (5.1h WE)</text>
        <circle cx="144" cy="60" r="5" fill="var(--lo)" />
        <text class="lbl" x="144" y="76" font-weight="600" fill="var(--lo)" text-anchor="middle">OECD Avg (4.4h)</text>
        <circle cx="108" cy="76" r="3.5" fill="var(--hi)" />
        <text class="lbl" x="100" y="78" fill="var(--sec)" text-anchor="end">Japan (3.0h)</text>
        <circle cx="130" cy="65" r="2.5" fill="var(--sec)" opacity="0.4" />
        <circle cx="155" cy="58" r="2.5" fill="var(--sec)" opacity="0.4" />
        <circle cx="170" cy="48" r="2.5" fill="var(--sec)" opacity="0.4" />
      </svg>`
    }
  ];

  var currentIdx = Math.floor(Math.random() * HERO_CHARTS.length);

  function renderChart(idx) {
    var c = HERO_CHARTS[idx];
    document.getElementById('hero-chart-title').textContent = c.title;
    document.getElementById('hero-chart-sub').textContent = c.sub;
    document.getElementById('hero-chart-note').textContent = c.note;
    var l = document.getElementById('hero-chart-link');
    l.innerHTML = c.linkText;
    l.setAttribute('href', c.linkHref);
    document.getElementById('hero-chart-svg-wrap').innerHTML = c.svg;
  }

  function initChartRotator() {
    var btn = document.getElementById('next-chart-btn');
    if (!btn) return;
    renderChart(currentIdx);
    btn.addEventListener('click', function() {
      currentIdx = (currentIdx + 1) % HERO_CHARTS.length;
      renderChart(currentIdx);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initChartRotator);
  } else {
    initChartRotator();
  }
})();
</script>"""

    return f"{findings_html}\n{chart_html}"


import json
import pandas as pd

OUT_DIR = Path(__file__).resolve().parent / "outputs"


def master_country_data():
    panel_path = OUT_DIR / "09_panel_composites.csv"
    if not panel_path.exists():
        return {}
    panel_df = pd.read_csv(panel_path).set_index("system")
    clus_df = pd.read_csv(OUT_DIR / "09c_clusters.csv").set_index("system") if (OUT_DIR / "09c_clusters.csv").exists() else pd.DataFrame()
    weak_df = pd.read_csv(OUT_DIR / "03_capacity_weakest_link.csv").set_index("system") if (OUT_DIR / "03_capacity_weakest_link.csv").exists() else pd.DataFrame()
    policy_df = pd.read_csv(OUT_DIR / "08_policy_index.csv").set_index("system") if (OUT_DIR / "08_policy_index.csv").exists() else pd.DataFrame()
    guid_df = pd.read_csv(OUT_DIR / "07_use_guidance_metrics.csv").set_index("system") if (OUT_DIR / "07_use_guidance_metrics.csv").exists() else pd.DataFrame()

    master = {}
    for sys in panel_df.index:
        p_row = panel_df.loc[sys]
        c_row = clus_df.loc[sys] if sys in clus_df.index else pd.Series(dtype=object)
        w_row = weak_df.loc[sys] if sys in weak_df.index else pd.Series(dtype=object)
        pol_row = policy_df.loc[sys] if sys in policy_df.index else pd.Series(dtype=object)
        g_row = guid_df.loc[sys] if sys in guid_df.index else pd.Series(dtype=object)

        master[sys] = {
            "science": round(float(p_row.get("science")), 1) if not pd.isna(p_row.get("science")) else None,
            "resources": round(float(p_row.get("resources")), 2) if not pd.isna(p_row.get("resources")) else None,
            "capacity": round(float(p_row.get("capacity")), 2) if not pd.isna(p_row.get("capacity")) else None,
            "learning_time_school": round(float(p_row.get("learning_time_school")), 2) if not pd.isna(p_row.get("learning_time_school")) else None,
            "leisure_at_school": round(float(p_row.get("leisure_at_school")), 2) if not pd.isna(p_row.get("leisure_at_school")) else None,
            "leisure_outside_school": round(float(p_row.get("leisure_outside_school")), 2) if not pd.isna(p_row.get("leisure_outside_school")) else None,
            "distraction": round(float(p_row.get("distraction")), 2) if not pd.isna(p_row.get("distraction")) else None,
            "rules": round(float(p_row.get("rules")), 2) if not pd.isna(p_row.get("rules")) else None,
            "ai_use": round(float(p_row.get("ai_use")), 2) if not pd.isna(p_row.get("ai_use")) else None,
            "ai_guidance": round(float(p_row.get("ai_guidance")), 2) if not pd.isna(p_row.get("ai_guidance")) else None,
            "cluster": int(c_row.get("cluster")) if ("cluster" in c_row and not pd.isna(c_row.get("cluster"))) else None,
            "cluster_label": str(c_row.get("label")) if ("label" in c_row and not pd.isna(c_row.get("label"))) else "",
            "weakest_link": str(w_row.get("weakest_absolute")) if ("weakest_absolute" in w_row and not pd.isna(w_row.get("weakest_absolute"))) else "",
            "phone_ban_pct": round(float(pol_row.get("phone_ban")), 1) if ("phone_ban" in pol_row and not pd.isna(pol_row.get("phone_ban"))) else None,
            "use_any_pct": round(float(g_row.get("use_any")), 1) if ("use_any" in g_row and not pd.isna(g_row.get("use_any"))) else None,
            "guid_pct": round(float(g_row.get("guid")), 1) if ("guid" in g_row and not pd.isna(g_row.get("guid"))) else None,
        }
    return master


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--xlsx", type=Path, default=DEFAULT_XLSX)
    ap.add_argument("--docs", type=Path, default=DOCS)
    args = ap.parse_args()

    for p in PAGES:
        out = args.docs / p["slug"] / "index.html"
        try:
            res = p["build"](args.xlsx, out)
            print(f"{p['slug']:20s} {out}: {res}")
        except FileNotFoundError as err:
            print(f"{p['slug']:20s} {out}: kept pre-rendered page ({Path(err.filename).name} missing)")
    index = args.docs / "index.html"
    master_json = json.dumps(master_country_data(), separators=(",", ":"), ensure_ascii=False)
    write_page(index, fill(load_template("landing.html"), {
        "PAGES": landing_items(),
        "HERO_CONTENT": hero_content(),
        "MASTER_DATA": master_json,
    }))
    print(f"{'landing':20s} {index}: {len(PAGES)} dashboards linked")


if __name__ == "__main__":
    main()
