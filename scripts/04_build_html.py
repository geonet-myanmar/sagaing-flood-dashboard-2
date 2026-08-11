"""
Inline the processed data into the template and emit a single self-contained
dashboard file. No external requests at runtime: the MIMU vectors are the map,
so there is no tile service, no CDN and no fetch.

Writes index.html at the repository root, which is what GitHub Pages serves
(Pages is configured to publish from the main branch root). Never hand-edit
index.html -- change src/template.html and re-run this script.
"""

import json
import os

HERE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(HERE, ".."))
PROC = os.path.join(ROOT, "data", "processed")
SRC = os.path.join(ROOT, "src", "template.html")

# key in the bundle -> processed file
LAYERS = {
    "townships":  "townships.geojson",
    "districts":  "districts.geojson",
    "context":    "context_regions.geojson",
    "rivers":     "rivers.geojson",
    "riverLines": "river_lines.geojson",
    "reservoirs": "reservoirs.geojson",
    "damPoints":  "dam_points.geojson",
    "roads":      "roads.geojson",
    "towns":      "towns.geojson",
    "villages":   "villages.geojson",
    "hospitals":  "hospitals.geojson",
    "bridges":    "bridges.geojson",
}


def main():
    flood = json.load(open(os.path.join(PROC, "flood.json"), encoding="utf-8"))
    geo = {}
    for key, fn in LAYERS.items():
        geo[key] = json.load(open(os.path.join(PROC, fn), encoding="utf-8"))

    html = open(SRC, encoding="utf-8").read()

    def inject(marker, obj):
        nonlocal html
        if marker not in html:
            raise SystemExit(f"marker {marker} not found in template")
        # </script> inside JSON string data would close the block early
        blob = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
        html = html.replace(marker, blob)

    inject("/*__FLOOD__*/", flood)
    inject("/*__GEO__*/", geo)

    out = os.path.join(ROOT, "index.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)

    size = os.path.getsize(out)
    print(f"wrote {out}")
    print(f"  {size/1_048_576:.2f} MB")
    print(f"  layers: {', '.join(f'{k}={len(v['features'])}' for k, v in geo.items())}")
    print(f"  posts={len(flood['posts'])} townships={len(flood['townships'])} "
          f"incidents={len(flood['incidents'])} timeline={len(flood['timeline'])}")


if __name__ == "__main__":
    main()
