"""
Download MIMU GIS layers from the MIMU GeoNode (geonode.themimu.info) via GeoServer WFS.

Source: Myanmar Information Management Unit (MIMU) GeoNode, GeoServer WFS endpoint.
Boundaries are MIMU v9.4 (250k scale); village points are MIMU PCode v9.7.

Layers are pulled as GeoJSON in EPSG:4326. Where a layer is national in scope and
large, a BBOX restricted to Sagaing Region is applied server-side.
"""

import json
import os
import sys
import time
import urllib.parse
import urllib.request

WFS = "https://geonode.themimu.info/geoserver/wfs"
RAW = os.path.join(os.path.dirname(__file__), "..", "data", "raw")

# Generous bbox covering Sagaing Region (minx, miny, maxx, maxy in EPSG:4326)
SAGAING_BBOX = "91.8,21.0,97.4,28.8"

LAYERS = [
    # (output filename, geoserver layer, bbox or None)
    ("adm1_states.geojson",        "geonode:mmr_polbnda_adm1_250k_mimu_1",                  None),
    ("adm2_districts.geojson",     "geonode:mmr_polbnda_adm2_250k_mimu",                    None),
    ("adm3_townships.geojson",     "geonode:mmr_polbnda_adm3_250k_mimu_1",                  None),
    ("adm4_vt_sagaing.geojson",    "geonode:mmr_sag_polbnda_adm4_250k_mimu_1",              None),
    ("town_points.geojson",        "geonode:mmr_pplp1_mimu250k",                            None),
    ("village_points_sagaing.geojson", "geonode:mmr_sag_pplp2_250k_mimu",                   None),
    ("rivers_250k.geojson",        "geonode:myanmar_river_network_250k",         SAGAING_BBOX),
    ("dams_lakes.geojson",         "geonode:mmr_dam_lake_2021",                             None),
    ("hydropower_dams.geojson",    "geonode:mm_hydropowerdam_pt_v20250812",                 None),
    ("roads.geojson",              "geonode:mmr_rdsl_mimu_250k",                 SAGAING_BBOX),
    ("hospitals.geojson",          "geonode:health_facilities_myanmar2020_v20241016",       None),
    ("schools_upper.geojson",      "geonode:formal_sector_school_location_uppermyanmar_2019", SAGAING_BBOX),
    ("bridges.geojson",            "geonode:mm_bridges_pt",                                 None),
    ("sluice_gates.geojson",       "geonode:mm_sluicegates_cde_pt_v20250101",               None),
    ("rice_2023.geojson",          "geonode:msrice_myanmar_2023_1",              SAGAING_BBOX),
]


def build_url(layer, bbox=None):
    params = {
        "service": "WFS",
        "version": "1.0.0",
        "request": "GetFeature",
        "typeName": layer,
        "outputFormat": "application/json",
        "srsName": "EPSG:4326",
    }
    if bbox:
        params["bbox"] = bbox + ",EPSG:4326"
    return WFS + "?" + urllib.parse.urlencode(params)


def fetch(url, dest, tries=3):
    for attempt in range(1, tries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "sagaing-flood-dashboard/1.0"})
            with urllib.request.urlopen(req, timeout=300) as r:
                data = r.read()
            # Validate it is really GeoJSON and not a GeoServer XML error
            obj = json.loads(data)
            n = len(obj.get("features", []))
            with open(dest, "wb") as f:
                f.write(data)
            return n, len(data)
        except Exception as e:  # noqa: BLE001
            if attempt == tries:
                raise
            print(f"    retry {attempt} after error: {e}", flush=True)
            time.sleep(4)
    return 0, 0


def main():
    os.makedirs(RAW, exist_ok=True)
    failures = []
    for name, layer, bbox in LAYERS:
        dest = os.path.join(RAW, name)
        if os.path.exists(dest) and os.path.getsize(dest) > 0:
            print(f"[skip] {name} already present", flush=True)
            continue
        print(f"[get ] {name}  <- {layer}", flush=True)
        try:
            n, size = fetch(build_url(layer, bbox), dest)
            print(f"       {n:,} features, {size/1_048_576:.2f} MB", flush=True)
        except Exception as e:  # noqa: BLE001
            print(f"       FAILED: {e}", flush=True)
            failures.append((name, layer, str(e)))
    if failures:
        print("\nFAILURES:")
        for f in failures:
            print("  ", f)
        sys.exit(1)
    print("\nAll layers downloaded.")


if __name__ == "__main__":
    main()
