"""
Inline the processed data into the template and emit the dashboard.

src/template.html is a BODY FRAGMENT and the single source of truth. It carries
no <html>/<head>/<body> of its own, because the Claude Artifact platform wraps
the file in its own document skeleton at publish time. Two outputs come out of
here, for the two delivery targets:

  index.html               complete standalone document -- what GitHub Pages
                           serves. Adds the doctype (without it the browser
                           renders in quirks mode), charset, viewport (without
                           it phones lay the page out at desktop width), an
                           inline SVG favicon (so no favicon.ico 404), social
                           preview tags and a minimal reset.

  dist/artifact-body.html  the same page as a fragment, for publishing as a
                           Claude Artifact.

Both are fully self-contained: no tile service, no CDN, no fetch. The MIMU
vectors are the map.

Never hand-edit either output -- change src/template.html and re-run this.
"""

import json
import os
import re

HERE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(HERE, ".."))
PROC = os.path.join(ROOT, "data", "processed")
SRC = os.path.join(ROOT, "src", "template.html")
DIST = os.path.join(ROOT, "dist")

SITE = "https://geonet-myanmar.github.io/sagaing-flood-dashboard-2/"

# A wave glyph, inline so the browser never requests /favicon.ico
FAVICON = (
    "data:image/svg+xml,"
    "%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E"
    "%3Crect width='100' height='100' rx='18' fill='%23171b21'/%3E"
    "%3Cpath d='M8 62c11 0 11-10 22-10s11 10 22 10 11-10 22-10 11 10 18 10' "
    "fill='none' stroke='%235598e7' stroke-width='9' stroke-linecap='round'/%3E"
    "%3Cpath d='M8 40c11 0 11-10 22-10s11 10 22 10 11-10 22-10 11 10 18 10' "
    "fill='none' stroke='%23c43a2c' stroke-width='9' stroke-linecap='round'/%3E"
    "%3C/svg%3E"
)

HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<meta name="color-scheme" content="light dark" />
<meta name="theme-color" content="#eef1f4" media="(prefers-color-scheme: light)" />
<meta name="theme-color" content="#0e1116" media="(prefers-color-scheme: dark)" />
{title}
{description}
<meta name="author" content="geonet-myanmar" />
<link rel="icon" href="{favicon}" />
<meta property="og:type" content="website" />
<meta property="og:url" content="{site}" />
<meta property="og:title" content="{og_title}" />
<meta property="og:description" content="{og_desc}" />
<meta name="twitter:card" content="summary" />
<style>
/* minimal reset -- the Artifact platform supplies its own; standalone needs one */
*, *::before, *::after {{ box-sizing: border-box; }}
html {{ -webkit-text-size-adjust: 100%; }}
body {{ margin: 0; }}
img, svg, canvas {{ max-width: 100%; }}
button, input, select, textarea {{ font: inherit; color: inherit; }}
</style>
</head>
<body>
"""

FOOT = "\n</body>\n</html>\n"

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

    # Lift <title>/<meta name=description> out of the fragment into a real <head>.
    m_title = re.search(r"<title>(.*?)</title>", html, re.S)
    m_desc = re.search(r'<meta name="description" content="(.*?)"\s*/?>', html, re.S)
    if not m_title:
        raise SystemExit("template is missing a <title>")
    title_txt, desc_txt = m_title.group(1).strip(), (m_desc.group(1).strip() if m_desc else "")

    body = html
    for m in (m_title, m_desc):
        if m:
            body = body.replace(m.group(0), "", 1)
    body = body.lstrip("\n")

    # 1. standalone document for GitHub Pages
    doc = HEAD.format(
        title=m_title.group(0),
        description=(m_desc.group(0) if m_desc else ""),
        favicon=FAVICON, site=SITE,
        og_title=title_txt, og_desc=desc_txt,
    ) + body + FOOT
    out = os.path.join(ROOT, "index.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(doc)

    # 2. fragment for the Claude Artifact platform, which adds its own skeleton
    os.makedirs(DIST, exist_ok=True)
    frag = os.path.join(DIST, "artifact-body.html")
    with open(frag, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"wrote {out}")
    print(f"  {os.path.getsize(out)/1_048_576:.2f} MB  (standalone, GitHub Pages)")
    print(f"wrote {frag}")
    print(f"  {os.path.getsize(frag)/1_048_576:.2f} MB  (fragment, Claude Artifact)")
    print(f"  layers: {', '.join(f'{k}={len(v['features'])}' for k, v in geo.items())}")
    print(f"  posts={len(flood['posts'])} townships={len(flood['townships'])} "
          f"incidents={len(flood['incidents'])} timeline={len(flood['timeline'])}")


if __name__ == "__main__":
    main()
