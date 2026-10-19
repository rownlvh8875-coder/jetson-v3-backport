"""Managed Jetson preparation; installed only into a disposable candidate.

HELLO describes a capability. The current Carrot validators and offroad exact
approval remain the trust boundary. This module performs no provisioning.
"""
import json
from pathlib import Path

from openpilot.common.jetlink_managed import is_managed_jetson_peer, loaded_sha
from openpilot.selfdrive.modeld.jetlink.contracts import validate_model_spec
from openpilot.selfdrive.modeld.jetlink.selection import ModelChanged, approved_spec, remember_spec
from jetlink.client import EngineMissing


def prepare_managed(client, peer, offroad, connected, progress, cache, mode='usb'):
  # Import here because mac routes to this module before its legacy branches.
  from openpilot.selfdrive.modeld.jetlink.mac import PreparationDeferred, PreparationTransport, require_setup

  if not is_managed_jetson_peer(peer, mode):
    raise ValueError('Invalid managed Jetson selection capability')
  selected = loaded_sha(peer, mode)
  if selected is None:
    raise PreparationDeferred('Selected Jetson engine is not resident; prepare it offroad')
  cache = Path(cache) / 'managed-jetson'
  approved = approved_spec(cache)
  needs_approval = approved is None or approved.sha256 != selected
  if needs_approval:
    require_setup(offroad, connected)

  def check():
    if not connected():
      raise PreparationDeferred('Jetlink host disconnected; waiting for reconnection')
    if needs_approval:
      require_setup(offroad, connected)

  def stopped():
    # The managed server contract allows resident engines only. If an older
    # server reports pending preparation, stop before waiting/building onroad.
    require_setup(offroad, connected)
    return False

  def report(*args):
    require_setup(offroad, connected)
    progress(*args)

  original = client.t
  client.t = PreparationTransport(original, check)
  try:
    check()
    current = client.state()
    if not isinstance(current, dict) or current.get('loaded') != selected:
      raise ModelChanged('Managed Jetson identity changed before approval')
    try:
      result = client.ensure_engine(selected, approved.nbytes if not needs_approval else 0,
                                    frame_skip=4, build_timeout=30,
                                    should_stop=stopped, progress=report)
    except EngineMissing:
      raise PreparationDeferred('Selected Jetson engine is not ready; prepare it offroad') from None
    validate_model_spec(result)
    if result.sha256 != selected:
      raise ValueError('Managed Jetson ready SHA does not match HELLO selection')
    canonical = json.loads(Path(__file__).with_name('cinque_v3.json').read_text())
    if selected == canonical['sha256'] and result.to_dict() != canonical:
      raise ValueError('Cinque V3 identity/spec does not match verified seed contract')
    if approved is not None and approved.sha256 == selected and approved.to_dict() != result.to_dict():
      raise ValueError('Previously approved Jetson model contract changed')
    # Detect selection changes during ENGINE_REQ before publishing approval.
    current = client.state()
    if not isinstance(current, dict) or current.get('loaded') != selected:
      raise ModelChanged('Managed Jetson identity changed during approval')
    check()
    if needs_approval:
      require_setup(offroad, connected)
      remember_spec(cache, result)
    return result
  finally:
    client.t = original
    client.progress_cb = None
    client._should_stop = lambda: False
