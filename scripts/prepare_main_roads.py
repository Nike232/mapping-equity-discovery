"""Fetch only the five current, permitted Overture drivable-road extracts."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import json
import xml.etree.ElementTree as ET
import requests
import argparse
from prepare_screen import download, PREFIX
from prepare_discovery_scope import sha256

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--only-eastern-ok',action='store_true',help='Download only the road input needed by the discovery fire case')
    args=parser.parse_args()
    response = requests.get("https://s3.us-west-2.amazonaws.com/us-west-2.opendata.source.coop",
                            params={"list-type":"2", "prefix":PREFIX+"reference/"}, timeout=30)
    response.raise_for_status()
    ns = {"s":"http://s3.amazonaws.com/doc/2006-03-01/"}
    items = []
    for node in ET.fromstring(response.content).findall("s:Contents",ns):
        key = node.find("s:Key",ns).text
        if key.endswith("-overture-roads.parquet"):
            items.append({"key":key,"bytes":int(node.find("s:Size",ns).text),
                          "modified":node.find("s:LastModified",ns).text})
    if len(items) != 5:
        raise ValueError("Expected five permitted road extracts")
    if args.only_eastern_ok:
        items=[item for item in items if '/eastern-ok/' in item['key']]
    print("PERMITTED_ROADS_BYTES",sum(item["bytes"] for item in items),flush=True)
    with ThreadPoolExecutor(max_workers=3) as pool:
        paths = list(pool.map(download,items))
    manifest = [{**item,"path":path.relative_to(ROOT).as_posix(),
                 "url":"https://data.source.coop/"+item["key"],"sha256":sha256(path)}
                for item,path in zip(items,paths)]
    filename='oak_cliff_roads_manifest.json' if args.only_eastern_ok else 'main_roads_manifest.json'
    (ROOT/'data/metadata'/filename).write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print('MANIFEST','data/metadata/'+filename,flush=True)


if __name__ == "__main__":
    main()
