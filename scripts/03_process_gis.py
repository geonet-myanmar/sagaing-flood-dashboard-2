"""
Clip, simplify and join the MIMU layers into compact GeoJSON for the dashboard.

The dashboard renders MIMU vectors directly on an HTML canvas -- there is no
basemap tile service involved -- so these files are the map. Geometry is
simplified to a tolerance appropriate for a region-scale view and coordinates
are rounded to 4 decimal places (~11 m), which is well inside the 1:250,000
source accuracy of the boundary layers.
"""

import json
import os

import geopandas as gpd
import pandas as pd
from shapely.geometry import shape  # noqa: F401  (kept for clarity)

HERE = os.path.dirname(__file__)
RAW = os.path.join(HERE, "..", "data", "raw")
OUT = os.path.join(HERE, "..", "data", "processed")

SAGAING = "MMR005"
PREC = 4          # coordinate decimal places
TOL_ADM = 0.0006  # ~65 m simplification for admin polygons
TOL_HYD = 0.0010  # ~110 m for hydrography / roads


def load(name):
    return gpd.read_file(os.path.join(RAW, name))


def round_coords(obj, p=PREC):
    if isinstance(obj, list):
        if obj and isinstance(obj[0], (int, float)):
            return [round(float(v), p) for v in obj]
        return [round_coords(v, p) for v in obj]
    return obj


def dump(gdf, path, keep, drop_empty=True):
    """Write a GeoDataFrame to compact GeoJSON with only `keep` properties."""
    gdf = gdf.copy()
    if drop_empty:
        gdf = gdf[~gdf.geometry.is_empty & gdf.geometry.notna()]
    feats = []
    for _, row in gdf.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue
        g = json.loads(gpd.GeoSeries([geom]).to_json())["features"][0]["geometry"]
        g["coordinates"] = round_coords(g["coordinates"])
        props = {}
        for k in keep:
            v = row.get(k)
            if v is None or (isinstance(v, float) and pd.isna(v)):
                continue
            if isinstance(v, float):
                v = round(v, 5)
            props[k] = v
        feats.append({"type": "Feature", "properties": props, "geometry": g})
    fc = {"type": "FeatureCollection", "features": feats}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(fc, f, ensure_ascii=False, separators=(",", ":"))
    kb = os.path.getsize(path) / 1024
    print(f"  -> {os.path.basename(path):32s} {len(feats):6,d} features  {kb:8.1f} KB")
    return fc


