"""Restore one new-file organizer run: python3 undo-new-files.py RUN_DIRECTORY.
Never runs without an explicit selected run. Does not touch the original image pass.
"""
import sys,json
from pathlib import Path
import organizer as o
if len(sys.argv)!=2:raise SystemExit('Provide a run directory from ongoing/runs after choosing which run to undo.')
run=Path(sys.argv[1]).resolve();assert run.parent==o.P/'runs','Not an organizer run'
rows=json.loads((run/'plan.json').read_text());c=o.db()
for r in rows:
 if r['path']==r['destination']:continue
 old=Path(r['path']);new=Path(r['destination'])
 if old.exists() and not new.exists() and o.sha(old)==r['sha256']:continue
 assert not old.exists() and new.is_file() and o.sha(new)==r['sha256'],'File changed or original path occupied; stopped before restoring'
for r in reversed(rows):
 if r['path']==r['destination']:continue
 old=Path(r['path']);new=Path(r['destination'])
 if new.exists():old.parent.mkdir(parents=True,exist_ok=True);o.exclusive_rename(new,old);assert o.sha(old)==r['sha256']
 r.update(destination=str(old),status='restored',renamed=False);o.put(c,r,'done')
o.export(c);print('Restored selected run. Rebuild dashboard. Restored paths are retained in registry so they are not automatically moved again.')
