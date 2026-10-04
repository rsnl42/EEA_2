# PISA 2025 dashboards: verification guide and candidate narratives

Everything quoted here is read from the repo's `outputs/*.csv` files, and each headline number is a row in `claims_register.csv` with the OECD table, the workbook columns to check, and the script that produced it. Where a figure is a judgement call of mine rather than an OECD number, it says so.

## 1. How to verify a number

**Where the raw data is.** `data/digital_devices_AI_chapter4.xlsx`, sheet `Digital & AI`. Rows are systems (plus an `OECD average` row); each column starts with its table, e.g. `[I.B1.4.53]`, and every estimate is followed by its own `S.E.` column. Science scores come from `data/pisa2025_table_I1.csv` (you have confirmed the Tajikistan and Uzbekistan rows).

**Three levels of checking**
1. *Claims register* (fastest). Open `claims_register.csv`, pick a row, find the columns it names in the workbook, and redo the arithmetic. About 36 rows cover the headline number on every dashboard.
2. *Spreadsheet recipes* (derived quantities):
   - #4 weekday learning hours = `Learning activities at school - Hours` + `Learning activities before and after school - Hours`, OECD row: 1.73 + 1.24 = 2.97 (the OECD text adds them the same way).
   - #6 gap = (`once or twice a week` + `every day`) for "draft texts" minus the same for "help me learn".
   - #10 difference test: z = (a - b) / sqrt(se_a^2 + se_b^2); the page calls a pair "different" when |z| > 1.96 (or about 3.4 for the strict version).
   - #1 and #2 use the OECD's own `Dif.` columns; check sign and size there.
3. *Against the printed report*: spot-check any OECD-average figure against the corresponding Volume I table.

