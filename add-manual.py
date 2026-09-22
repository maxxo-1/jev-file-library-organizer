import sys,json
import organizer
p=organizer.P/'manual.json';d=json.loads(p.read_text()) if p.exists() else {}
for line in sys.stdin.read().splitlines():
 if not line.strip():continue
 i,c,t=line.split('|',2);d[i]={'category':c,'title':t,'source':'manual visual inspection'}
p.write_text(json.dumps(d,indent=2));print('Visual decisions',len(d))
