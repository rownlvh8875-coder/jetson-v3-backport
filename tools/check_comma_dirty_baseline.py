"""Read-only exact attestation of a privately pinned actual366 runtime overlay.

collect-private reads a JSON configuration from stdin and emits PRIVATE paths to
stdout. Run from reviewed source in memory under Python -B, never install it on
comma. verify emits anonymous results only and requires an independently trusted
expected-manifest digest plus a fresh collection challenge. Neither mode writes,
cleans, imports vehicle packages, changes Git state, or authorizes installation.
Hashes check an approved observation/policy; they do not authenticate its author.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys

BASE_SHA = '366d6eae9aa9962104391e1d997fe956dea8f64d'
PATCH_SHA = '3a3e19430ab667d204f22fd1e40438a85e1ade1dbab2e6f9dd6e3dd32de4c1ee'
MODEL = 'openpilot/selfdrive/modeld/jetlink/model.py'
PACKAGE = 'openpilot/selfdrive/modeld/jetlink/input_recording'
SOURCE_PINS = {
    MODEL: 'c627644ff2f986883325aaca1b8410f216f45447c6595a123d8c1e53ef8c83da',
    'openpilot/selfdrive/modeld/jetlink/link.py': '9bdb6fb3b9c669fefd0e065e144ceea76068f839cd53eb9d5ccaf3c34c3908c4',
    'openpilot/selfdrive/modeld/camera_gap.py': '7b959fa8bdd740c4bea150c07248a69ea33f08db327110601be3ee17d9bc938a',
    'openpilot/selfdrive/modeld/camera_sync.py': '398980260825757393239796cb4dc10399ef1384f0fd9e23cdad0fd12d0cc0d2',
    'third_party/jetlink/jetlink/spec.py': 'ec844ccaf13ffc1d7c03ad683b0e3f2ce6a1d78f4088067739aaa419af422170',
}
AFTER = {MODEL:'4813e215b13b447a234ca78839d4cac605f69a9ec2b1a6263ed9ffa063204f0d',
    PACKAGE+'/__init__.py':'e70246cd5900e93d9c6176443895b9fd5e0487b1d416b861b63b34ff482292ca',
    PACKAGE+'/format.py':'9deff26ba3ba9b66642f7a471b10c637272003029866ce47fe82f80ff702acdf',
    PACKAGE+'/dataset.py':'25af73e6de65116cbb8050c7da2c89e1c2d1f7e275cfeaf54bd939ed9529e0f7',
    PACKAGE+'/hook.py':'e8196e46df04a0ca99dd1ba4d009d5a683bd8e8a7a91b05a8b81bec3731f5bd1',
    PACKAGE+'/recorder.py':'d6004d0934a87fd23adb82e8873b44ec710935c1e7bd5ec8f1806a46513aeada'}
CLASSES = {'SAFE_GENERATED','SAFE_BACKUP_NOT_REFERENCED','CUSTOM_SOURCE_REFERENCED',
           'CUSTOM_SOURCE_NOT_REFERENCED','RUNTIME_REQUIRED','UNKNOWN_USER_OWNED'}
_GENERATED = {1,3,4,6,7,8,11,12,13,14,15,16,23,24,25,26,31,44,47}
BASELINE_CLASSES = {f'U{i:02d}': 'SAFE_GENERATED' if i in _GENERATED else
                    'SAFE_BACKUP_NOT_REFERENCED' if i==2 else
                    'UNKNOWN_USER_OWNED' if i in (32,46) else 'RUNTIME_REQUIRED'
                    for i in range(1,49)}
RESOLUTION_ENV_KEYS = ('PYTHONPATH','PYTHONHOME','VIRTUAL_ENV','PATH','LD_LIBRARY_PATH',
                       'PYTHONSAFEPATH','PYTHONNOUSERSITE')


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def inventory_digest(entries):
    return digest([(e['path'],e['tree_digest']) for e in entries])


def load_json(raw):
    def pairs(items):
        out={}
        for key,value in items:
            if key in out:raise ValueError('duplicate')
            out[key]=value
        return out
    try:
        if len(raw)>16*1024*1024:return None
        value=json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda _: (_ for _ in ()).throw(ValueError('constant')))
        return value if isinstance(value,dict) else None
    except (ValueError,UnicodeError,TypeError):return None


def _relative(name):
    if not isinstance(name,str) or not name or '\\' in name or '\0' in name:raise ValueError('path')
    p=PurePosixPath(name)
    if p.is_absolute() or '..' in p.parts or str(p)!=name or name.startswith('.git/'):raise ValueError('path')
    return name


def _hex(value,length=64):
    return isinstance(value,str) and re.fullmatch('[0-9a-f]{'+str(length)+'}',value) is not None


def _inventory(snapshot):
    entries=snapshot['entries'];paths=[];ids=[];files=total=0;all_paths=set()
    for e in entries:
        path=_relative(e['path']);paths.append(path);ids.append(e['id'])
        nodes=e['nodes'];names=[];count=size=0
        for n in nodes:
            name=_relative(n['path']);names.append(name)
            if name!=path and not name.startswith(path+'/'):raise ValueError('entry scope')
            if name in all_paths:raise ValueError('duplicate node')
            all_paths.add(name)
            if n['kind'] not in ('file','dir'):raise ValueError('unsupported node')
            for k in ('mode','uid','gid','bytes','mtime_ns','ctime_ns'):
                if type(n[k]) is not int or n[k]<0:raise ValueError('metadata')
            if n['mode']>0o7777:raise ValueError('mode')
            keys={'path','kind','mode','uid','gid','bytes','mtime_ns','ctime_ns'}
            if n['kind']=='file':
                keys|={'sha256','git_blob_oid'}
                if not _hex(n['sha256']) or not _hex(n['git_blob_oid'],40):raise ValueError('hash')
                count+=1;size+=n['bytes']
            if set(n)!=keys:raise ValueError('node fields')
        if names!=sorted(names) or not nodes or e['root']!=next(n for n in nodes if n['path']==path):raise ValueError('root')
        if e['tree_digest']!=digest(nodes) or e['regular_files']!=count or e['bytes']!=size:raise ValueError('tree')
        files+=count;total+=size
    if paths!=sorted(set(paths)) or len(ids)!=len(set(ids)):raise ValueError('namespace')
    if ids!=[f'U{i+1:02d}' for i in range(len(entries))]:raise ValueError('entry ids')
    if snapshot['inventory_digest']!=inventory_digest(entries):raise ValueError('inventory commitment')
    if snapshot['recursive_regular_files']!=files or snapshot['recursive_bytes']!=total:raise ValueError('totals')
    return entries


def _identities(snapshot):
    rows=snapshot['proc']['processes']
    values=sorted((p['pid'],p['start_ticks'],p['exe'],p['cwd'],
                   digest({k:v for k,v in p.get('resolution_env',{}).items() if k in RESOLUTION_ENV_KEYS})) for p in rows)
    if not rows or len({p['pid'] for p in rows})!=len(rows) or any(p.get('errors') for p in rows):raise ValueError('process coverage')
    return values


def verify(expected,observed,*,patch,challenge):
    """Pure comparison. An unresolved policy yields PARTIAL, never install-ready.

    Paths/argv/environment/error strings never leave this public return value.
    Unknown acceptance must be explicit, reviewed, evidence-bound isolation; no
    boolean whitelist. Runtime consumers stay part of the exact snapshot.
    """
    hard=[];pending=[];checks={};counts={};unknown=0;observed_digest=None
    try:
        if expected['schema']!=1 or not _hex(challenge,32):raise ValueError('schema/challenge')
        base=expected['snapshot'];old=_inventory(base);new=_inventory(observed)
        observed_digest=observed['inventory_digest']
        def require(name,condition):
            checks[name]=bool(condition)
            if not condition:hard.append(name)
        require('ACTUAL366_BRANCH_HEAD',base['branch']==observed['branch']=='carrot-nav' and base['head']==observed['head']==BASE_SHA)
        require('OFFROAD',base['flags']==observed['flags']=={'IsOffroad':'1','IsOnroad':'0'})
        require('PARAMS_BINDING',_hex(base.get('params_binding_digest')) and base['params_binding_digest']==observed.get('params_binding_digest'))
        require('TRACKED_UNMODIFIED',base['tracked_status']==observed['tracked_status']==[])
        require('TRACKED_INDEX_FLAGS_SAFE',base.get('tracked_index_flags_all_H') is True and observed.get('tracked_index_flags_all_H') is True)
        require('FRESH_CHALLENGE',observed.get('nonce')==challenge)
        require('SAME_BOOT',isinstance(base.get('boot_id'),str) and re.fullmatch('[0-9a-f-]{36}',base['boot_id']) is not None and base['boot_id']==observed.get('boot_id'))
        require('EXPECTED48',len(old)==len(new)==48)
        require('EXACT_PRIVATE_INVENTORY',old==new and base['inventory_digest']==observed_digest)
        for field in ('source_hashes','model_hashes','routes_inventory'):
            require(field.upper(),bool(base[field]) and base[field]==observed[field])
        require('M18_SOURCE_PINS',all(base['source_hashes'].get(p)==h==observed['source_hashes'].get(p) for p,h in SOURCE_PINS.items()))
        require('PROCESS_IDENTITIES',_identities(base)==_identities(observed))
        classes=expected['classifications']
        require('CLASSIFICATIONS',classes==BASELINE_CLASSES and set(classes)=={e['id'] for e in old})
        counts={c:sum(v==c for v in classes.values()) for c in sorted(CLASSES)}
        old_by_id={e['id']:e for e in old};new_by_id={e['id']:e for e in new}
        require('RUNTIME_REQUIRED_HASHES',all(old_by_id[i]==new_by_id.get(i) for i,c in BASELINE_CLASSES.items() if c=='RUNTIME_REQUIRED'))
        proof=expected['patch'];files=proof['files'];targets={f['path'] for f in files}
        parsed=set(re.findall(r'^\+\+\+ b/(.*?)$',patch.decode('utf-8'),re.M))
        require('EXACT_M18_PATCH',hashlib.sha256(patch).hexdigest()==proof['sha256']==PATCH_SHA and parsed==targets==set(AFTER) and len(files)==6)
        require('PATCH_FILE_IDENTITIES',all(f['after_sha256']==AFTER.get(f['path']) and f['before_sha256']==(SOURCE_PINS[MODEL] if f['path']==MODEL else None) for f in files))
        collision=False
        for e in new:
            for n in e['nodes']:
                p=n['path']
                if any(p==t or (n['kind']=='dir' and t.startswith(p+'/')) or p.removesuffix('.bak')==t for t in targets):collision=True
        require('RECORDER_PATH_COLLISION_ABSENT',not collision)
        require('RECORDER_PHYSICAL_NAMESPACE_ABSENT',all(base.get('recorder_namespace',{}).get(k) is True and
                observed.get('recorder_namespace',{}).get(k) is True for k in
                ('new_package_absent','new_targets_absent','parent_dirs_safe')))
        isolation=expected['isolation']
        isolated=(isolation.get('status')=='PASS' and isolation.get('baseline_digest')==base['inventory_digest']
                  and isolation.get('patch_sha256')==PATCH_SHA and _hex(isolation.get('evidence_sha256'))
                  and isolation.get('package_shadow') is False
                  and isolation.get('dynamic_import_risk')=='ASSESSED_NO_PATCH_OVERLAP')
        checks['REVIEWED_IMPORT_ISOLATION']=bool(isolated)
        if not isolated:pending.append('IMPORT_ISOLATION_UNRESOLVED')
        for ident,resolved in [('U32',{'SAFE_UNUSED_OBSERVER','RUNTIME_REFERENCED'}),('U46',{'SAFE_GENERATED_LEGACY','BUILD_REQUIRED'})]:
            entry=next(e for e in old if e['id']==ident);p=expected['provenance'].get(ident,{})
            bound=(p.get('sha256')==entry['root'].get('sha256'))
            accepted=(p.get('decision')=='UNKNOWN_ACCEPTABLE_FOR_PATCH_ISOLATION'
                      and p.get('baseline_digest')==base['inventory_digest'] and p.get('patch_sha256')==PATCH_SHA
                      and _hex(p.get('evidence_sha256')) and isolated
                      and all(p.get(k) is True for k in ('path_disjoint','import_shadow_absent','runtime_reference_absent','target_overlap_absent'))
                      and p.get('dynamic_import_risk')=='ASSESSED_NO_PATCH_OVERLAP')
            ok=bound and (p.get('status') in resolved or accepted)
            checks[ident+'_POLICY']=bool(ok)
            if not ok:unknown+=1;pending.append(ident+'_PROVENANCE_UNRESOLVED')
    except (KeyError,TypeError,ValueError,AttributeError,IndexError,StopIteration,UnicodeError):hard.append('INVALID_PRIVATE_EVIDENCE')
    status='FAIL' if hard else 'PARTIAL' if pending else 'PASS'
    return {'schema':1,'status':'ATTESTED_DIRTY_BASELINE_'+status,'ready_to_retry_M19':status=='PASS',
            'checks':checks,'reasons':sorted(set(hard+pending)),'classification_counts':counts,
            'unknown_policy_remaining':unknown,'observed_inventory_digest':observed_digest,
            'evidence_kind':'READ_ONLY_COMPARISON_OF_TRUSTED_PRIVATE_OBSERVATIONS',
            'installation_authorized':False,'actual_mutations':False}


def _absolute(value):
    p=Path(value)
    if not p.is_absolute() or '..' in p.parts or any(q.is_symlink() for q in (p,*p.parents)):raise ValueError('absolute non-symlink path')
    return p


def _safe(root,name):
    p=root/_relative(name)
    if any(q.is_symlink() for q in (p,*p.parents)):raise ValueError('symlink')
    return p


def read_flags(config):
    """Read only the two gates; a known Params alias must bind a physical root.

    Source/untracked symlink refusal is unchanged. This explicit exception does
    not follow an arbitrary alias supplied as params_root or change any Params.
    """
    target=_absolute(config['params_root']);alias=config.get('params_alias')
    def bound():
        if alias is None:return
        p=Path(alias)
        if not p.is_absolute() or '..' in p.parts or not p.is_symlink() or any(q.is_symlink() for q in p.parents):raise ValueError('Params alias')
        if p.resolve(strict=True)!=target:raise ValueError('Params alias drift')
    bound()
    flags={}
    for name in ('IsOffroad','IsOnroad'):
        p=target/name;s=p.lstat()
        if not stat.S_ISREG(s.st_mode) or s.st_size not in (1,2):raise ValueError('Params scalar type/size')
        fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        try:
            if _sig(s)!=_sig(os.fstat(fd)):raise ValueError('Params scalar race')
            data=os.read(fd,3)
            if data not in (b'0',b'1',b'0\n',b'1\n') or len(data)!=s.st_size:raise ValueError('Params scalar value')
            if _sig(s)!=_sig(os.fstat(fd)) or _sig(s)!=_sig(p.lstat()):raise ValueError('Params scalar race')
            flags[name]=data.decode().strip()
        finally:os.close(fd)
    bound()
    return flags,digest({'physical_root':str(target),'known_alias':alias})


def _sig(s):
    return s.st_dev,s.st_ino,s.st_mode,s.st_uid,s.st_gid,s.st_size,s.st_mtime_ns,s.st_ctime_ns


def recorder_namespace(root):
    """Probe even ignored/empty paths, which a normal Git status cannot reveal."""
    root=_absolute(root);parent=root/PurePosixPath(PACKAGE).parent;safe=True
    while parent!=root:
        if parent.is_symlink() or not parent.is_dir():safe=False
        parent=parent.parent
    return {'new_package_absent':not os.path.lexists(root/PACKAGE),
            'new_targets_absent':all(not os.path.lexists(root/name) for name in AFTER if name!=MODEL),
            'parent_dirs_safe':safe}


def _node(root,p):
    s=p.lstat();n=dict(path=p.relative_to(root).as_posix(),mode=stat.S_IMODE(s.st_mode),uid=s.st_uid,gid=s.st_gid,
                      mtime_ns=s.st_mtime_ns,ctime_ns=s.st_ctime_ns,bytes=s.st_size)
    if stat.S_ISDIR(s.st_mode):n['kind']='dir'
    elif stat.S_ISREG(s.st_mode):
        _safe(root,n['path']);fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        try:
            if _sig(os.fstat(fd))!=_sig(s):raise ValueError('file race')
            h=hashlib.sha256();g=hashlib.sha1(b'blob '+str(s.st_size).encode()+b'\0')
            while True:
                data=os.read(fd,1<<20)
                if not data:break
                h.update(data);g.update(data)
            if _sig(os.fstat(fd))!=_sig(s) or _sig(p.lstat())!=_sig(s):raise ValueError('file race')
            n.update(kind='file',sha256=h.hexdigest(),git_blob_oid=g.hexdigest())
        finally:os.close(fd)
    else:raise ValueError('symlink/special node unsupported')
    return n


def _git(root,*args):
    base=['git','-c','core.fsmonitor=false','-c','core.untrackedCache=false','-C',str(root)]
    options=dict(stderr=subprocess.DEVNULL,env={**os.environ,'GIT_OPTIONAL_LOCKS':'0','GIT_NO_LAZY_FETCH':'1'},timeout=30)
    if args and args[0]=='status':
        # Even status can run clean/process filters for stat-dirty tracked files.
        # Config and index enumeration do not convert working-tree content. Reject
        # helpers rather than execute them, disable attributes or hide dirty files.
        filters=subprocess.run([*base,'config','--name-only','--null','--get-regexp',r'^filter\..*\.(clean|process)$'],
                               stdout=subprocess.PIPE,**options)
        if filters.returncode not in (0,1):raise subprocess.CalledProcessError(filters.returncode,'git config')
        staged=subprocess.check_output([*base,'ls-files','--stage','-z'],**options)
        # Delegated submodule status can use its own unsafe config. actual366 has
        # no gitlinks. Refuse them until separate recursive read-only handling exists.
        if any(row.startswith(b'160000 ') for row in staged.split(b'\0')):raise ValueError('Git submodule status unsupported')
        if filters.returncode==0:
            drivers={key[7:].rsplit(b'.',1)[0] for key in filters.stdout.split(b'\0') if key}
            names=[row.split(b'\t',1)[1] for row in staged.split(b'\0') if row]
            if names:
                attrs=subprocess.check_output([*base,'check-attr','-z','--stdin','filter'],
                    input=b'\0'.join(names)+b'\0',**options).split(b'\0')
                if attrs[-1]!=b'' or len(attrs)!=3*len(names)+1:raise ValueError('filter attribute coverage')
                if any(attrs[i]!=name or attrs[i+1]!=b'filter' for i,name in zip(range(0,len(attrs)-1,3),names)):
                    raise ValueError('filter attribute coverage')
                if any(value in drivers for value in attrs[2:-1:3]):raise ValueError('external Git status filter unsupported')
    return subprocess.check_output([*base,*args],**options).decode()


def _processes(root):
    own={os.getpid()};pid=os.getppid()
    while pid>1 and pid not in own:
        own.add(pid)
        try:pid=int(Path(f'/proc/{pid}/stat').read_text().split(') ',1)[1].split()[1])
        except OSError:break
    rows=[];inaccessible=0
    inside=lambda p:p==str(root) or p.startswith(str(root)+'/')
    for p in Path('/proc').iterdir():
        if not p.name.isdecimal() or int(p.name) in own:continue
        try:argv=(p/'cmdline').read_bytes().decode(errors='replace').rstrip('\0').split('\0')
        except OSError:continue
        if not argv or not argv[0]:continue
        row={'pid':int(p.name)};paths=[];errors=[]
        for key in ('cwd','exe'):
            try:row[key]=os.readlink(p/key);paths.append(row[key])
            except OSError:errors.append(key)
        try:row['start_ticks']=(p/'stat').read_text().split(') ',1)[1].split()[19]
        except OSError:errors.append('stat')
        try:
            for line in (p/'maps').read_text().splitlines():
                parts=line.split(None,5)
                if len(parts)==6 and parts[5].startswith('/'):paths.append(parts[5].removesuffix(' (deleted)'))
        except OSError:errors.append('maps')
        try:
            for fd in (p/'fd').iterdir():
                try:paths.append(os.readlink(fd).removesuffix(' (deleted)'))
                except OSError:pass
        except OSError:errors.append('fd')
        relevant=any(inside(x) for x in paths) or any('openpilot.' in x or 'manager.py' in x for x in argv)
        if relevant:
            try:
                env=dict(x.split('=',1) for x in (p/'environ').read_bytes().decode(errors='replace').split('\0') if '=' in x)
                row['resolution_env']={k:env[k] for k in RESOLUTION_ENV_KEYS if k in env}
            except OSError:errors.append('environ')
            row['errors']=errors;rows.append(row)
        elif errors:inaccessible+=1
    return {'processes':rows,'other_inaccessible_process_count':inaccessible,'excluded_own_lineage':sorted(own)}


def collect(config):
    """Collect PRIVATE evidence without imports, writes, fetches or index refresh.

    Linux only. Caller's fresh nonce is echoed; caller must trust this collection
    channel and source. This is an observation window, not an atomic device image.
    Atime is deliberately excluded because ordinary reads may update it.
    """
    root=_absolute(config['root']);flags,params_binding=read_flags(config)
    if flags!={'IsOffroad':'1','IsOnroad':'0'}:raise ValueError('offroad')
    if not _hex(config['nonce'],32):raise ValueError('nonce')
    head=_git(root,'rev-parse','HEAD').strip();branch=_git(root,'branch','--show-current').strip()
    status=_git(root,'status','--porcelain=v1','-z').split('\0')
    index_flags=_git(root,'ls-files','-v','-z');namespace=recorder_namespace(root)
    names=[v[3:].rstrip('/') for v in status if v.startswith('?? ')]
    entries=[]
    for i,name in enumerate(names):
        p=_safe(root,name);nodes=[_node(root,p)]
        if nodes[0]['kind']=='dir':
            for base,dirs,files in os.walk(p,followlinks=False):
                for n in sorted(dirs+files):nodes.append(_node(root,Path(base)/n))
        nodes.sort(key=lambda n:n['path']);regular=[n for n in nodes if n['kind']=='file']
        entries.append(dict(id=f'U{i+1:02d}',path=name,root=next(n for n in nodes if n['path']==name),nodes=nodes,
                            regular_files=len(regular),bytes=sum(n['bytes'] for n in regular),tree_digest=digest(nodes)))
    source={name:_node(root,_safe(root,name))['sha256'] for name in config['source_paths']}
    model_root=_absolute(config['model_root']);models={}
    for p in sorted(model_root.iterdir()):
        if p.is_file():models[p.name]=_node(model_root,p)['sha256']
    route_root=_absolute(config['route_root']);routes=[]
    for base,dirs,files in os.walk(route_root,followlinks=False):
        dirs[:]=sorted(d for d in dirs if not (Path(base)/d).is_symlink())
        for n in sorted(files):
            p=Path(base)/n;s=p.lstat();routes.append([p.relative_to(route_root).as_posix(),s.st_mode,s.st_size,s.st_mtime_ns])
    routes.sort();processes=_processes(root)
    if status!=_git(root,'status','--porcelain=v1','-z').split('\0') or head!=_git(root,'rev-parse','HEAD').strip():raise ValueError('source race')
    if index_flags!=_git(root,'ls-files','-v','-z') or namespace!=recorder_namespace(root):raise ValueError('index/namespace race')
    if (flags,params_binding)!=read_flags(config):raise ValueError('offroad/Params binding race')
    # A second namespace/stat pass also catches changes inside a collapsed ?? dir.
    for e in entries:
        current=[];p=_safe(root,e['path']);current.append(p)
        if p.is_dir():
            for base,dirs,files in os.walk(p,followlinks=False):current.extend(Path(base)/n for n in sorted(dirs+files))
        if sorted(x.relative_to(root).as_posix() for x in current)!=[n['path'] for n in e['nodes']]:raise ValueError('namespace race')
        for n in e['nodes']:
            s=_safe(root,n['path']).lstat()
            if (stat.S_IMODE(s.st_mode),s.st_uid,s.st_gid,s.st_size,s.st_mtime_ns,s.st_ctime_ns)!=(n['mode'],n['uid'],n['gid'],n['bytes'],n['mtime_ns'],n['ctime_ns']):raise ValueError('metadata race')
    return dict(branch=branch,head=head,flags=flags,tracked_status=[v for v in status if v and not v.startswith('?? ')],
                entries=entries,recursive_regular_files=sum(e['regular_files'] for e in entries),
                recursive_bytes=sum(e['bytes'] for e in entries),inventory_digest=inventory_digest(entries),
                source_hashes=source,model_hashes=models,routes_inventory={'files':len(routes),'sha256':digest(routes)},
                proc=processes,nonce=config['nonce'],boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                params_binding_digest=params_binding,recorder_namespace=namespace,
                tracked_index_flags_all_H=bool(index_flags) and all(v.startswith('H ') for v in index_flags.split('\0') if v))


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='mode',required=True)
    sub.add_parser('collect-private',help='PRIVATE stdout; reviewed config on stdin, no output files')
    check=sub.add_parser('verify');check.add_argument('expected');check.add_argument('observed')
    check.add_argument('--patch',required=True);check.add_argument('--expected-sha256',required=True);check.add_argument('--challenge',required=True)
    args=parser.parse_args(argv)
    try:
        if args.mode=='collect-private':
            config=load_json(sys.stdin.buffer.read(16*1024*1024+1))
            if config is None:raise ValueError('config')
            print(json.dumps(collect(config)));return 0
        raw=Path(args.expected).read_bytes()
        if not _hex(args.expected_sha256) or hashlib.sha256(raw).hexdigest()!=args.expected_sha256:raise ValueError('manifest identity')
        expected=load_json(raw);observed=load_json(Path(args.observed).read_bytes())
        if expected is None or observed is None:raise ValueError('json')
        result=verify(expected,observed,patch=Path(args.patch).read_bytes(),challenge=args.challenge)
        print(json.dumps(result));return 0 if result['ready_to_retry_M19'] else 1
    except (OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError):
        print(json.dumps({'status':'ATTESTED_DIRTY_BASELINE_FAIL','reasons':['INVALID_INPUT_OR_COLLECTION'],'ready_to_retry_M19':False}));return 1


if __name__=='__main__':
    raise SystemExit(main())