**Cross-check against the published report (done 3 Oct 2026).** The extraction script was run end to end on the report PDF (table on PDF page 30) and reproduces `data/pisa2025_table_I1.csv` on all 828 cells, with no unparsed rows; the same table on OECD's website agrees. OECD's Executive Summary also carries Table I.6 (AI and digital snapshot). Table I.6 matches the workbook, within rounding, on five columns for the OECD average and 16 countries: capacity index, % using AI weekly to help them learn (this also confirms dashboard #6's weekly-or-more figure of 45.5%), % learning to assess AI-generated information, % in schools where cell phones are not allowed, and % in schools with subject-specific guidelines. The distraction measure on #9 and #10 is table 4.43, "peers distracted by digital devices in most or every science lesson" (OECD average 28.4%); Table I.6's "no distraction" column (39.2%) is a different measure.

**Tolerances.** Published values are rounded to 1-2 decimals, so recomputed sums can differ by 0.1. The `OECD average` row is an average of country values, not a pooled figure, so an OECD gap is the average of country gaps, not a difference of two OECD averages.

**Check first: the choices that are mine, not the OECD's**
- #4 weekday total = at school + before/after school; no weekly total is implied.
- #5 estimated hours use band midpoints (0, 0.5, 2, 4, 6, and 8 for "more than 7 hours"). The seven activities overlap and sum to far more than a day, so use hours only for comparison. "Passive" = social browsing + web browsing; "creative" = creating or editing own content.
- #6 adoption = 100 minus "never"; intensity = weekly-or-more as a share of adopters (a ratio, no interval); "draft texts" is only a proxy for offloading.
- #9 composites are means of z-scored indicators with chosen signs (see `COMPOSITES` in `analysis/09_cross_domain_panel.py`).
- Clusters (#3, #4, #6, #9) are weak: silhouettes are about 0.26, 0.24, 0.29 and 0.14-0.18. Read them as broad summaries.
- #7 compares each system with the OECD average using only its own standard error.
- #10 assumes independent, normal estimates; the strict test is a Bonferroni correction.

## 2. The dashboards at a glance

| # | Page | Source tables | Systems | Headline |
|---|------|---------------|---------|----------|
| 1 | Equity gaps | 4.26, 43, 54-59, 68 | 52-90 per cell | Advantaged students: higher AI-use index (+0.19), clear in 75 of 84 systems, none the other way |
| 2 | Infrastructure | 4.1, 4, 5, 7, 8, 11, 15 | 71-90 | Raw device counts and reported quality point in opposite directions |
| 3 | Capacity | 4.14 | 91 | Weakest OECD item: incentives for teachers, 52.7%; weakest in 35 of 91 systems |
| 4 | Time use | 4.21 | 90 (US missing) | Learning-to-leisure ratio falls 1.62 -> 0.54 -> 0.41 (school, before/after, weekend) |
| 5 | Leisure | 4.37, 4.40 | 44 | Games +8.0 pp above 3 h at weekends; creating content +0.6 pp |
| 6 | AI portfolios | 4.53 | 85 | Learning beats drafting in all 85 systems |
| 7 | Use vs guidance | 4.53, 55, 67, 68 | 85 | 22 systems: high use, low guidance |
| 8 | Policy | 4.47 and others | up to 91 | 51 fast adopters, 28 moderate/already regulated, 12 lagging |
| 9 | Cross-domain | many | 83-91 | 20 of 45 composite pairs significant |
| 10 | Uncertainty | ten indicators | 85-91 | Only 1-8% of neighbours in a ranking differ significantly |

## 3. Candidate narratives (strongest first)

**N1. Students mostly say they use AI to learn, not to draft texts.**
- OECD: 45.5% use AI weekly or more to help them learn vs 28.8% to draft (gap -16.7 pp); roughly 21% vs 32% never use it for each.
- Learning exceeds drafting in all 85 systems; the gap ranges from -34.9 to -6.9 pp, and even the smallest is far outside sampling error.
- *Weakens it:* self-reported frequency; "help me learn" is the student's own label and may include copying. Check the item wording in the report.

**N2. AI access and guidance both follow social class; gender shows no consistent pattern.**
- Advantaged minus disadvantaged students: AI-use index +0.19 (75 of 84 systems clearly positive, 0 negative); share asked to assess AI output +9.2 pp (78 of 84); share never using AI to learn -6.2 pp (74 of 84).
- Boys minus girls on the AI-use index is +0.04, with 18 systems clearly positive and 28 clearly negative.
- *Weakens it:* effect sizes in index points are modest; SES is defined within each country, so the gap is not comparable across levels of wealth.

**N3. Use and guidance move together, with a group of systems where use outruns guidance.**
- Spearman correlation between use and guidance across systems: 0.52 (n = 85). Quadrants vs the OECD average: 46 high/high, 22 high use/low guidance, 10 low/low, 7 low use/high guidance.
- *Weakens it:* guidance is measured by one narrow item (students asked to assess AI output).

**N4. At weekends, learning gives way to leisure, and the extra leisure is games rather than creating.**
- OECD learning-to-leisure ratio: 1.62 at school, 0.54 before/after school, 0.41 at weekends; weekday 2.97 h learning vs 3.37 h leisure; 30.9% spend over 5 h on weekend-day leisure.
- Games +8.0 pp above 3 h (clear in 37 of 44 systems); creating or editing content +0.6 pp; passive-to-creative estimated hours 4.2 : 1.
- *Weakens it:* #5 covers only 44 systems, and they average higher science scores than the rest; hours are midpoint approximations.

**N5. Resourcing tracks science results; "capacity" adds nothing once resources are held fixed.**
- Resources vs science +0.77 (n = 89), still +0.71 controlling for capacity. Capacity vs science +0.44 falls to -0.07 controlling for resources.
- *Weakens it:* a country-level association across 89 points. "Resources" very likely stands in for national wealth, which this data cannot separate out.

**N6. Better-resourced systems report less AI use but more guidance.**
- Resources vs AI use -0.39 (n = 84); capacity vs AI guidance +0.41; AI use vs guidance +0.51 (partial correlation holding resources fixed: 0.61).
- *Weakens it:* AI use also correlates -0.34 with science. This is an association between systems; it does not show AI use lowers scores.

**N7. "Do richer schools have better tech?" depends on what you ask.**
- Raw computer counts: poorer schools clearly ahead in 29 systems, richer in 17 (of 88). Reported shortages: private schools better by about 12 pp, clearly so in 51 of 79 systems, none the other way. Readiness: richer schools ahead in 47 systems vs 6 (of 90).
- *Weakens it:* the device ratio is per student, so small schools can look well supplied.

**N8. Deeper school policy goes with less distraction, and the least-regulated systems have more leisure device use at school.**
- Policy depth vs distraction rho = -0.32 (n = 85); share with neither ban nor guidelines vs leisure at school +0.40 (n = 90).
- *Weakens it:* 21 correlations were tested (about 1 would pass p < 0.05 by chance); the direction may run the other way, since systems with problems adopt policies; policies are principal-reported.

**N9. Method story: most of a country ranking is not real at the level readers look at.**
- Across ten indicators, 80-88% of all pairs of systems differ significantly, but only 1-8% of neighbours in the ranking do, and a typical 95% rank range is 8-14 places wide. Groups of systems are distinguishable; adjacent places are not.
- Inverse-variance weighting is dominated by near-census systems on school-level tables: Luxembourg carries 86% of the weight for "schools lacking digital resources" (pooled 5.1% vs a plain average of 31.9%).

## 4. Narrative hygiene

- **Associations between systems, not students.** Every cross-country correlation is about countries; none shows what happens to an individual.
- **Not independent confirmations.** #6, #7 and #9 are built from overlapping tables (4.53, 4.55, 4.68). That Japan, Ireland, the United Kingdom and B-S-J-Z appear as low AI users on all three is mechanical, not three pieces of evidence.
- **Multiple comparisons.** #9 has 20 of 45 pairs significant (about 2 expected by chance) and the page does not correct for this.
- **Coverage bias.** #5 covers 44 systems that average higher in science than the rest. Missing systems are missing entirely, not a few suppressed cells.
- **Self-reported hours and frequencies** differ in meaning across languages and cultures; open top bands ("more than 7 hours") are large in a few systems.
- **Significance is not size.** A z of 20 on an index gap of 0.19 is a very consistent, fairly small difference.

## 5. What I have not verified

- The page scripts for #1, #7, #8 and #9 beyond loading cleanly (I did check #2's colour logic and the data behind #1's signs).
- `analysis/09b` partial correlations in detail, #8's correlation list, and `09c`'s bootstrap code.

Resolved since the first draft: the extraction script has now been run on the report PDF; the report confirms the computer ratio is per ten students (Table I.B1.4.1; OECD average 8.8, the text says "nine") and that rural schools often have more computers per student, as #2 shows.

Fixes made during the audit: #2's "no clear difference" counts (the 71 of 77 claim is now 57 of 77), #9's cluster labelling, #10's table label for distraction, and #1's per-cell range.
