"""Discovery-only case evidence from challenge POIs, roads and tract geometries.

No external geocoder, reference facility inventory, targets or predictions.
Road distances corroborate street-name consistency, not surveyed station error.
"""
from pathlib import Path
import json
import duckdb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/"runs/discovery_emergency"


def main():
    pairs=json.loads((OUT/"identity_candidates.json").read_text(encoding="utf-8"))
    case=next(p for p in pairs if p["a"]["id"]=="2e36387b-2cd4-40c6-9e05-3cdc293d772d")
    db=duckdb.connect();db.execute("LOAD spatial")
    roads=ROOT/"data/screening/reference/eastern-ok/eastern-ok-overture-roads.parquet"
    tracts=ROOT/"data/screening/strata/eastern-ok/eastern-ok-census-tracts.parquet"
    points=[]
    for side in ["a","b"]:
        r=case[side]
        point=db.execute("SELECT ST_X(g),ST_Y(g) FROM (SELECT ST_Transform(ST_Point(?,?),'EPSG:4326','EPSG:5070',always_xy:=true) g)",[r["lon"],r["lat"]]).fetchone()
        points.append(point)
        result=db.execute("""
            SELECT id, names.primary AS name, class,
                   ST_Distance(ST_Transform(geometry,'EPSG:4326','EPSG:5070',always_xy:=true),
                   ST_Transform(ST_Point(?,?),'EPSG:4326','EPSG:5070',always_xy:=true)) AS metres
            FROM read_parquet(?)
            WHERE bbox.xmin<=? AND bbox.xmax>=? AND bbox.ymin<=? AND bbox.ymax>=?
              AND names.primary IS NOT NULL ORDER BY metres LIMIT 6
        """,[r["lon"],r["lat"],str(roads),r["lon"]+.004,r["lon"]-.004,r["lat"]+.004,r["lat"]-.004])
        fields=[c[0] for c in result.description]
        r["nearest_named_road_segments_in_window"]=[dict(zip(fields,row)) for row in result.fetchall()]
        r["window_half_width_degrees"] = .004
        r["same_category_before"] = r["tract_same_category_records"]
        r["same_category_after_excluding_this_id"] = r["tract_same_category_records"]-1
    case["review"]={"status":"Corroborated station-identity/coordinate conflict; rural point is the stronger suspect",
        "identity_basis":"Same Station 1 name, 13425 S Bryant Ave address, postcode and phone in both supplied records",
        "spatial_basis":"Rural point is beside Western/Simmons roads; urban comparator is beside South Bryant Road in the supplied Overture road layer",
        "external_supplementary_citation":"https://oakclifffd.com/employment",
        "citation_accessed":"2026-10-07",
        "citation_use":"Current official page corroborates Station 1 identity, address and phone only. Copyrighted page is not redistributed or treated as an openly licensed dataset; quantitative and reproducible evidence uses the challenge package.",
        "limitations":"Distances are supplied-point separation and point-to-supplied-road distances. No surveyed coordinate, address-number geocode, response time, service-area loss or harmed population is established. The fire case has no zoom<=18 grid flag."}
    manifest_path=ROOT/'data/metadata/oak_cliff_roads_manifest.json'
    if not manifest_path.exists():manifest_path=ROOT/'data/metadata/main_roads_manifest.json'
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    case["road_input"]=next(r for r in manifest if r["path"].endswith("eastern-ok-overture-roads.parquet"))
    case["input_provenance"]="runs/discovery_scope/provenance.json for POIs, tracts and allowed strata fields"
    case["licensing"]="POI sources: CDLA-Permissive-2.0; Overture transportation: ODbL; challenge package: CC-BY-SA-4.0. Attribute Overture Maps Foundation and its sources including OpenStreetMap contributors, Humane Intelligence, Zindi and Radiant Earth."
    (OUT/"oak_cliff_case.json").write_text(json.dumps(case,ensure_ascii=False,indent=2),encoding="utf-8")
    xmin=min(p[0] for p in points)-1250;xmax=max(p[0] for p in points)+1250
    ymin=min(p[1] for p in points)-1750;ymax=max(p[1] for p in points)+1750
    fig,ax=plt.subplots(figsize=(11,5.2),layout="constrained")
    colors={case["a"]["GEOID"]:"#fff0db",case["b"]["GEOID"]:"#e4f0f1"}
    for geoid,fill in colors.items():
        geo=db.execute("SELECT ST_AsGeoJSON(ST_Transform(geometry,'EPSG:4326','EPSG:5070',always_xy:=true)) FROM read_parquet(?) WHERE GEOID=?",[str(tracts),geoid]).fetchone()[0]
        geometry=json.loads(geo)
        polygons=geometry["coordinates"] if geometry["type"]=="MultiPolygon" else [geometry["coordinates"]]
        for polygon in polygons:
            ax.add_patch(Polygon(polygon[0],facecolor=fill,edgecolor="#aab1b3",linewidth=.8,zorder=0))
    segments=db.execute("""SELECT names.primary,ST_AsGeoJSON(ST_Transform(geometry,'EPSG:4326','EPSG:5070',always_xy:=true)) FROM read_parquet(?)
       WHERE bbox.xmin<=? AND bbox.xmax>=? AND bbox.ymin<=? AND bbox.ymax>=?""",
       [str(roads),max(case["a"]["lon"],case["b"]["lon"])+.02,min(case["a"]["lon"],case["b"]["lon"])-.02,
        max(case["a"]["lat"],case["b"]["lat"])+.02,min(case["a"]["lat"],case["b"]["lat"])-.02]).fetchall()
    for name,geo in segments:
        g=json.loads(geo);lines=g["coordinates"] if g["type"]=="MultiLineString" else [g["coordinates"]]
        highlighted=name in {"South Western Avenue","South Bryant Road"}
        for line in lines:
            ax.plot([p[0] for p in line],[p[1] for p in line],color="#747e85" if highlighted else "#c2c8cc",lw=1.6 if highlighted else .6,zorder=1)
    a,b=points
    ax.plot([a[0],b[0]],[a[1],b[1]],ls="--",color="#ab6f61",lw=1.2,zorder=2)
    for (x,y),label,color in [(a,"BrightQuery / Rural\nconfidence 0.950\n40083600802: fire labels 1 -> 0","#b54738"),
                              (b,"Meta / Urban\nconfidence 0.920\n40083600801: fire labels 2","#197d86")]:
        ax.scatter([x],[y],s=80,color=color,edgecolor="white",linewidth=1,zorder=4)
        ax.annotate(label,(x,y),xytext=(0,30),textcoords="offset points",ha="center",va="bottom",fontsize=9,color=color,
                    bbox=dict(boxstyle="round,pad=.4",fc="white",ec="none",alpha=.95),zorder=5)
    ax.text((a[0]+b[0])/2,(a[1]+b[1])/2-450,"6.512 km between supplied points",ha="center",fontsize=10,color="#8a4035")
    ax.text(a[0],ymin+500,"South Western Avenue\n89.2 m from rural point",ha="center",fontsize=9,color="#505961")
    ax.text(b[0],ymin+500,"South Bryant Road\n24.2 m from urban point",ha="center",fontsize=9,color="#505961")
    ax.set(xlim=(xmin,xmax),ylim=(ymin,ymax),aspect="equal")
    ax.set_xticks([]);ax.set_yticks([])
    for spine in ax.spines.values():spine.set_visible(False)
    ax.plot([xmin+250,xmin+1250],[ymin+150,ymin+150],color="#38424a",lw=2)
    ax.text(xmin+750,ymin+230,"1 km",ha="center",fontsize=8)
    fig.suptitle("One fire-station identity, two high-confidence locations",fontsize=15,fontweight="bold")
    ax.set_title("Both records: Oak Cliff Station 1, 13425 S Bryant Ave, (405) 340-9115",fontsize=10,pad=12)
    fig.text(.5,.005,"Supplied Overture 2026-08-19.0 roads and tract geometry; EPSG:5070. 1 -> 0 is record-count sensitivity, not loss of fire service.",ha="center",fontsize=8)
    fig.savefig(OUT/"oak_cliff_conflict.png",dpi=180,bbox_inches="tight")
    plt.close(fig)
    print(json.dumps({"point_separation_km":case["distance_km"],"rural_tract":case["a"]["GEOID"],"population_context":case["a"]["pop_total"],"rural_count_change":[case["a"]["same_category_before"],case["a"]["same_category_after_excluding_this_id"]],"case":"runs/discovery_emergency/oak_cliff_case.json","figure":"runs/discovery_emergency/oak_cliff_conflict.png"}),flush=True)


if __name__ == "__main__":main()
