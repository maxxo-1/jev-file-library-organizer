"""Loopback-only, token-authenticated review actions for the local dashboard."""
import sys,json,os,secrets,subprocess,fcntl,time,hmac
from pathlib import Path
from http.server import HTTPServer,BaseHTTPRequestHandler
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P.parent))
import organizer as o
TOKEN_PATH=o.P/'dashboard-token'
if not TOKEN_PATH.exists():
 TOKEN_PATH.write_text(secrets.token_urlsafe(32));TOKEN_PATH.chmod(0o600)
TOKEN=TOKEN_PATH.read_text().strip()
PORT=int(o.CONFIG.get('dashboard_port',48763))
ACTIONS=o.P/'dashboard-actions';ACTIONS.mkdir(exist_ok=True)

def act(c,payload):
 if payload.get('action') not in ('rename','trash','metadata'):raise ValueError('Unknown action.')
 for pending in ACTIONS.glob('*.json'):
  prior=json.loads(pending.read_text())
  if prior.get('state')=='prepared':raise ValueError('A previous file action needs recovery. Ask Codex to reconcile the saved action before continuing.')
 row=c.execute('SELECT status,data FROM files WHERE id=?',(payload.get('id'),)).fetchone()
 if not row or row[0]!='done':raise ValueError('This file is no longer available. Refresh the dashboard.')
 r=json.loads(row[1]);src=Path(r['destination'])
 if payload['action']=='metadata':
  if payload.get('expected_path')!=str(src) or payload.get('expected_sha256')!=r['sha256']:raise ValueError('This file changed. Refresh the dashboard before editing its metadata.')
  if not src.is_file() or src.is_symlink() or not any(root in src.parents for root in o.ROOTS):raise ValueError('File is unavailable or outside the library.')
  def text_value(name,limit):
   value=payload.get(name,'')
   if not isinstance(value,str) or len(value)>limit or any(ord(ch)<32 and ch not in '\t\n' for ch in value):raise ValueError('Invalid '+name.replace('_',' ')+'.')
   return ' '.join(value.split())
  def list_value(name):
   value=payload.get(name,[])
   if not isinstance(value,list) or len(value)>20:raise ValueError('Invalid '+name.replace('_',' ')+'.')
   result=[]
   for item in value:
    if not isinstance(item,str) or len(item)>80 or any(ord(ch)<32 for ch in item):raise ValueError('Invalid '+name.replace('_',' ')+'.')
    item=' '.join(item.split())
    if item and item.casefold() not in {x.casefold() for x in result}:result.append(item)
   return result
  allowed_purposes={'research','newsletter illustration','agreement','receipt or transaction','presentation','screenshot','personal photo','reference','unknown'}
  purpose=payload.get('purpose','unknown')
  if purpose not in allowed_purposes:raise ValueError('Invalid purpose.')
  metadata_dir=o.P/'metadata';metadata_dir.mkdir(exist_ok=True);edits_path=metadata_dir/'user-edits.json'
  edits=json.loads(edits_path.read_text()) if edits_path.exists() else {}
  edits[str(r['id'])]={'summary':text_value('summary',280),'keywords':list_value('keywords'),'entities':list_value('entities'),'visible_content':list_value('visible_content'),'purpose':purpose,'edited_at':time.time()}
  o.atomic(edits_path,edits)
  return {'ok':True,'message':'Descriptive metadata saved.'}
 if not r.get('needs_review'):raise ValueError('Only items marked for review can be changed here.')
 if payload.get('expected_path')!=str(src):raise ValueError('This file has changed location. Refresh the dashboard.')
 if src.is_symlink() or not src.is_file() or src.resolve()!=src or not any(root in src.parents for root in o.ROOTS):raise ValueError('File is unavailable or outside the library.')
 if o.sha(src)!=r['sha256']:raise ValueError('File contents changed. Review the file again before changing it.')
 action=payload['action'];dst=None
 if action=='rename':
  name=payload.get('name','').strip()
  if not name or name in ('.','..') or name.startswith('.') or any(ch in name for ch in '/\\:') or any(ord(ch)<32 for ch in name) or len(os.fsencode(name))>240:raise ValueError('Enter a filename without slashes, colons, or control characters (maximum 240 bytes).')
  if Path(name).suffix.lower()!=src.suffix.lower():raise ValueError('Keep the original file extension: '+src.suffix)
  dst=src.with_name(name)
  if dst==src:return {'ok':True,'message':'The filename is unchanged.'}
  if dst.exists():raise ValueError('A file with that name already exists. Choose another name.')
 journal=ACTIONS
 log=journal/(str(time.time_ns())+'.json')
 entry={'id':r['id'],'action':action,'before':str(src),'after':str(dst) if dst else None,'sha256':r['sha256'],'state':'prepared','time':time.time()}
 o.atomic(log,entry)
 if action=='rename':
  o.exclusive_rename(src,dst)
  r.update(destination=str(dst),title=dst.stem,renamed=dst.name!=Path(r['path']).name,status='renamed by user')
  o.put(c,r,'done')
 else:
  trash_helper=Path(o.CONFIG.get('trash_helper',o.BASE/'bin'/'trash'));completed=subprocess.run([str(trash_helper),str(src)],capture_output=True,text=True)
  if completed.returncode:raise ValueError('Could not move the file to Trash: '+completed.stderr.strip())
  entry['after']=completed.stdout.strip();r.update(trashed_from=str(src),trash_path=entry['after'],status='moved to Trash by user')
  o.put(c,r,'trashed')
 entry['state']='complete';o.atomic(log,entry)
 return {'ok':True,'message':'Filename saved.' if action=='rename' else 'Moved to Trash. You can restore it in Finder.'}

