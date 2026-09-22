import tempfile,json,os,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
bootstrap=Path(tempfile.mkdtemp(prefix='organizer-config-'));config=bootstrap/'config.json';config.write_text(json.dumps({'roots':[str(bootstrap/'inbox')],'state_dir':str(bootstrap/'state')}));os.environ['ORGANIZER_CONFIG']=str(config)
import organizer as o
with tempfile.TemporaryDirectory(prefix='organizer-test-') as folder:
 base=Path(folder);o.P=base/'work';o.P.mkdir();o.BASE=base;o.ROOTS=[base/'inbox'];o.ROOTS[0].mkdir();(o.P/'runs').mkdir();(o.P/'review-queue.json').write_text('[]');c=o.db()
 src=o.ROOTS[0]/'download.pdf';src.write_bytes(b'Original immutable document bytes');os.utime(src,(1,1))
 o.scan(c);pending=o.pending(c);assert len(pending)==1;r=pending[0];dst=o.ROOTS[0]/'Organized PDFs'/'Business and Leadership'/'Planning document.pdf';r.update(destination=str(dst),title='Planning document',category='Business and Leadership',protected=False,renamed=True,needs_review=False,decision_source='test');o.atomic(o.P/'plan.json',[r]);o.apply(c)
 assert dst.read_bytes()==b'Original immutable document bytes' and not src.exists();o.scan(c);assert len(o.pending(c))==0
 # Atomic overwrite protection.
 a=base/'a';b=base/'b';a.write_bytes(b'a');b.write_bytes(b'b')
 try:o.exclusive_rename(a,b);raise AssertionError('Overwrite permitted')
 except OSError:pass
 assert a.read_bytes()==b'a' and b.read_bytes()==b'b'
 # Crash recovery after rename but before database commit.
 src2=o.ROOTS[0]/'video.mp4';src2.write_bytes(b'video bytes');dst2=o.ROOTS[0]/'Organized Videos'/'demo.mp4';dst2.parent.mkdir();r2=dict(r,id=r['id']+1,path=str(src2),destination=str(dst2),size=11,sha256=o.sha(src2));o.put(c,r2,'moving');o.exclusive_rename(src2,dst2);o.atomic(o.P/'plan.json',[r2])
 # Unique run name despite tests running in same second.
 import shutil
 shutil.rmtree(o.P/'runs');(o.P/'runs').mkdir();o.apply(c);assert c.execute('SELECT status FROM files WHERE id=?',(r2['id'],)).fetchone()[0]=='done'
 # Symlinks are never scanned; project assets are protected.
 (o.ROOTS[0]/'alias.pdf').symlink_to(dst);o.scan(c);assert len(o.pending(c))==0
 assert o.protected({'path':str(o.ROOTS[0]/'assets'/'logo.png'),'root':str(o.ROOTS[0])})
 src.write_bytes(b'New download with reused original filename');os.utime(src,(1,1));o.scan(c);assert len(o.pending(c))==1 and o.pending(c)[0]['sha256']!=r['sha256']
 assert o.generic('download (3)',.9) and not o.generic('Customer experience guide',.9)
print('PASS: unchanged bytes, idempotent scan, atomic collision refusal, crash recovery, symlink exclusion, project preservation')
