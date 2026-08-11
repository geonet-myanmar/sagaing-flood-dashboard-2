# Sagaing Flood Dashboard — August 2026

**Live: https://geonet-myanmar.github.io/sagaing-flood-dashboard-2/**

An interactive situation dashboard for the Mu River basin flooding in Sagaing Region, Myanmar,
built by joining 52 preserved Facebook reports to Myanmar Information Management Unit (MIMU)
administrative geography.

Between 5 and 11 August 2026 the Mu River flooded a chain of townships across central Sagaing
after releases from Thapanseik Dam met two weeks of monsoon rain. The dashboard maps what the
reports describe, keeps every claim attached to the account that made it, and shows where the
sources contradict each other rather than averaging them away.

> **This is source-level reporting, not a verified situation report.** Nothing here is
> independently confirmed. Reported death tolls range from 7 to 20 depending on the outlet, the
> date and the geographic scope being counted. A township shown without reports was not covered by
> any post in this collection — that is not evidence it was unaffected.

---

## What's in it

| Section | Contents |
|---|---|
| Overview | Headline claims as stat tiles, each naming its outlet and date |
| Map | Severity choropleth over MIMU boundaries — pan, zoom, hover, click-to-pin, layer toggles, legend isolation, three view presets, scale bar |
| Townships | The map as a sortable table: severity, reported figures, evidence basis, post counts |
| Chronology | Day-by-day account, 5–11 August, with a posts-per-day column chart |
| Mechanism | Numbered causal chain, the downstream path of the flood wave, and named places that could not be located |
| Contested figures | All 11 death-toll and 8 affected-population claims plotted with attribution and scope |
| Impacts | Villages flooded by area, reports by source type, agriculture and livestock |
| Needs & access | What was requested, and what was blocking the response |
| Sources | All 52 posts, filterable by township, source type, theme, date and free text |
| Method | Full provenance, how severity was assigned, and known limits |

The map and the source panel cross-link both ways: clicking a township filters the reports to it,
and clicking a township chip on a report selects it on the map.

---

## Architecture

The build produces **one self-contained `index.html`** (~1.4 MB) at the repository root.

It makes **no network requests at runtime** — no tile service, no CDN, no `fetch`. The MIMU vectors
*are* the map, rendered to an HTML canvas with a Web Mercator projection, custom hit-testing and
label collision avoidance. Charts are hand-built SVG. There are no JavaScript dependencies.

That means it works identically from GitHub Pages, from a `file://` URL, offline, or embedded as a
Claude Artifact.

```
src/template.html          the application: markup, CSS tokens, canvas map, charts
                           with /*__FLOOD__*/ and /*__GEO__*/ injection markers
scripts/01_download_mimu.py    pull 15 layers from the MIMU GeoNode WFS   -> data/raw/
scripts/02_build_flood_data.py structure the 52 posts                    -> data/processed/flood.json
scripts/03_process_gis.py      clip to Sagaing, simplify, join severity   -> data/processed/*.geojson
scripts/04_build_html.py       inline everything into the template        -> index.html
data/source/               the raw Facebook dataset the analysis is built from
```

**Never hand-edit `index.html`.** It is generated. Change `src/template.html` (for the app) or
`scripts/02_build_flood_data.py` (for the analysis) and re-run the build.

### Build

```bash
pip install -r requirements.txt

python scripts/01_download_mimu.py      # ~79 MB, skips layers already in data/raw/
python scripts/02_build_flood_data.py
python scripts/03_process_gis.py
python scripts/04_build_html.py
```

Only step 3 needs third-party packages (geopandas/shapely/pandas); the rest are standard library.

`data/processed/` is committed, so if you only want to change the presentation you can skip
straight to step 4. `data/raw/` is gitignored — it is 79 MB of national-extent MIMU layers and is
fully regenerable by step 1.

### Deployment

GitHub Pages serves the `main` branch root. Pushing to `main` republishes; there is no CI step and
no build server — `index.html` is committed.

```bash
python scripts/04_build_html.py
git add index.html data/processed
git commit -m "Rebuild dashboard"
git push
```

`.nojekyll` is present so Pages serves the files verbatim rather than running them through Jekyll.

---

## GIS data — all from MIMU

Retrieved from the MIMU GeoNode GeoServer WFS (`geonode.themimu.info`) in EPSG:4326.