def rebuild(c):
 o.export(c)
 subprocess.run([sys.executable,str(o.BASE/'build_dashboard.py')],check=True,capture_output=True,text=True)

class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def response_headers(self,status):
  self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Cache-Control','no-store')
  if self.headers.get('Origin')=='null':self.send_header('Access-Control-Allow-Origin','null')
  self.end_headers()
 def reply(self,status,obj):self.response_headers(status);self.wfile.write(json.dumps(obj).encode())
 def valid_host(self):return self.headers.get('Host')==f'127.0.0.1:{PORT}'
 def do_OPTIONS(self):
  if not self.valid_host() or self.headers.get('Origin')!='null':return self.reply(403,{'error':'Not allowed'})
  self.send_response(204);self.send_header('Access-Control-Allow-Origin','null');self.send_header('Access-Control-Allow-Methods','POST, OPTIONS');self.send_header('Access-Control-Allow-Headers','Content-Type, X-Library-Token');self.send_header('Access-Control-Allow-Private-Network','true');self.end_headers()
 def do_POST(self):
  if not self.valid_host() or self.headers.get('Origin') not in (None,'null') or not hmac.compare_digest(self.headers.get('X-Library-Token',''),TOKEN):return self.reply(403,{'error':'Not allowed'})
  if self.path not in ('/health','/action'):return self.reply(404,{'error':'Unknown endpoint'})
  if self.path=='/health':return self.reply(200,{'ok':True})
  try:
   length=int(self.headers.get('Content-Length','0'))
   if length<1 or length>16384:raise ValueError('Invalid request.')
   payload=json.loads(self.rfile.read(length))
   with (o.P/'run.lock').open('a') as lock:
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:raise ValueError('Organization is running. Try again in a moment.')
    c=o.db()
    try:
     result=act(c,payload)
     try:rebuild(c)
     except Exception:result['message']+=' The dashboard refresh needs attention; the file action was saved.';result['refresh_failed']=True
    finally:c.close()
   self.reply(200,result)
  except (ValueError,OSError) as e:self.reply(400,{'error':str(e)})
  except Exception:self.reply(500,{'error':'The action could not finish. Check the file location before retrying.'})
if __name__=='__main__':HTTPServer(('127.0.0.1',PORT),Handler).serve_forever()
