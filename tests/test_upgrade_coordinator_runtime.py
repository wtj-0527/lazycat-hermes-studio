"""Execute the actual manifest shell against a process-safe fake Docker daemon."""
import os
from pathlib import Path
import subprocess
import sys
import yaml

MANIFEST = Path(__file__).resolve().parents[1] / 'lzc-manifest.yml'
FAKE = r'''import fcntl,json,os,sys,time
p=os.environ['FAKE_STATE']; a=sys.argv[1:]
with open(p,'a+') as f:
 fcntl.flock(f,fcntl.LOCK_EX); f.seek(0); s=json.loads(f.read() or '{}')
 def save():
  f.seek(0);f.truncate();json.dump(s,f);f.flush()
 def fail(): sys.exit(1)
 mode=os.environ.get('FAIL','')
 if a[0]=='info':
  if mode=='info': fail()
 elif a[:2]==['image','inspect']:
  if mode in ('pull','missing'): fail()
 elif a[0]=='pull':
  if mode=='pull': fail()
 elif a[0]=='run':
  name=a[a.index('--name')+1]
  if name in s or mode=='run': fail()
  labels={}
  for i,x in enumerate(a):
   if x=='--label':
    k,v=a[i+1].split('=',1);labels[k]=v
  s[name]={'Id':name,'Name':'/'+name,'Created':str(time.time_ns()),'Config':{'Labels':labels}}
  save();print(name)
 elif a[0]=='inspect':
  if a[1] not in s: fail()
  print(json.dumps([s[a[1]]],indent=4))
 elif a[0]=='ps':
  filters=[a[i+1][6:].split('=',1) for i,x in enumerate(a) if x=='--filter' and a[i+1].startswith('label=')]
  for k,v in s.items():
   if all(v['Config']['Labels'].get(x)==y for x,y in filters):print(k)
 elif a[0]=='rm':
  s.pop(a[-1],None);save()
 elif a[0]=='rename':
  if a[1] not in s:fail()
  v=s.pop(a[1]);v['Name']='/'+a[2];s[a[1]]=v;save()
 else: fail()
'''

def setup(tmp_path):
    docker=tmp_path/'docker'
    docker.write_text(f'#!{sys.executable}\n'+FAKE);docker.chmod(0o755)
    script=yaml.safe_load(MANIFEST.read_text())['services']['hermes-webui']['setup_script']
    script=script.split('      # --- Image fingerprint')[0] if '      # --- Image fingerprint' in script else script.split('# --- Image fingerprint')[0]
    script=script.replace('sleep 5','sleep 0.05').replace('sleep 10','sleep 0.05')
    script=script.replace('PROGRESS_STATE=/tmp/hermes-rootfs-progress','PROGRESS_STATE="$TEST_PROGRESS"')
    script=script.replace('UPGRADE_LOCAL_LOCK_FILE=/lzcapp/cache/rootfs-upgrade.lock','UPGRADE_LOCAL_LOCK_FILE="$TEST_LOCAL_LOCK"')
    shell=tmp_path/'run.sh'
    shell.write_text(script+'''\nCURRENT_ID=test
CURRENT_IMAGE=business-image-not-in-coordinator
acquire_upgrade_slot || exit 42
printf 'enter %s\\n' "$LAZYCAT_APP_DEPLOY_UID" >> "$EVENTS"
sleep 0.15
printf 'exit %s\\n' "$LAZYCAT_APP_DEPLOY_UID" >> "$EVENTS"
release_upgrade_slot
''')
    env=dict(os.environ,PATH=str(tmp_path)+':'+os.environ['PATH'],FAKE_STATE=str(tmp_path/'state'),EVENTS=str(tmp_path/'events'),TEST_PROGRESS=str(tmp_path/'progress'),TEST_LOCAL_LOCK=str(tmp_path/'local.lock'))
    return shell,env

def test_three_instances_do_not_overlap(tmp_path):
    shell,env=setup(tmp_path)
    procs=[subprocess.Popen(['sh',str(shell)],env=dict(env,LAZYCAT_APP_DEPLOY_UID=str(i),TEST_PROGRESS=str(tmp_path/f'p{i}')),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL) for i in range(3)]
    try:
        assert [p.wait(timeout=30) for p in procs]==[0,0,0]
    finally:
        for p in procs:
            if p.poll() is None:p.kill()
    events=(tmp_path/'events').read_text().splitlines()
    assert len(events)==6
    for i in range(0,6,2):
        assert events[i].startswith('enter ')
        assert events[i+1]=='exit '+events[i].split()[1]

def test_unavailable_coordinator_uses_serialized_local_flock(tmp_path):
    shell,env=setup(tmp_path)
    procs=[subprocess.Popen(['sh',str(shell)],env=dict(env,FAIL='info',LAZYCAT_APP_DEPLOY_UID=str(i),TEST_PROGRESS=str(tmp_path/f'fallback-p{i}')),stdout=subprocess.PIPE,stderr=subprocess.PIPE) for i in range(3)]
    results=[]
    for proc in procs:
        out,err=proc.communicate(timeout=15)
        results.append((proc.returncode,out,err))
    assert [item[0] for item in results]==[0,0,0],results
    assert all(b'acquired instance-local upgrade lock' in item[1] for item in results)
    events=(tmp_path/'events').read_text().splitlines()
    assert len(events)==6
    for i in range(0,6,2):
        assert events[i].startswith('enter ')
        assert events[i+1]=='exit '+events[i].split()[1]

def test_broken_available_coordinator_still_fails_closed(tmp_path):
    shell,env=setup(tmp_path)
    for mode in ('pull','run'):
        result=subprocess.run(['sh',str(shell)],env=dict(env,FAIL=mode),capture_output=True,timeout=15)
        assert result.returncode==42,result.stderr

def test_missing_business_image_does_not_disable_lock(tmp_path):
    shell,env=setup(tmp_path)
    result=subprocess.run(['sh',str(shell)],env=dict(env,FAIL='missing'),capture_output=True,timeout=15)
    assert result.returncode==0,result.stderr
    assert 'acquired host-wide upgrade slot' in result.stdout.decode()

def test_no_automatic_revocation_or_success_on_copy_failure():
    text=MANIFEST.read_text()
    assert 'continuing with idle I/O priority' not in text
    assert 'sleep 43200' not in text
    assert 'docker run -d --rm' not in text
    assert 'NOW - LOCK_EPOCH' not in text
    assert 'if ! wait "$COPY_PID"; then' in text
    assert "trap 'release_upgrade_slot'" not in text
    assert 'acquire_local_upgrade_slot' in text
    assert 'flock 9' in text

def test_old_lock_is_not_revoked_even_without_heartbeat(tmp_path):
    import json
    shell,env=setup(tmp_path)
    name='hermes-studio-rootfs-upgrade-lock'
    (tmp_path/'state').write_text(json.dumps({name:{'Id':name,'Name':'/'+name,'Created':'0','Config':{'Labels':{'community.lazycat.app.hermes.upgrade.request':'dead-or-slow-owner'}}}}))
    # Bound the waiter without signaling a real machine or touching a real lock.
    text=shell.read_text().replace('  start_progress_heartbeat\n', '  :\n').replace('WAIT_COUNT=$((WAIT_COUNT+1))','WAIT_COUNT=$((WAIT_COUNT+1)); [ "$WAIT_COUNT" -lt 3 ] || return 1')
    shell.write_text(text)
    result=subprocess.run(['sh',str(shell)],env=env,capture_output=True,timeout=15)
    assert result.returncode==42
    assert not (tmp_path/'events').exists()
    assert name in json.loads((tmp_path/'state').read_text())
