# Raw econometric data

Real source data for the 4 econometric inputs the PRD calls out (Frey-Osborne, ILOSTAT, WDI, SOC↔ISCO crosswalk). All filtered/scoped to Ghana + India where relevant.

**Status:** Optional source material for `data/countries.json`, `data/frey_osborne.json`. Currently those files use composite estimates — these raw inputs are here if Nimisha wants to swap any composites for live values.

**Don't auto-process these into the existing JSON files.** The schemas in `data/*.json` are deliberately curated; don't overwrite without coordination.

## What's here

### `frey-osborne/frey-osborne-2013.csv`
702 US SOC occupations × computerization probability from Frey & Osborne (2013), the original Future of Employment paper.

- Source: GitHub mirror at `mathias3/jobs-exposure-atlas`
- Columns: `_ - rank, _ - code (SOC), prob, Average annual wage, education, occupation, ...`
- Sample: `Data Entry Keyers, SOC 43-9021, prob=0.99`
- Use case: validates / extends `data/frey_osborne.json` raw_probability values

### `crosswalk/soc-2018-to-isco-08.csv`
SOC10 → ISCO-08 crosswalk (1,131 mapping rows).

- Source: IBS Warsaw (Frey-Cortez derivation)
- Columns: `soc10, isco08`
- Note: file name says "2018" but content is SOC-2010 mappings. This is correct — Frey-Osborne uses 2010-SOC. BLS's official SOC-2018 file was Akamai-blocked.
- Bonus: `crosswalk/sarah-cortez-isco-soc-frey.xlsx` has ISCO+SOC+Frey-Osborne pre-joined into one sheet.

### `ilostat/EAR_4MTH_SEX_OCU_NB_GHA_IND.csv`
ILOSTAT mean monthly earnings by occupation, filtered to GHA + IND.

- Source: ILOSTAT rplumber API
- Indicator: `EAR_EMTA_SEX_OCU_NB_A` (the `EAR_4MTH_*` code in the PRD is deprecated; this is the current equivalent — same metric)
- 728 rows, both Ghana and India represented
- Sample: `GHA, EAR_EMTA_SEX_OCU_NB, SEX_T, OCU_SKILL_TOTAL, 2024, 2578.889 GHS`
- Note: ILOSTAT publishes wages by `OCU_SKILL_*` skill-level groupings AND by ISCO 2-digit. NOT typically at 4-digit ISCO. So you may need to map your 14 4-digit ISCO codes back to their 2-digit parent for matches.
- Use case: replaces `countries.GH.wage_data` and `countries.IN.wage_data` composite values with real anchored numbers.

### `wdi/wdi-*.json`
World Bank WDI for Ghana + India, 7 indicators each:

- `SL.EMP.TOTL.SP.ZS` — employment-to-population ratio (15+, total, %)
- `SL.AGR.EMPL.ZS` — agriculture employment (% of total)
- `SL.IND.EMPL.ZS` — industry employment (%)
- `SL.SRV.EMPL.ZS` — services employment (%)
- `NV.AGR.TOTL.KD.ZG` — agriculture value added growth (annual %)
- `NV.IND.TOTL.KD.ZG` — industry growth (%)
- `NV.SRV.TOTL.KD.ZG` — services growth (%)
- Source: World Bank API v2, JSON
- Use case: validates / replaces `countries.<CC>.sectors.<sector>.{growth_annual, share_employment}` with live WDI values.

## How to use (if at all)

If you want to stay with composite estimates, leave this folder alone. It's reference material.

If you want to swap in real values, write a small Python script that:

1. Reads `wdi-SL.AGR.EMPL.ZS.json` → extract latest year's value for GHA → write to `countries.GH.sectors.agriculture.share_employment`
2. Reads `wdi-NV.AGR.TOTL.KD.ZG.json` → extract trailing 5y avg for GHA → write to `countries.GH.sectors.agriculture.growth_annual`
3. Same for IND, same for industry/services.
4. For wage_data: the ILOSTAT file is only at 2-digit ISCO. Map 4-digit codes to their 2-digit parent (e.g. `7421` → `74`, then look up `OCU_ISCO08_74`).

Keep the `_meta.honesty_note` updated: if you swap in real values for some fields and keep composites for others, say so explicitly.

## What's NOT here

- ESCO classification bundle — too big to commit (~50MB). If `data/esco_skills.json` needs the canonical `esco_uri` populated, download the ESCO v1.2.1 EN bundle from https://esco.ec.europa.eu/en/use-esco/download and grep the `skills_en.csv` file by skill_label.
