import unittest,tempfile,json,hashlib,sqlite3,subprocess,os
from pathlib import Path
from unittest.mock import patch
bootstrap=Path(tempfile.mkdtemp(prefix='organizer-config-'));config=bootstrap/'config.json';config.write_text(json.dumps({'roots':[str(bootstrap/'inbox')],'state_dir':str(bootstrap/'state')}));os.environ['ORGANIZER_CONFIG']=str(config)
import server
class Actions(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name).resolve();server.o.ROOTS=[self.root];self.old_p=server.P;self.old_op=server.o.P;self.old_actions=server.ACTIONS;server.P=self.root/'service';server.P.mkdir();server.o.P=self.root/'ongoing';server.o.P.mkdir();server.ACTIONS=server.o.P/'dashboard-actions';server.ACTIONS.mkdir()
  self.c=sqlite3.connect(':memory:');self.c.execute('CREATE TABLE files(id INTEGER PRIMARY KEY,source TEXT,destination TEXT,status TEXT,data TEXT)')
  self.src=self.root/'example.png';self.src.write_bytes(b'harmless dashboard file-action test')
  self.r=dict(id=-1,path=str(self.src),destination=str(self.src),needs_review=True,sha256=server.o.sha(self.src),title='Test',renamed=False)
  server.o.put(self.c,self.r,'done')
 def tearDown(self):self.c.close();server.P=self.old_p;server.o.P=self.old_op;server.ACTIONS=self.old_actions;self.tmp.cleanup()
 def call(self,action='rename',name='New name.png',**kw):return server.act(self.c,dict(id=-1,expected_path=str(self.src),action=action,name=name,**kw))
 def test_rename(self):
  self.call();dst=self.root/'New name.png';self.assertEqual(server.o.sha(dst),self.r['sha256']);self.assertFalse(self.src.exists());self.assertEqual(json.loads(self.c.execute('SELECT data FROM files').fetchone()[0])['destination'],str(dst))
 def test_collision(self):
  (self.root/'New name.png').write_bytes(b'existing')
  with self.assertRaises(ValueError):self.call()
  self.assertTrue(self.src.exists())
 def test_invalid(self):
  for name in ['../escape.png','wrong.pdf','.hidden.png','a/b.png']:
   with self.assertRaises(ValueError):self.call(name=name)
 def test_stale(self):
  with self.assertRaises(ValueError):server.act(self.c,dict(id=-1,expected_path='old',action='trash'))
 def test_changed(self):
  self.src.write_bytes(b'changed')
  with self.assertRaises(ValueError):self.call()
 def test_nonreview(self):
  self.r['needs_review']=False;server.o.put(self.c,self.r,'done')
  with self.assertRaises(ValueError):self.call()
 def test_metadata(self):
  result=server.act(self.c,dict(id=-1,expected_path=str(self.src),expected_sha256=self.r['sha256'],action='metadata',summary='A useful test description.',keywords=['test','example'],entities=[],visible_content=['file'],purpose='reference'))
  self.assertTrue(result['ok']);saved=json.loads((server.o.P/'metadata'/'user-edits.json').read_text())['-1'];self.assertEqual(saved['summary'],'A useful test description.');self.assertTrue(self.src.exists());self.assertEqual(server.o.sha(self.src),self.r['sha256'])
 def test_metadata_rejects_stale_fingerprint(self):
  with self.assertRaises(ValueError):server.act(self.c,dict(id=-1,expected_path=str(self.src),expected_sha256='wrong',action='metadata',summary='x',keywords=[],entities=[],visible_content=[],purpose='reference'))
 def test_trash(self):
  dst=self.root/'Trash'/'example.png';dst.parent.mkdir()
  def fake_run(*args,**kwargs):server.o.exclusive_rename(self.src,dst);return subprocess.CompletedProcess(args[0],0,str(dst),'')
  with patch.object(server.subprocess,'run',side_effect=fake_run):self.call(action='trash')
  status,raw=self.c.execute('SELECT status,data FROM files').fetchone();self.assertEqual(status,'trashed');r=json.loads(raw);self.assertEqual(Path(r['trash_path']),dst);self.assertFalse(self.src.exists());self.assertEqual(server.o.sha(dst),self.r['sha256'])
if __name__=='__main__':unittest.main()
