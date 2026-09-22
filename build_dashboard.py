#!/usr/bin/env python3
"""Build the local searchable dashboard from the organizer state directory."""

from pathlib import Path
import collections, concurrent.futures, csv, datetime, json
from PIL import Image, ImageDraw, ImageOps
import organizer

BASE = Path(__file__).resolve().parent
STATE = organizer.P
DASHBOARD = BASE / "dashboard"
THUMBNAILS = DASHBOARD / "thumbnails"
DASHBOARD.mkdir(exist_ok=True);THUMBNAILS.mkdir(exist_ok=True)
rows_path = STATE / "all-results.json"
if not rows_path.exists():raise SystemExit("No organized catalog exists yet. Run organizer.py apply or export first.")
rows = json.loads(rows_path.read_text());Image.MAX_IMAGE_PIXELS = None

def verify(row):
    path=Path(row["destination"])
    if not path.is_file() or path.is_symlink():raise FileNotFoundError(path)
    if path.stat().st_size!=row["size"] or organizer.sha(path)!=row["sha256"]:raise ValueError(f"Fingerprint mismatch: {path}")
    return row["id"]

with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:verified=list(pool.map(verify,rows))
summary={"total":len(rows),"moved":sum(r["path"]!=r["destination"] for r in rows),"renamed":sum(bool(r.get("renamed")) for r in rows),"protected":sum(bool(r.get("protected")) for r in rows),"review":sum(bool(r.get("needs_review")) for r in rows),"verified":len(verified),"categories":dict(collections.Counter(r["category"] for r in rows)),"roots":dict(collections.Counter(Path(r["root"]).name for r in rows)),"types":dict(collections.Counter(r.get("kind","Image") for r in rows)),"verified_at":datetime.datetime.now().isoformat(timespec="seconds")}
(STATE/"verification.json").write_text(json.dumps(summary,indent=2))
fields=["id","kind","category","title","path","destination","renamed","protected","needs_review","decision_source","status","sha256"]
for name,subset in [("catalog.csv",rows),("review.csv",[r for r in rows if r.get("needs_review")])]:
    with (BASE/name).open("w",newline="") as output:
        writer=csv.DictWriter(output,fieldnames=fields,extrasaction="ignore");writer.writeheader();writer.writerows(subset)

def thumbnail(row):
    output=THUMBNAILS/f"{row['id']:05d}.jpg"
    if output.exists():return
    preview=STATE/"extracted"/f"{row['id']:05d}.jpg";source=preview if preview.exists() else Path(row["destination"])
    try:
        with Image.open(source) as image:
            image=ImageOps.exif_transpose(image);image.thumbnail((400,280));background=Image.new("RGB",image.size,"#f2f1ed")
            if image.mode in ("RGBA","LA") or "transparency" in image.info:image=image.convert("RGBA");background.paste(image,mask=image.getchannel("A"))
            else:background.paste(image.convert("RGB"))
            background.save(output,quality=80,optimize=True)
    except Exception:
        image=Image.new("RGB",(400,280),"#f2f1ed");ImageDraw.Draw(image).text((25,120),"Preview unavailable",fill="#222222");image.save(output)

with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(thumbnail,rows))
metadata_dir=STATE/"metadata"/"cache";edits_path=STATE/"metadata"/"user-edits.json";edits=json.loads(edits_path.read_text()) if edits_path.exists() else {};data=[]
for row in rows:
    path=Path(row["destination"]);metadata_path=metadata_dir/f"{row['id']:05d}.json";metadata=json.loads(metadata_path.read_text()) if metadata_path.exists() else {}
    if metadata and (metadata.get("sha256")!=row["sha256"] or metadata.get("schema_version")!=1):metadata={}
    metadata.update(edits.get(str(row["id"]),{}))
    data.append({"id":row["id"],"added_run":row.get("added_run",""),"new":bool(row.get("new")),"latest":bool(row.get("latest")),"name":path.name,"old":Path(row["path"]).name,"title":row.get("title") or path.stem,"category":row["category"],"root":Path(row["root"]).name,"path":str(path),"original":row["path"],"url":path.as_uri(),"renamed":bool(row.get("renamed")),"protected":bool(row.get("protected")),"review":bool(row.get("needs_review")),"method":row.get("decision_source",""),"bytes":row["size"],"kind":row.get("kind","Image"),"pages":row.get("pages"),"duration":row.get("duration"),"evidence":row.get("evidence_note",""),"sha256":row["sha256"],"summary":metadata.get("summary",row.get("title") or path.stem),"keywords":metadata.get("keywords",[]),"entities":metadata.get("entities",[]),"visible_content":metadata.get("visible_content",[]),"purpose":metadata.get("purpose","unknown"),"metadata_tags":metadata.get("tags",{}),"metadata_ready":bool(metadata),"metadata_model":metadata.get("model","")})
token_path=STATE/"dashboard-token"
if not token_path.exists():
    import secrets
    token_path.write_text(secrets.token_urlsafe(32));token_path.chmod(0o600)
template=(BASE/"dashboard-template.html").read_text();html=template.replace("__DATA__",json.dumps(data,ensure_ascii=False).replace("</","<\\/")).replace("__SUMMARY__",json.dumps(summary)).replace("__ACTION_TOKEN__",json.dumps(token_path.read_text().strip()))
(DASHBOARD/"index.html").write_text(html)
(BASE/"LIBRARY-REPORT.md").write_text(f"# Organized file library\n\nVerified {summary['verified_at']} local time.\n\n- {summary['total']:,} files cataloged.\n- {summary['moved']:,} moved into categories.\n- {summary['renamed']:,} given descriptive names.\n- {summary['protected']:,} project assets kept in place.\n- {summary['review']:,} flagged for review.\n\nEvery listed file passed a current SHA-256 check. Source bytes were not edited, and duplicates were retained.\n\n## Undo\n\nUse `undo-new-files.py` with one selected directory under the state folder's `runs/` directory. Undo refuses changed files and occupied original paths.\n")
print(f"Dashboard ready: {len(data)} files; {len(verified)} fingerprints verified")