| Layer | MIMU dataset | Used for |
|---|---|---|
| Township boundaries | `mmr_polbnda_adm3_250k_mimu_1` (v9.4) | 37 Sagaing townships, the choropleth |
| District boundaries | `mmr_polbnda_adm2_250k_mimu` (v9.4) | optional overlay, table column |
| Region boundaries | `mmr_polbnda_adm1_250k_mimu_1` (v9.4) | neighbouring-region context |
| Village tracts | `mmr_sag_polbnda_adm4_250k_mimu_1` (v9.4) | reference geography |
| Village points | `mmr_sag_pplp2_250k_mimu` (PCode v9.7) | 2,477 settlements in reported-flood townships; incident geocoding |
| Town points | `mmr_pplp1_mimu250k` (v9.4) | map labels, DMH gauge-station locations |
| River network | `myanmar_river_network` + `myanmar_river_network_250k` | Mu, Chindwin and Ayeyarwady surfaces and centrelines |
| Lakes and dams | `mmr_dam_lake_2021` | Thapanzeik reservoir |
| Hydropower dams | `mm_hydropowerdam_pt_v20250812` | Thapanzeik Dam point — the release location |
| Roads | `mmr_rdsl_mimu_250k` (2022) | main and secondary network |
| Bridges | `mm_bridges_pt` | bridges over 180 ft in Sagaing |
| Public hospitals | `health_facilities_myanmar2020_v20241016` | optional facility layer |

Boundaries are simplified to about 65 m and hydrography to about 110 m, with coordinates rounded to
4 decimal places (~11 m) — well inside the 1:250,000 source accuracy. **Joins are by P-code, never
by name.**

MIMU spells Depayin as **Tabayin**; the dashboard shows both. `scripts/02_build_flood_data.py`
carries an alias map for the other spelling variants that appear in the posts (Tantse/Taze,
Kantbalu/Kanbalu, Kyaunghla/Kyunhla, Ayardaw/Ayadaw, Min Kin/Mingin).

---

## The flood dataset

`data/processed/flood.json` holds the 52 posts — source type, follower count, language, townships,
water depth, summary, media, note and URL — plus these derived layers:

**Township assessment.** A severity class for each of the 24 townships any post covered, with the
evidence basis written out and the supporting post IDs listed.

| Class | Meaning | Count |
|---|---|---|
| Critical | Deaths reported in the township, or near-township-wide inundation with dozens of villages | 5 |
| Severe | Widespread inundation and mass displacement, no township-specific death toll | 4 |
| Moderate | Flooding reported but localised, or named in affected-area lists without detail | 5 |
| River watch | Gauge at or above danger, or inside the forecast corridor, with no inundation reported | 10 |
| No reports | Not covered by any post in this collection — absence of evidence only | 13 |

**Incidents.** Ten point locations. A place is only plotted where a MIMU record matches *inside the
township the post names* — village names repeat heavily across Myanmar, so an unconstrained name
match would misplace them. Three named places (Magyitaw, Thayethauk, Bogyone) failed that test and
are listed in the dashboard as unlocated rather than plotted.

**Also:** chronology, causal chain, contested figures, needs, response constraints, agriculture.

Figures are deliberately **not** reconciled. Sources count different areas over different windows,
so they are not additive and not directly comparable; the dashboard shows the full spread with
attribution instead of a single headline number.

---

## Design notes

The severity ramp was validated against this dashboard's own surfaces, not against defaults:

| | Moderate | Severe | Critical | Surface |
|---|---|---|---|---|
| Light | `#f0a08c` | `#dd5b47` | `#a32222` | `#fbfcfd` |
| Dark | `#f7c6b6` | `#e2836c` | `#c43a2c` | `#171b21` |

Both pass the ordinal checks (single hue, monotone lightness, ΔL ≥ 0.06, end-step contrast), and
all-pairs against the river-watch blue `#5598e7` clear the colour-vision-deficiency floor
(ΔE 14.4 light / 15.3 dark) and the normal-vision floor (16.0 / 16.6).

The dark ramp keeps the **same direction** as light — critical is the deepest red in both themes —
so hue never means the opposite thing in one of them. Critical and severe townships additionally
carry a heavier outline: a non-colour rank channel that survives greyscale, printing and full
colour-vision deficiency.

River watch sits deliberately *off* the severity ramp in blue, because a gauge reading above danger
is a different state from inundation, not a lower grade of it.

Every chart has a table-view twin, and the map's twin is the township assessment table, so no value
is reachable only by colour or only by hover.

---

## Known limits

- **Coverage follows attention, not impact.** Shwebo appears in 19 posts and Ayadaw in 4. That gap
  measures where cameras and connectivity were, not where the water was deepest. Northern townships
  are barely represented.
- **Figures are not additive.** Village and population counts come from different outlets on
  different dates covering overlapping areas.
- **Severity is editorial.** The five classes are a reading of the reports, not a measurement. A
  satellite-derived flood extent would give a different and more defensible map.
- **Nothing is verified.** Several posts carry political framing and contested allegations about the
  dam release. They are preserved as claims attributed to their authors.
- **The window closes mid-event.** Collection stopped on 11 August while the Chindwin was still
  rising and a 150–245 mm forecast covered the following week.

---

## Licence and attribution

Code is MIT licensed — see [LICENSE](LICENSE).

Geospatial layers are from the **Myanmar Information Management Unit (MIMU)** and remain subject to
[MIMU's terms of use](https://themimu.info/terms-of-use).

Source reports are publicly posted Facebook content. Each claim belongs to the account that
published it and is reproduced for documentation, not endorsed or verified by this project.
