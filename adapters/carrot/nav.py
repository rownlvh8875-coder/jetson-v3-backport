"""Comma-only managed P3 candidate for the installed exact carrot-nav source.

No host port, update, activation or reference mutation. Existing WIP source
guards remain unchanged; legacy Nav serialization and selection stay intact.
"""
from __future__ import annotations
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import shutil
from adapters.carrot.integration import REPO,comma_files,git,replace_once

BASE='366d6eae9aa9962104391e1d997fe956dea8f64d'
SPEC='third_party/jetlink/jetlink/spec.py'


def nav_files(reference):
    changes=comma_files(reference)
    spec=(reference/SPEC).read_text(encoding='utf-8')
    def replace(old,new):
        nonlocal spec
        spec=replace_once(spec,old,new,'Nav ModelSpec serialization')
    replace('from dataclasses import dataclass','from dataclasses import dataclass, field')
    replace('  checkpoint: str | None\n','  checkpoint: str | None\n  input_dtypes: dict[str, str] = field(default_factory=dict)\n  output_dtypes: dict[str, str] = field(default_factory=dict)\n')
    replace('  def to_dict(self) -> dict:\n    return {','  def to_dict(self) -> dict:\n    d = {')
    replace("      'output_slices': {k: [v.start, v.stop] for k, v in self.output_slices.items()},\n    }", "      'output_slices': {k: [v.start, v.stop] for k, v in self.output_slices.items()},\n    }\n    if self.input_dtypes:\n      d['input_dtypes'] = dict(self.input_dtypes)\n    if self.output_dtypes:\n      d['output_dtypes'] = dict(self.output_dtypes)\n    return d")
    replace("      checkpoint=d.get('checkpoint'))", "      checkpoint=d.get('checkpoint'),\n      input_dtypes=dict(d.get('input_dtypes', {})),\n      output_dtypes=dict(d.get('output_dtypes', {})))")
    # Do not infer or populate maps from metadata for legacy Nav: N16 hashes
    # the exact dictionary. Only explicit declarations survive wire roundtrip.
    changes[SPEC]=spec.encode()
    name='openpilot/selfdrive/modeld/jetlink/managed.py'
    managed=changes[name].decode()
    managed=replace_once(managed,'  cache = Path(cache) / \'managed-jetson\'\n', '''  # Nav candidate catalog is deliberately limited to reviewed exact seeds.
  # Capability metadata alone cannot authorize an arbitrary compatible graph.
  from jetlink.spec import ModelSpec
  from openpilot.selfdrive.modeld.jetlink.contracts import DEFAULT_SPEC, JETSON_SPEC
  canonical = json.loads(Path(__file__).with_name('cinque_v3.json').read_text())
  v3 = ModelSpec.from_dict(canonical)
  catalog = {spec.sha256: spec.to_dict() for spec in (DEFAULT_SPEC, JETSON_SPEC, v3)}
  if selected not in catalog:
    raise ValueError('Unknown managed Jetson model; exact reviewed catalog entry required')
  cache = Path(cache) / 'managed-jetson'
''','Nav managed catalog')
    managed=replace_once(managed,"    canonical = json.loads(Path(__file__).with_name('cinque_v3.json').read_text())\n    if selected == canonical['sha256'] and result.to_dict() != canonical:\n      raise ValueError('Cinque V3 identity/spec does not match verified seed contract')", "    if result.to_dict() != catalog[selected]:\n      raise ValueError('Managed model identity/spec does not match exact reviewed catalog')",'Nav exact seed gate')
    changes[name]=managed.encode()
    return changes


def build_nav_candidate(reference,destination):
    reference,destination=Path(reference).resolve(),Path(destination).resolve()
    if destination.exists() or destination==reference or reference in destination.parents:
        raise ValueError('fresh candidate outside reference required')
    base=git(reference,'rev-parse','HEAD').decode().strip()
    if base!=BASE:raise ValueError('INCOMPATIBLE: actual Nav base changed; review before porting')
    if git(reference,'status','--porcelain','--untracked-files=all').strip():raise ValueError('clean Nav reference required')
    changes=nav_files(reference) # All source anchors must match before writes.
    destination.mkdir(parents=True)
    names=[r[2:] for r in git(reference,'ls-files','-t','-z').decode().split('\0') if r.startswith('H ')]
    for name in names:
        p=reference/name
        if p.is_file() and not p.is_symlink():
            target=destination/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
    touched=[];hunks=[]
    for name,after in sorted(changes.items()):
        before=(reference/name).read_bytes() if (reference/name).is_file() else None
        target=destination/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(after)
        touched.append({'path':name,'before_sha256':hashlib.sha256(before).hexdigest() if before is not None else None,'after_sha256':hashlib.sha256(after).hexdigest()})
        hunks.extend(difflib.unified_diff((before or b'').decode().splitlines(True),after.decode().splitlines(True),fromfile='a/'+name if before is not None else '/dev/null',tofile='b/'+name))
    patch=''.join(hunks).encode()
    manifest={'schema':1,'base_sha':base,'branch':'carrot-nav','repository':'https://github.com/ajouatom/openpilot',
              'status':'CANDIDATE_UNVERIFIED','evidence':'CPU_FAKE/FIXTURE only until checked','installation':'DO_NOT_INSTALL',
              'patch_sha256':hashlib.sha256(patch).hexdigest(),'touched_files':touched,
              'host':'existing WIP host candidate in separate process; no Nav server port',
              'rollback':'Check exact after hashes; reverse patch only in disposable development copy and verify before hashes. Operating V2/Nav/cache/current remain untouched.'}
    out=destination/'.jetlink-candidate';out.mkdir()
    (out/'candidate.patch').write_bytes(patch);(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('reference',type=Path);p.add_argument('destination',type=Path)
    a=p.parse_args();print(json.dumps(build_nav_candidate(a.reference,a.destination),indent=2))


if __name__=='__main__':main()
