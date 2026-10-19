"""Rolling checker gates exercised with real local Git and pytest processes."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "tools/check_latest_carrot_compat.py"


def checker():
    assert SCRIPT.is_file(), "rolling compatibility checker is not implemented"
    spec = importlib.util.spec_from_file_location("latest_carrot_compat", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(path, *args):
    return subprocess.check_output(["git", "-C", str(path), *args], text=True).strip()


def repository(path):
    path.mkdir()
    git(path, "init", "-q")
    git(path, "config", "user.name", "Checker Fixture")
    git(path, "config", "user.email", "fixture@example.invalid")
    (path / "watched").mkdir()
    (path / "watched/client.py").write_text("VALUE = 1\n")
    (path / "unrelated.txt").write_text("unrelated\n")
    commit(path)
    return path


def commit(path):
    git(path, "add", ".")
    git(path, "commit", "-qm", "fixture")
    return git(path, "rev-parse", "HEAD")


def test_latest_head_reads_remote_ref_instead_of_local_cached_head(tmp_path):
    c = checker()
    remote = repository(tmp_path / "remote")
    branch = git(remote, "branch", "--show-current")
    first = c.latest_head(str(remote), f"refs/heads/{branch}")
    (remote / "watched/client.py").write_text("VALUE = 2\n")
    second = commit(remote)
    assert c.latest_head(str(remote), f"refs/heads/{branch}") == second
    assert second != first


def test_tree_diff_reports_added_removed_changed_and_ignores_other_paths(tmp_path):
    c = checker()
    root = repository(tmp_path / "reference")
    before = c.snapshot_blobs(root, ["watched/"])
    (root / "watched/client.py").write_text("VALUE = 2\n")
    (root / "watched/new.py").write_text("new\n")
    (root / "unrelated.txt").write_text("different\n")
    commit(root)
    after = c.snapshot_blobs(root, ["watched/"])
    assert c.changed_blobs(before, after) == {
        "added": ["watched/new.py"], "removed": [], "modified": ["watched/client.py"]}
    (root / "watched/client.py").unlink()
    commit(root)
    assert c.changed_blobs(after, c.snapshot_blobs(root, ["watched/"])) == {
        "added": [], "removed": ["watched/client.py"], "modified": []}


def test_exact_reference_fetch_is_separate_and_does_not_modify_remote(tmp_path):
    c = checker()
    remote = repository(tmp_path / "remote")
    expected = git(remote, "rev-parse", "HEAD")
    destination = tmp_path / "reference"
    c.fetch_reference(str(remote), expected, destination, ["watched"])
    assert git(destination, "rev-parse", "HEAD") == expected
    assert (destination / "watched/client.py").read_text() == "VALUE = 1\n"
    assert git(remote, "status", "--porcelain") == ""


@pytest.mark.parametrize(("body", "expected", "passed", "skipped"), [
    ("assert True", "PASS", 1, 0),
    ("assert False", "FAIL", 0, 0),
    ("import pytest; pytest.skip('required integration unavailable')", "FAIL", 0, 1),
    ("import pytest; pytest.xfail('known issue')", "FAIL", 0, 1),
])
def test_required_pytest_group_fails_closed_on_failure_skip_or_xfail(tmp_path, body, expected, passed, skipped):
    c = checker()
    case = tmp_path / "test_case.py"
    case.write_text(f"def test_behavior():\n    {body}\n")
    result = c.execute_pytest_suite("fixture", [case], tmp_path, tmp_path, tmp_path / "result")
    assert result["status"] == expected
    assert result["passed"] == passed
    assert result["skipped"] == skipped
    assert Path(result["log"]).is_file()
    assert result["command"][0] == sys.executable


def test_required_pytest_group_rejects_zero_collected_tests(tmp_path):
    c = checker()
    case = tmp_path / "test_empty.py"
    case.write_text("VALUE = 1\n")
    result = c.execute_pytest_suite("empty", [case], tmp_path, tmp_path, tmp_path / "result")
    assert result["status"] == "FAIL"
    assert result["tests"] == 0


def test_required_pytest_process_receives_candidate_reference_and_isolates_parent_pythonpath(tmp_path, monkeypatch):
    c = checker()
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    (candidate / "current_module.py").write_text("VALUE = 'candidate source'\n")
    reference = tmp_path / "clean-reference"
    reference.mkdir()
    (reference / "identity").write_text("clean source\n")
    monkeypatch.setenv("PYTHONPATH", "/invalid/stale/development")
    monkeypatch.setenv("CARROT_REFERENCE_ROOT", "/invalid/stale/reference")
    case = tmp_path / "test_import.py"
    case.write_text("import os\nfrom pathlib import Path\nimport current_module\n"
                    "def test_behavior():\n"
                    "    assert current_module.VALUE == 'candidate source'\n"
                    "    assert Path(current_module.__file__).parent == Path(os.environ['CARROT_CANDIDATE_ROOT'])\n"
                    "    assert (Path(os.environ['CARROT_REFERENCE_ROOT']) / 'identity').read_text() == 'clean source\\n'\n")
    result = c.execute_pytest_suite("import", [case], candidate, tmp_path, tmp_path / "result", reference=reference)
    assert result["status"] == "PASS", Path(result["log"]).read_text()


@pytest.mark.parametrize(("mode", "group_status", "latest_compatible"), [
    ("OFFLINE_REFERENCE", "PASS", False),
    ("ONLINE_LATEST", "FAIL", False),
    ("ONLINE_LATEST", "SKIP", False),
    ("ONLINE_LATEST", "PASS", False),
])
def test_baseline_is_unchanged_without_full_online_success(tmp_path, mode, group_status, latest_compatible):
    c = checker()
    baseline = tmp_path / "baseline.json"
    baseline.write_text('{"previous": "validated"}\n')
    original = baseline.read_bytes()
    report = {"mode": mode, "status": "PASS", "latest_compatible": latest_compatible,
              "checks": [{"required": True, "status": group_status, "tests": 1, "passed": 1, "skipped": 0}]}
    with pytest.raises(c.CheckError):
        c.update_baseline(baseline, report)
    assert baseline.read_bytes() == original


def test_baseline_updates_only_after_full_online_success(tmp_path):
    c = checker()
    baseline = tmp_path / "baseline.json"
    report = {"mode": "ONLINE_LATEST", "status": "PASS", "latest_compatible": True,
              "upstreams": {"carrot-wip": {"sha": "a" * 40}},
              "relevant_blobs": {"watched/client.py": "b" * 40},
              "checks": [{"required": True, "status": "PASS", "tests": 2, "passed": 2, "skipped": 0}]}
    c.update_baseline(baseline, report)
    saved = json.loads(baseline.read_text())
    assert saved["upstreams"]["carrot-wip"]["sha"] == "a" * 40
    assert saved["relevant_blobs"] == {"watched/client.py": "b" * 40}


def test_validated_baseline_contains_portable_evidence_without_local_paths(tmp_path):
    c = checker()
    baseline = tmp_path / "baseline.json"
    report = {"mode": "ONLINE_LATEST", "status": "PASS", "latest_compatible": True,
              "upstreams": {"carrot-wip": {"sha": "a" * 40, "url": "https://example.invalid/repo"}},
              "relevant_blobs": {"watched/client.py": "b" * 40},
              "candidate_manifest": {"base_sha": "a" * 40, "patch_sha256": "c" * 64, "touched_files": []},
              "implementation_source_sha256": {"tools/check_latest_carrot_compat.py": "d" * 64},
              "reference_root": "/home/private/checkouts/reference",
              "invocation": ["/home/private/venv/python", "/home/private/checker.py"],
              "checks": [{"name": "behavior", "required": True, "status": "PASS", "tests": 2,
                          "passed": 2, "skipped": 0, "evidence": "CPU_FAKE", "command": ["/home/private/python"],
                          "log": "/home/private/log"}]}
    c.update_baseline(baseline, report)
    saved = json.loads(baseline.read_text())
    assert "/home/private" not in baseline.read_text()
    assert saved["checks"][0]["passed"] == 2
    assert saved["candidate_manifest"]["patch_sha256"] == "c" * 64
    assert saved["implementation_source_sha256"] == {"tools/check_latest_carrot_compat.py": "d" * 64}


def test_source_provenance_includes_recurrent_helpers_and_behavioral_peer(tmp_path):
    c = checker()
    paths = ["tools/check_latest_carrot_compat.py", "jetlink/queues.py", "jetlink/spec.py",
             "jetlink/cinque_v3.py", "jetlink/onnx_meta.py", "jetlink/multimodel_policy.py",
             "tools/build_trt_v3.py", "tools/patch_v3_uint8.py", "artifacts/cinque_v3.json",
             "tests/current_carrot_loopback_peer.py", "tests/current_carrot_server_trt.py",
             "tests/test_production_v3.py"]
    for name in paths:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("original\n")
    before = c.local_source_hashes(tmp_path)
    assert set(paths) <= before.keys()
    (tmp_path / "jetlink/queues.py").write_text("changed recurrent validation\n")
    assert c.local_source_hashes(tmp_path)["jetlink/queues.py"] != before["jetlink/queues.py"]
    with pytest.raises(c.CheckError, match="implementation changed"):
        c.assert_source_unchanged(before, tmp_path)


def test_cli_writes_blocked_report_and_nonzero_exit_for_missing_reference(tmp_path):
    assert SCRIPT.is_file(), "rolling compatibility checker is not implemented"
    report = tmp_path / "report.json"
    result = subprocess.run([sys.executable, str(SCRIPT), "--reference", str(tmp_path / "absent"),
                             "--report", str(report)], capture_output=True, text=True)
    assert result.returncode != 0
    saved = json.loads(report.read_text())
    assert saved["status"] == "BLOCKED"
    assert saved["mode"] == "OFFLINE_REFERENCE"
    assert saved["latest_compatible"] is False


def test_changed_upstream_prepare_signature_is_failed_compatibility_not_pass(tmp_path):
    c = checker()
    reference = repository(tmp_path / "reference")
    peer = reference / "openpilot/common/jetlink_peer.py"
    mac = reference / "openpilot/selfdrive/modeld/jetlink/mac.py"
    peer.parent.mkdir(parents=True)
    mac.parent.mkdir(parents=True)
    peer.write_text("import re\n")
    mac.write_text("def prepare(client, incompatible_signature):\n    pass\n")
    commit(reference)
    report = tmp_path / "report.json"
    result = subprocess.run([sys.executable, str(SCRIPT), "--reference", str(reference),
                             "--report", str(report)], capture_output=True, text=True)
    saved = json.loads(report.read_text())
    assert result.returncode == 1, result.stdout + result.stderr
    assert saved["status"] == "FAIL"
    assert saved["latest_compatible"] is False
    assert saved["checks"][0]["status"] == "FAIL"
    assert "mac.prepare signature" in saved["checks"][0]["error"]


def test_dirty_reference_is_rejected_before_candidate_creation(tmp_path):
    c = checker()
    reference = repository(tmp_path / "reference")
    (reference / "watched/client.py").write_text("uncommitted source\n")
    report = tmp_path / "report.json"
    workspace = tmp_path / "work"
    result = subprocess.run([sys.executable, str(SCRIPT), "--reference", str(reference),
                             "--report", str(report), "--work-dir", str(workspace)], capture_output=True, text=True)
    saved = json.loads(report.read_text())
    assert result.returncode == 2
    assert saved["status"] == "BLOCKED"
    assert "reference must be clean" in saved["error"]
    assert not (workspace / "candidate").exists()


def test_required_suite_discovery_refuses_missing_current_integration(tmp_path):
    c = checker()
    with pytest.raises(c.CheckError, match="required"):
        c.required_suites(tmp_path, tmp_path)
