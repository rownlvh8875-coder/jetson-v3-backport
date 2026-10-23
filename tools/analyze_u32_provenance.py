"""Offline PRIVATE static provenance diagnostics; never import/execute the target.

The CPython3.12 pyc reader builds ordinary bounded data, never CodeType objects.
CLI output is private unless --public is selected. No writes, deployment, policy
edits, device access, bytecode compilation or installation authorization occurs.
M193 policy composition is explicit and preserves the frozen M192 policy result.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import struct

U32_SHA='07e2bd4cdac1479f85447c1f96182c8f24603a9184b11045086d7433b68e5b70'
BASELINE='8b0cbfc9df6194fa1607ce8bdc02bc06158b1bd3496a0a4f8de20fdffacfd9d5'
PATCH='3a3e19430ab667d204f22fd1e40438a85e1ade1dbab2e6f9dd6e3dd32de4c1ee'
FROZEN_CHECKER_SHA='3b8f77a388caeb380e78980ba13c02c8e24e8ce4017326f01fbbb7cbf3a90904'
BOUNDARY_PINS={
    'B01':'4d29f423bb359427ec36704e99eedd3512af76a4cac672a74f95ae91b43fed35',
    'B02':'d20ec36947c6aefd12b425daa0f8d1fa39d0d273d1da578b13a20b079aad878a',
    'B03':'c41f66de1daa06643f09bf6b93163279167f00ae753be0019f18dbe546f7708e',
    'B04':'2bb8305cce4070d7fba5caa00ec928bedf13a40da3424d8e16ce23ab632e4ab1',
    'B05':'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
    'B06':'d91817debcdddb7ff4833faacd6c8b84f9cce2b8f2809177d75f307339f37866',
    'B07':'c627644ff2f986883325aaca1b8410f216f45447c6595a123d8c1e53ef8c83da',
    'B08':'59254235f9d5ee6dcfd5ca2ef451d7a851a6d531664e014504e067d029cc8038',
}
LEGACY_CHECKS=('ACTUAL366_BRANCH_HEAD','OFFROAD','PARAMS_BINDING','TRACKED_UNMODIFIED',
    'TRACKED_INDEX_FLAGS_SAFE','FRESH_CHALLENGE','SAME_BOOT','EXPECTED48','EXACT_PRIVATE_INVENTORY',
    'SOURCE_HASHES','MODEL_HASHES','ROUTES_INVENTORY','M18_SOURCE_PINS','PROCESS_IDENTITIES',
    'CLASSIFICATIONS','RUNTIME_REQUIRED_HASHES','EXACT_M18_PATCH','PATCH_FILE_IDENTITIES',
    'RECORDER_PATH_COLLISION_ABSENT','RECORDER_PHYSICAL_NAMESPACE_ABSENT',
    'REVIEWED_IMPORT_ISOLATION','U32_POLICY','U46_POLICY')
REQUIREMENTS=('path_disjoint','namespace_shadow_absent','static_caller_relation_absent',
              'callback_registration_relation_absent','target_mutation_evidence_absent',
              'off_path_interaction_absent','baseline_exact','post_patch_preservation_verifiable',
              'rollback_health_gate_defined')
BLOCKERS=('runtime_caller_found','dynamic_registration_possible','target_mutation_possible',
          'same_namespace_shadow','import_order_interaction','custom_runtime_patch_evidence',
          'current_boot_execution_role_unclear')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def source_profile(raw):
    if not isinstance(raw,bytes) or len(raw)>1_000_000:raise ValueError('source bound')
    tree=ast.parse(raw);imports=[];definitions=[];calls=[];assignments=[];decorators=[]
    parents={child:node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
    globals_=[];messages=set();fingerprints={};top=[]
    for node in ast.walk(tree):
        if isinstance(node,(ast.Import,ast.ImportFrom)):
            imports.append({'line':node.lineno,'module':node.module if isinstance(node,ast.ImportFrom) else None,
                            'names':[(n.name,n.asname) for n in node.names]})
        if isinstance(node,(ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef)):
            lineage=[];parent=parents.get(node)
            while parent is not None:
                if isinstance(parent,(ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef)):lineage.append(parent.name)
                parent=parents.get(parent)
            definitions.append({'line':node.lineno,'name':node.name,'qualname':'.'.join([*reversed(lineage),node.name]),
                                'kind':type(node).__name__,
                                'parameters':ast.unparse(node.args) if hasattr(node,'args') else None,
                                'returns':ast.unparse(node.returns) if getattr(node,'returns',None) is not None else None})
            decorators.extend({'line':node.lineno,'expression':ast.unparse(d)} for d in node.decorator_list)
            if isinstance(node,ast.ClassDef) and len(node.name)>=10:fingerprints[node.name]='CLASS'
        if isinstance(node,ast.Call):
            name=ast.unparse(node.func);calls.append({'line':node.lineno,'name':name})
            if name.endswith(('.new_message','.send')) and node.args and isinstance(node.args[0],ast.Constant) and isinstance(node.args[0].value,str):
                messages.add(node.args[0].value)
                if len(node.args[0].value)>=12:fingerprints[node.args[0].value]='MESSAGE'
        if isinstance(node,(ast.Assign,ast.AnnAssign,ast.AugAssign)):
            targets=node.targets if isinstance(node,ast.Assign) else [node.target]
            assignments.extend({'line':node.lineno,'target':ast.unparse(t)} for t in targets)
    for node in tree.body:
        top.append({'line':node.lineno,'kind':type(node).__name__})
        if isinstance(node,(ast.Assign,ast.AnnAssign)):
            targets=node.targets if isinstance(node,ast.Assign) else [node.target]
            globals_.extend({'name':ast.unparse(t),'value_kind':type(node.value).__name__} for t in targets)
    registrations=[c for c in calls if re.search(r'(?:^|\.)(?:register\w*|\w*callback\w*|\w*hook\w*|subscribe)$',c['name'],re.I)]
    external=[a for a in assignments if ('.' in a['target'] or '[' in a['target']) and not a['target'].startswith(('self.','out.','msg.','raw_params['))]
    unsafe=[c for c in calls if re.search(r'\b(?:exec|eval|__import__|Popen|Thread|Process|sendcan|send_can|send_actuators|write|write_text|write_bytes|unlink|remove|rename|connect)\b',c['name'])]
    singletons=[v for v in globals_ if v['value_kind']=='Call']
    # This category describes observed syntax, never whole-program authority proof.
    category='OBSERVER_WITH_PUBLISH' if messages else 'PURE_DEFINITION_ONLY'
    if registrations or external or unsafe:category='MUTATING_RUNTIME_HELPER'
    if singletons:category='UNKNOWN'
    if any(re.search(r'\b(?:sendcan|send_can|send_actuators|apply_control)\b',c['name']) for c in calls):category='CONTROL_RELEVANT'
    return {'source_sha256':sha(raw),'source_bytes':len(raw),'category':category,
            'imports':imports,'definitions':definitions,'decorators':decorators,'globals':globals_,
            'top_level_statements':top,'calls':calls,'assignments':assignments,
            'messages':sorted(messages),'registration_calls':registrations,'external_assignments':external,
            'unsafe_calls':unsafe,'module_singletons':singletons,
            'fingerprints':[{'value':v,'kind':k,'sha256':sha(v.encode())} for v,k in sorted(fingerprints.items())],
            'executed':False,'static_classification_not_authority_proof':True}


def public_profile(profile):
    return {'source_sha256':profile['source_sha256'],'source_bytes':profile['source_bytes'],
            'category':profile['category'],'imports':len(profile['imports']),'definitions':len(profile['definitions']),
            'fingerprints':[{'id':f'F{i+1:02d}','kind':v['kind'],'sha256':v['sha256']} for i,v in enumerate(profile['fingerprints'])],
            'registration_calls':len(profile['registration_calls']),
            'external_assignments':len(profile['external_assignments']),'executed':False}


def reference_context(raw,profile,*,module):
    if len(raw)>2_000_000:raise ValueError('reference bound')
    tree=ast.parse(raw);tokens={x['value'] for x in profile['fingerprints']};out=[]
    for n in ast.walk(tree):
        if isinstance(n,ast.Import):
            if any(v.name==module for v in n.names):out.append({'line':n.lineno,'kind':'STATIC_IMPORT'})
        elif isinstance(n,ast.ImportFrom):
            if n.module==module:out.append({'line':n.lineno,'kind':'STATIC_IMPORT'})
            elif any(v.name in tokens for v in n.names):out.append({'line':n.lineno,'kind':'DISTINCT_SYMBOL_IMPORT_NOT_MODULE_BOUND'})
        elif isinstance(n,ast.Call):
            name=ast.unparse(n.func)
            if name.endswith(('import_module','__import__','load_module','spec_from_file_location')):
                literals=[a.value for a in n.args if isinstance(a,ast.Constant) and isinstance(a.value,str)]
                target=any(module in v or any(t in v for t in tokens) for v in literals)
                out.append({'line':n.lineno,'kind':'DYNAMIC_LITERAL_TARGET' if target else 'DYNAMIC_UNRESOLVED' if not literals else 'DYNAMIC_OTHER_LITERAL'})
            elif isinstance(n.func,ast.Name) and n.func.id in tokens:out.append({'line':n.lineno,'kind':'DISTINCT_SYMBOL_CALL'})
    return out


class _Marshal312:
    """Intentionally restricted marshal subset for code constants; not a loader."""
    def __init__(self,data):
        self.data=data;self.pos=0;self.refs=[];self.objects=0

    def take(self,n):
        if n<0 or n>1_000_000 or self.pos+n>len(self.data):raise ValueError('marshal bounds')
        b=self.data[self.pos:self.pos+n];self.pos+=n;return b

    def integer(self):
        return struct.unpack('<i',self.take(4))[0]

    def read(self,depth=0):
        self.objects+=1
        if depth>80 or self.objects>50000:raise ValueError('marshal resource cap')
        tag=self.take(1)[0];flag=bool(tag&128);tag=chr(tag&127);slot=None
        if flag:slot=len(self.refs);self.refs.append(None)
        if tag=='r':
            i=self.integer()
            if flag or i<0 or i>=len(self.refs) or self.refs[i] is None:raise ValueError('invalid/cyclic reference')
            return self.refs[i]
        if tag in ('N','F','T','.'):value={'N':None,'F':False,'T':True,'.':Ellipsis}[tag]
        elif tag=='i':value=self.integer()
        elif tag=='l':
            n=self.integer()
            if abs(n)>1024:raise ValueError('integer cap')
            digits=[struct.unpack('<H',self.take(2))[0] for _ in range(abs(n))]
            if any(d>=32768 for d in digits):raise ValueError('long digit')
            value=sum(d<<(15*i) for i,d in enumerate(digits))*(-1 if n<0 else 1)
        elif tag=='g':value=struct.unpack('<d',self.take(8))[0]
        elif tag in ('s','u','t','a','A','z','Z'):
            size=self.take(1)[0] if tag in ('z','Z') else self.integer()
            data=self.take(size)
            value=data if tag=='s' else data.decode('ascii' if tag in ('a','A','z','Z') else 'utf-8')
        elif tag in ('(',')','>'):
            n=self.take(1)[0] if tag==')' else self.integer()
            if n<0 or n>10000:raise ValueError('container cap')
            values=tuple(self.read(depth+1) for _ in range(n))
            value=values if tag!='>' else {'kind':'frozenset','items':values}
        elif tag=='c':
            value={'kind':'code'}
            for k in ('argcount','posonlyargcount','kwonlyargcount','stacksize','flags'):value[k]=self.integer()
            for k in ('bytecode','consts','names','localsplusnames','localspluskinds','filename','name','qualname'):value[k]=self.read(depth+1)
            value['firstlineno']=self.integer()
            for k in ('linetable','exceptiontable'):value[k]=self.read(depth+1)
            if not all(isinstance(value[k],bytes) for k in ('bytecode','localspluskinds','linetable','exceptiontable')):raise ValueError('code bytes')
            if not all(isinstance(value[k],str) for k in ('filename','name','qualname')):raise ValueError('code names')
            if not all(isinstance(value[k],tuple) for k in ('consts','names','localsplusnames')):raise ValueError('code tuples')
            if not all(isinstance(v,str) for k in ('names','localsplusnames') for v in value[k]):raise ValueError('name elements')
        else:raise ValueError('unsupported marshal tag')
        if slot is not None:self.refs[slot]=value
        return value


def _code_summary(code,budget=None):
    if not isinstance(code,dict) or code.get('kind')!='code':raise ValueError('not code metadata')
    if budget is None:budget=[30000,4_000_000]
    def charge(size=0):
        budget[0]-=1;budget[1]-=size
        if min(budget)<0:raise ValueError('expanded metadata cap')
    for key in ('filename','name','qualname'):charge(len(code[key])*2)
    for key in ('names','localsplusnames'):
        for value in code[key]:charge(len(value))
    children=[];strings=[]
    def constants(value):
        charge()
        if isinstance(value,dict) and value.get('kind')=='code':
            child=_code_summary(value,budget);children.append(child)
            return {'type':'code','qualname':value['qualname'],'metadata_sha256':sha(json.dumps(child,sort_keys=True,separators=(',',':')).encode())}
        elif isinstance(value,dict) and value.get('kind')=='frozenset':
            return {'type':'frozenset','items':[constants(v) for v in value['items']]}
        elif isinstance(value,tuple):
            return {'type':'tuple','items':[constants(v) for v in value]}
        elif isinstance(value,str):
            charge(len(value)*2);strings.append(value);return {'type':'str','value':value}
        elif isinstance(value,bytes):return {'type':'bytes','bytes':len(value),'sha256':sha(value)}
        elif isinstance(value,float):return {'type':'float','ieee_le_hex':struct.pack('<d',value).hex()}
        elif value is Ellipsis:return {'type':'ellipsis'}
        elif value is None or type(value) in (int,bool):return {'type':type(value).__name__,'value':value}
        raise ValueError('unsupported constant')
    consts=[constants(v) for v in code['consts']]
    return {k:code[k] for k in ('filename','name','qualname','firstlineno','argcount','posonlyargcount','kwonlyargcount','flags','stacksize')}|{
        'names':list(code['names']),'localsplusnames':list(code['localsplusnames']),
        'bytecode_sha256':sha(code['bytecode']),'linetable_sha256':sha(code['linetable']),
        'exceptiontable_sha256':sha(code['exceptiontable']),'localspluskinds_sha256':sha(code['localspluskinds']),
        'consts':consts,'string_constants':strings,'children':children}


def parse_pyc(raw):
    if not isinstance(raw,bytes) or len(raw)<17 or len(raw)>2_000_000:raise ValueError('pyc bound')
    if raw[:4]!=bytes.fromhex('cb0d0d0a'):raise ValueError('only CPython3.12 supported')
    flags=struct.unpack('<I',raw[4:8])[0]
    if flags not in (0,1,3):raise ValueError('invalid PEP552 flags')
    header={'magic_hex':raw[:4].hex(),'flags':flags,'mode':'HASH_BASED' if flags&1 else 'TIMESTAMP_BASED'}
    if flags&1:header.update(source_hash_hex=raw[8:16].hex(),check_source=bool(flags&2))
    else:header.update(source_mtime_seconds=struct.unpack('<I',raw[8:12])[0],source_bytes=struct.unpack('<I',raw[12:16])[0])
    parser=_Marshal312(raw[16:]);data=parser.read()
    if parser.pos!=len(raw)-16:raise ValueError('trailing marshal bytes')
    return {'header':header,'code':_code_summary(data),'payload_sha256':sha(raw[16:]),'pyc_sha256':sha(raw),
            'objects':parser.objects,'executed':False,'code_objects_constructed':False}


def isolation_decision(evidence):
    reasons=[]
    if not isinstance(evidence,dict):evidence={}
    requirements=evidence.get('requirements');blockers=evidence.get('blockers')
    if not isinstance(requirements,dict):requirements={}
    if not isinstance(blockers,dict):blockers={}
    for key,value in (('source_sha256',U32_SHA),('baseline_digest',BASELINE),('patch_sha256',PATCH)):
        if evidence.get(key)!=value:reasons.append(key.upper()+'_BINDING')
    if not re.fullmatch('[0-9a-f]{64}',str(evidence.get('evidence_sha256',''))):reasons.append('EVIDENCE_BINDING')
    for k in REQUIREMENTS:
        if requirements.get(k) is not True:reasons.append('REQUIRE_'+k.upper())
    for k in BLOCKERS:
        if blockers.get(k) is not False:reasons.append('HOLD_'+k.upper())
    return {'proposal':'HOLD' if reasons else 'U32_UNKNOWN_ACCEPTABLE_FOR_PATCH_ISOLATION',
            'reasons':reasons,'installation_authorized':False,'legacy_attestation_policy_modified':False}


def baseline_preserved(before,after):
    keys=('head','branch','tracked_status','flags','entries','inventory_digest','source_hashes','model_hashes','routes_inventory','boot_id')
    return all(k in before and before[k]==after.get(k) for k in keys) and bool(before.get('entries')) and before.get('proc',{}).get('processes')==after.get('proc',{}).get('processes')


def receipt_digest(value):
    return sha(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode())


def compose_attestation(legacy,evidence,*,checker_sha256):
    """Apply the user's M193 scoped isolation policy, not an unused-runtime claim.

    Requires a trusted frozen-checker receipt and explicitly reviewed private
    proof, both independently committed by digest. These inputs are not author
    authentication. Never edit the old checker/manifest or grant installation.
    """
    decision=isolation_decision(evidence);hard=[];legacy_sha=None;legacy_status=None
    try:
        legacy_sha=receipt_digest(legacy)
        if legacy.get('status') in ('ATTESTED_DIRTY_BASELINE_PASS','ATTESTED_DIRTY_BASELINE_PARTIAL','ATTESTED_DIRTY_BASELINE_FAIL'):
            legacy_status=legacy['status']
        expected={k:k!='U32_POLICY' for k in LEGACY_CHECKS}
        if checker_sha256!=FROZEN_CHECKER_SHA:hard.append('FROZEN_CHECKER_IDENTITY')
        if (legacy.get('schema')!=1 or legacy.get('status')!='ATTESTED_DIRTY_BASELINE_PARTIAL'
                or legacy.get('reasons')!=['U32_PROVENANCE_UNRESOLVED']
                or legacy.get('observed_inventory_digest')!=BASELINE
                or legacy.get('checks')!=expected
                or any(type(v) is not bool for v in legacy['checks'].values())
                or legacy.get('installation_authorized') is not False
                or legacy.get('actual_mutations') is not False):hard.append('LEGACY_STRUCTURAL_GATE')
        if evidence.get('legacy_receipt_sha256')!=legacy_sha:hard.append('LEGACY_RECEIPT_BINDING')
        if evidence.get('boundary_hashes')!=BOUNDARY_PINS:hard.append('CURRENT_BOUNDARY_BINDING')
    except (AttributeError,KeyError,TypeError,ValueError):hard.append('INVALID_COMPOSITION_INPUT')
    passed=not hard and decision['proposal']=='U32_UNKNOWN_ACCEPTABLE_FOR_PATCH_ISOLATION'
    return {'policy':'M193_SCOPED_ISOLATION_V1',
            'status':'ATTESTED_DIRTY_BASELINE_PASS' if passed else 'ATTESTED_DIRTY_BASELINE_FAIL' if hard else 'ATTESTED_DIRTY_BASELINE_PARTIAL',
            'legacy_M192_status':legacy_status,
            'legacy_receipt_sha256':legacy_sha,
            'isolation':decision,'reasons':hard+decision['reasons'],'ready_to_retry_M19':passed,
            'current_runtime_use':'UNKNOWN','installation_authorized':False,'actual_mutations':False}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source');parser.add_argument('--pyc');parser.add_argument('--public',action='store_true')
    args=parser.parse_args()
    try:
        profile=source_profile(Path(args.source).read_bytes())
        out={'source':public_profile(profile) if args.public else profile}
        if args.pyc:
            parsed=parse_pyc(Path(args.pyc).read_bytes())
            out['pyc']={k:parsed[k] for k in ('pyc_sha256','payload_sha256','executed','code_objects_constructed')} if args.public else parsed
        print(json.dumps(out,allow_nan=False));return 0
    except (OSError,ValueError,TypeError,RecursionError,SyntaxError):
        print(json.dumps({'status':'REJECTED_PRIVATE_INPUT','executed':False}));return 1


if __name__=='__main__':
    raise SystemExit(main())
