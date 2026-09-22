import json,sys
from pathlib import Path
from PIL import Image,ImageDraw
import organizer as o
p=o.P;manual=json.loads((p/'manual.json').read_text()) if (p/'manual.json').exists() else {};items=json.loads((p/('batch.json' if (p/'batch.json').exists() else 'extract-batch.json')).read_text())
rows=[]
for r in items:
 if str(r['id']) in manual:continue
 f=p/'decisions'/f"{r['id']:05d}.json"
 if not f.exists():continue
 dec=json.loads(f.read_text());a=dec['result']['answers'];gen=o.generic(Path(r['path']).stem,a['existing_name']['noul']);e=json.loads((p/'extracted'/f"{r['id']:05d}.json").read_text())
 if o.kind(r['path'])=='Video' or a['category']['choice']=='Needs Visual Review' or a['category']['confidence']<.6 or (gen and a['title']['choice']=='none') or e.get('error'):rows.append(dict(r,category=a['category']['choice'],title='' if a['title']['choice']=='none' else dec['candidates'][int(a['title']['choice'])]))
rows=rows[:24];im=Image.new('RGB',(1920,1800),'#eeeeee');draw=ImageDraw.Draw(im)
for n,r in enumerate(rows):
 x=n%4*480;y=n//4*300;draw.text((x+5,y+3),str(r['id'])+' '+Path(r['path']).stem[:57],fill='black');draw.text((x+5,y+18),r['category'],fill='black');draw.text((x+5,y+33),r['title'][:67],fill='black')
 files=sorted((p/'extracted').glob(f"{r['id']:05d}-frame*.jpg"))
 files=[files[0],files[len(files)//2]] if files else [p/'extracted'/f"{r['id']:05d}.jpg"]
 for j,f in enumerate(files):
  try:
   a=Image.open(f);a.thumbnail((465//len(files),245));im.paste(a,(x+5+j*235,y+50))
  except:draw.text((x+10,y+100),'Preview unavailable',fill='black')
im.save(p/'review.jpg');o.atomic(p/'review-ids.json',[r['id'] for r in rows]);print([r['id'] for r in rows])