def main():
    os.makedirs(OUT, exist_ok=True)
    flood = json.load(open(os.path.join(OUT, "flood.json"), encoding="utf-8"))
    tinfo = {t["name"]: t for t in flood["townships"]}

    # ---------------------------------------------------------------- townships
    print("townships")
    ts = load("adm3_townships.geojson")
    sag = ts[ts.ST_PCODE == SAGAING].copy()
    sag["geometry"] = sag.geometry.simplify(TOL_ADM, preserve_topology=True)

    def sev(name):
        return tinfo.get(name, {}).get("severity", "none")

    sag["sev"] = sag.TS.map(sev)
    sag["mentions"] = sag.TS.map(lambda n: tinfo.get(n, {}).get("mentions", 0))
    sag["alias"] = sag.TS.map(lambda n: tinfo.get(n, {}).get("alias") or "")
    # representative point for labels (inside the polygon, unlike a centroid)
    rp = sag.geometry.representative_point()
    sag["lx"] = rp.x.round(4)
    sag["ly"] = rp.y.round(4)
    sag["area_km2"] = sag.to_crs(32646).geometry.area.div(1e6).round(0)
    dump(sag, os.path.join(OUT, "townships.geojson"),
         ["TS", "TS_MMR", "TS_PCODE", "DT", "ST", "sev", "mentions", "alias", "lx", "ly", "area_km2"])

    outline = sag.dissolve().geometry.iloc[0]
    sag_gdf = gpd.GeoDataFrame(geometry=[outline], crs=4326)

    # ---------------------------------------------------------------- districts
    print("districts")
    dt = load("adm2_districts.geojson")
    dts = dt[dt.ST_PCODE == SAGAING].copy()
    dts["geometry"] = dts.geometry.simplify(TOL_ADM, preserve_topology=True)
    dump(dts, os.path.join(OUT, "districts.geojson"), ["DT", "DT_MMR", "DT_PCODE"])

    # ------------------------------------------------- neighbouring regions
    print("context regions")
    a1 = load("adm1_states.geojson")
    ctx = a1[a1.ST_PCODE != SAGAING].copy()
    # keep only regions that touch or sit near Sagaing, for map context
    near = ctx[ctx.geometry.intersects(outline.buffer(0.15))].copy()
    near["geometry"] = near.geometry.simplify(0.004, preserve_topology=True)
    dump(near, os.path.join(OUT, "context_regions.geojson"), ["ST", "ST_PCODE"])

    a1s = a1[a1.ST_PCODE == SAGAING].copy()
    a1s["geometry"] = a1s.geometry.simplify(TOL_ADM, preserve_topology=True)
    dump(a1s, os.path.join(OUT, "region.geojson"), ["ST", "ST_PCODE"])

    # ---------------------------------------------------------------- rivers
    print("rivers")
    clip_to = outline.buffer(0.05)
    rv = load("rivers_detail.geojson")           # water-surface polygons, named
    rv = rv[rv.geometry.intersects(clip_to)].copy()
    rv["geometry"] = rv.geometry.intersection(clip_to).simplify(TOL_HYD, preserve_topology=True)
    rv["NAME"] = rv.NAME.fillna("UNK").replace({"": "UNK"})
    rv["nm"] = rv.NAME.map(lambda n: {"MU": "Mu River", "CHINDWIN": "Chindwin River",
                                      "IRRAWADDY": "Ayeyarwady River"}.get(n, ""))
    rv["major"] = rv.nm.ne("").astype(int)
    dump(rv, os.path.join(OUT, "rivers.geojson"), ["nm", "major"])

    # named centrelines for labelling the big rivers
    rl = load("rivers_250k.geojson")
    rl = rl[rl.geometry.intersects(clip_to)].copy()
    rl["geometry"] = rl.geometry.intersection(clip_to).simplify(TOL_HYD, preserve_topology=True)
    dump(rl, os.path.join(OUT, "river_lines.geojson"), ["Name"])

    # ---------------------------------------------------------------- dams
    print("dams and reservoirs")
    dl = load("dams_lakes.geojson")
    dl = dl[dl.geometry.intersects(clip_to)].copy()
    dl["geometry"] = dl.geometry.simplify(0.0004, preserve_topology=True)
    dl["key"] = dl.Name.fillna("").str.contains("Thapanzeik|Thapanchaung", case=False, regex=True).astype(int)
    dump(dl, os.path.join(OUT, "reservoirs.geojson"), ["Name", "Type", "key"])

    hp = load("hydropower_dams.geojson")
    hp = hp[hp.geometry.intersects(outline.buffer(0.3))].copy()
    dump(hp, os.path.join(OUT, "dam_points.geojson"), ["cl_nmEng", "statOperat"])

    # ---------------------------------------------------------------- roads
    print("roads")
    rd = load("roads.geojson")
    rd = rd[rd.geometry.intersects(clip_to)].copy()
    rd["geometry"] = rd.geometry.intersection(clip_to).simplify(TOL_HYD, preserve_topology=True)
    rd = rd[rd.Road_Type.isin(["Main", "Secondary"]) | rd.Route.fillna("").str.startswith("AH")]
    dump(rd, os.path.join(OUT, "roads.geojson"), ["Road_Type", "Route"])

    # ---------------------------------------------------------------- towns
    print("towns")
    tp = load("town_points.geojson")
    tp = tp[tp.SD_Pcode == SAGAING].copy()
    tp["sev"] = tp.Township.map(sev)
    dump(tp, os.path.join(OUT, "towns.geojson"),
         ["Town", "Town_MMR4", "Township", "District", "Level", "sev"])

    # ---------------------------------------------------------------- villages
    print("villages")
    vp = load("village_points_sagaing.geojson")
    vp["sev"] = vp.TS.map(sev)
    keep_sev = {"critical", "severe", "moderate"}
    vsel = vp[vp.sev.isin(keep_sev)].copy()
    print(f"     {len(vsel):,} villages in reported-flood townships "
          f"(of {len(vp):,} in Sagaing)")
    dump(vsel, os.path.join(OUT, "villages.geojson"),
         ["VILLAGE", "VLG_MMR", "TS", "VT", "sev"])

    # ------------------------------------------------- named villages in posts
    named = ["Magyitaw", "Htankone", "Shwe Hlan", "Thayethauk", "Daunggyi",
             "Bogyone", "Nyaungpinwun"]
    hits = []
    for n in named:
        m = vp[vp.VILLAGE.str.replace(" ", "", regex=False).str.lower()
               == n.replace(" ", "").lower()]
        for _, r in m.iterrows():
            hits.append(dict(query=n, village=r.VILLAGE, ts=r.TS, dt=r.DT,
                             lon=round(r.Longitude, 4), lat=round(r.Latitude, 4)))
    with open(os.path.join(OUT, "named_places.json"), "w", encoding="utf-8") as f:
        json.dump(hits, f, ensure_ascii=False, indent=1)
    print(f"  -> named_places.json  {len(hits)} matches for {len(named)} names in posts")

    # ---------------------------------------------------------------- facilities
    print("facilities")
    hs = load("hospitals.geojson")
    hs = hs[hs.SR_PCODE == SAGAING].copy()
    hs["sev"] = hs.TS_en.map(sev)
    dump(hs, os.path.join(OUT, "hospitals.geojson"),
         ["nmHsp_eng", "lvlHsp_eng", "bedClass", "TS_en", "sev"])

    br = load("bridges.geojson")
    br = br[br.nmSReng == "Sagaing"].copy()
    br["sev"] = br.nmTsEng.map(sev)
    dump(br, os.path.join(OUT, "bridges.geojson"),
         ["nmEng", "length_ft", "nmTsEng", "sev"])

    print("\ndone.")


if __name__ == "__main__":
    main()
