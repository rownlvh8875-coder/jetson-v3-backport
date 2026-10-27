#!/usr/bin/env python3
"""Verify a disposable current-carrot candidate; never install or change upstream.

Default mode queries remote refs on every run. --reference is explicitly offline
verification of a clean local checkout and cannot advance a validated baseline.
PASS covers CPU software contracts only, never Jetson/TRT/USB/vehicle validation.
"""
import argparse
from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
UPSTREAMS = {
    "carrot-wip": ("https://github.com/ajouatom/openpilot.git", "refs/heads/carrot-wip"),
    "carrot-jetson": ("https://github.com/ajouatom/carrot-jetson.git", "refs/heads/main"),
    "zoompilot/jetlink": ("https://github.com/zoompilot/jetlink.git", "refs/heads/main"),
}
RELEVANT_PATHS = (
    "openpilot/common/jetlink_peer.py",
    "openpilot/selfdrive/modeld/jetlink/",
    "openpilot/selfdrive/modeld/parse_model_outputs.py",
    "openpilot/selfdrive/modeld/model_join.py",
    "openpilot/selfdrive/modeld/modeld.py",
    "openpilot/system/camerad/cameras/nv12_info.py",
    "third_party/jetlink/jetlink/client.py",
    "third_party/jetlink/jetlink/protocol.py",
    "third_party/jetlink/jetlink/protocol_v3.py",
    "third_party/jetlink/jetlink/spec.py",
    "third_party/jetlink/jetlink/queues.py",
    "third_party/jetlink/jetlink/onnx_patch.py",
    "third_party/jetlink/jetlink/server/",
    "tools/jetlink/",
    "openpilot/selfdrive/carrot/server/features/",
    "openpilot/selfdrive/carrot/web/",
)
SPARSE_PATHS = (
    "openpilot/common", "openpilot/selfdrive/modeld", "third_party/jetlink",
    "tools/jetlink", "openpilot/selfdrive/carrot/server/features",
    "openpilot/selfdrive/carrot/web", "openpilot/system/camerad/cameras",
    "openpilot/selfdrive/navigation",
)
CURRENT_TESTS = (
    "test_current_carrot_adapter.py", "test_current_carrot_server.py",
    "test_current_carrot_loopback.py", "test_current_carrot_integration.py",
)


class CheckError(RuntimeError):
    """Verification could not be completed; do not claim compatibility."""


def run_text(command, *, cwd=None, timeout=120):
    try:
        result = subprocess.run(command, cwd=cwd, capture_output=True, text=True,
                                encoding="utf-8", errors="replace", timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CheckError(f"command unavailable or timed out: {command!r}: {exc}") from exc
    if result.returncode:
        raise CheckError(f"command failed ({result.returncode}): {command!r}\n{result.stderr.strip()}")
    return result.stdout.strip()


def git(root, *args):
    return run_text(["git", "-C", str(root), *args])


def full_sha(value):
    if not re.fullmatch(r"[0-9a-f]{40}", value):
        raise CheckError(f"expected full Git SHA, got {value!r}")
    return value


def latest_head(remote, ref):
    lines = run_text(["git", "ls-remote", "--exit-code", remote, ref]).splitlines()
    matching = [line.split("\t")[0] for line in lines if line.endswith("\t" + ref)]
    if len(matching) != 1:
        raise CheckError(f"remote did not return exactly one {ref}: {remote}")
    return full_sha(matching[0])


def resolve_upstreams():
    return {name: {"url": url, "ref": ref, "sha": latest_head(url, ref)}
            for name, (url, ref) in UPSTREAMS.items()}


def fetch_reference(remote, sha, destination, paths=SPARSE_PATHS):
    """Fetch an exact commit into a new reference, never into an existing checkout."""
    full_sha(sha)
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    git(destination, "init", "-q")
    # New references must preserve canonical blob bytes, including on Windows.
    # A global autocrlf setting otherwise changes patch contexts/before hashes.
    git(destination, 'config', 'core.autocrlf', 'false')
    git(destination, 'config', 'core.eol', 'lf')
    git(destination, "remote", "add", "origin", remote)
    git(destination, "sparse-checkout", "init", "--cone")
    git(destination, "sparse-checkout", "set", *paths)
    git(destination, "-c", "fetch.recurseSubmodules=false", "fetch", "--depth=1",
        "--filter=blob:none", "origin", sha)
    git(destination, "-c", "advice.detachedHead=false", "checkout", "--detach", "FETCH_HEAD")
    if git(destination, "rev-parse", "HEAD") != sha:
        raise CheckError("fetched reference does not match the freshly resolved SHA")


def snapshot_blobs(reference, paths=RELEVANT_PATHS):
    records = git(reference, "ls-tree", "-r", "-z", "HEAD", "--", *paths).split("\0")
    result = {}
    for record in records:
        if not record:
            continue
        metadata, name = record.split("\t", 1)
        _, kind, sha = metadata.split()
        if kind != "blob":
            raise CheckError(f"unexpected non-blob in relevant source: {name} ({kind})")
        result[name] = full_sha(sha)
    return result


def changed_blobs(previous, current):
    return {
        "added": sorted(current.keys() - previous.keys()),
        "removed": sorted(previous.keys() - current.keys()),
        "modified": sorted(name for name in previous.keys() & current.keys() if previous[name] != current[name]),
    }


def required_suites(repo, candidate):
    groups = [
        ("current-carrot-integration", [repo / "tests" / name for name in CURRENT_TESTS]),
        ("multimodel-policy", [repo / "tests/test_multimodel_policy.py"]),
        ("trt-builder-cpu-contracts", [repo / "tests/test_v3_build_verify.py"]),
        ("upstream-phase-linux-sockets", [candidate / "openpilot/selfdrive/modeld/tests/test_jetlink_phase.py"]),
        ("upstream-wire-model-cache", [candidate / "tools/jetlink" / name for name in (
            "test_stateful_protocol.py", "test_app_models.py", "test_cache_persistence.py")]),
        ("upstream-modeld-ipc-warp", [candidate / "openpilot/selfdrive/modeld/tests/test_jetlink.py"]),
        ("upstream-native-n16", [candidate / "tools/jetlink" / name for name in (
            "test_resaction_session.py", "test_output_projection.py", "test_packed_codec.py",
            "test_state_buffers.py", "test_device_state.py", "test_direct_map.py", "test_block_codec.py")]),
        ("optional-optimization-contracts", [repo / 'tests' / name for name in (
            'test_jetson_device_state.py', 'test_jetson_input_fastpath.py',
            'test_jetson_aio_candidate.py', 'test_jetson_optimization_integration.py')]),
    ]
    missing = [str(path) for _, paths in groups for path in paths if not path.is_file()]
    if missing:
        raise CheckError("missing required behavioral tests: " + ", ".join(missing))
    return groups


def execute_pytest_suite(name, tests, candidate, repo, output, reference=None, optimization_candidate=None):
    """Use JUnit evidence: pytest success alone also permits skips and xfails."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    junit, log = output / "junit.xml", output / "pytest.log"
    config = output / "pytest.ini"
    config.write_text("[pytest]\n", encoding="utf-8")
    test_paths = [str(Path(path).resolve()) for path in tests]
    common = Path(os.path.commonpath([str(Path(path).resolve().parent) for path in tests]))
    command = [sys.executable, "-m", "pytest", "-q", "-c", str(config),
               "--confcutdir", str(common), "--junitxml", str(junit), *test_paths]
    env = os.environ.copy()
    env["CARROT_CANDIDATE_ROOT"] = str(Path(candidate).resolve())
    if reference is not None:
        env["CARROT_REFERENCE_ROOT"] = str(Path(reference).resolve())
    else:
        env.pop("CARROT_REFERENCE_ROOT", None)
    if optimization_candidate is not None:
        env['CARROT_OPTIMIZATION_ROOT'] = str(Path(optimization_candidate).resolve())
    else:
        env.pop('CARROT_OPTIMIZATION_ROOT', None)
    # Local tests import this repository's legacy helpers; current-source tests
    # explicitly isolate vendor modules. Upstream tests must prefer candidate.
    first = candidate if name.startswith("upstream-") else repo
    second = repo if first == candidate else candidate
    env["PYTHONPATH"] = os.pathsep.join(str(Path(path).resolve()) for path in (first, second))
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    with log.open("w", encoding="utf-8") as stream:
        try:
            completed = subprocess.run(command, cwd=repo, env=env, stdout=stream,
                                       stderr=subprocess.STDOUT, timeout=300)
            returncode = completed.returncode
        except (OSError, subprocess.TimeoutExpired) as exc:
            stream.write(f"\n{exc}\n")
            returncode = -1
    cases = []
    parse_error = None
    try:
        cases = list(ET.parse(junit).iter("testcase"))
    except (OSError, ET.ParseError) as exc:
        parse_error = str(exc)
    skipped = sum(case.find("skipped") is not None for case in cases)
    failures = sum(case.find("failure") is not None for case in cases)
    errors = sum(case.find("error") is not None for case in cases)
    passed = len(cases) - skipped - failures - errors
    status = "PASS" if returncode == 0 and cases and not (skipped or failures or errors or parse_error) else "FAIL"
    return {"name": name, "required": True, "status": status, "evidence": "CPU_FAKE / FIXTURE",
            "command": command, "returncode": returncode, "tests": len(cases), "passed": passed,
            "skipped": skipped, "failures": failures, "errors": errors, "parse_error": parse_error,
            "log": str(log.resolve()), "junit": str(junit.resolve())}


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def update_baseline(path, report):
    checks = [check for check in report.get("checks", []) if check.get("required")]
    if (report.get("mode") != "ONLINE_LATEST" or report.get("status") != "PASS"
            or not report.get("latest_compatible") or not checks
            or any(check.get("status") != "PASS" or check.get("skipped", 0)
                   or check.get("passed", 0) <= 0 for check in checks)):
        raise CheckError("baseline requires full successful online verification with no required skips")
    portable = {key: report[key] for key in (
        "schema_version", "mode", "status", "latest_compatible", "finished_utc",
        "upstreams", "relevant_paths", "relevant_blobs", "candidate_manifest",
        "implementation_sha", "implementation_source_sha256",
        "optimization_candidate_manifest",
    ) if key in report}
    check_fields = ("name", "required", "status", "evidence", "tests", "passed", "skipped", "failures", "errors")
    portable["checks"] = [{key: check[key] for key in check_fields if key in check} for check in checks]
    portable["hardware_validation"] = {"status": "SKIP", "required": False,
                                       "reason": "CPU software evidence only; device validation remains separate"}
    write_json(path, portable)


def assert_clean_reference(reference):
    if git(reference, "status", "--porcelain", "--untracked-files=all"):
        raise CheckError("reference must be clean; refusing to validate modified or untracked source")


def local_source_hashes(repo=ROOT):
    repo = Path(repo)
    names = ("tools/check_latest_carrot_compat.py", "jetlink/cinque_v3.py", "jetlink/queues.py",
             "jetlink/spec.py", "jetlink/onnx_meta.py", "jetlink/multimodel_policy.py",
             "tools/build_trt_v3.py", "tools/patch_v3_uint8.py", "artifacts/cinque_v3.json",
             "tests/test_latest_carrot_compat.py", "tests/test_multimodel_policy.py",
             "tests/test_v3_build_verify.py", "tests/test_production_v3.py",
             ".github/workflows/carrot-wip-compat.yml")
    paths = [*(repo / name for name in names), *repo.glob("adapters/**/*.py"),
             *repo.glob("tests/test_current_carrot_*.py"), *repo.glob("tests/current_carrot_*.py"),
             *repo.glob('experimental/**/*.py'), *repo.glob('experimental/**/*.c'),
             *repo.glob('experimental/**/LICENSE'), *repo.glob('experimental/**/UPSTREAM.md'),
             *repo.glob('tests/test_jetson_*.py'), *repo.glob('tests/jetson_*.py')]
    return {path.relative_to(repo).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(set(paths)) if path.is_file()}


def assert_source_unchanged(expected, repo=ROOT):
    if local_source_hashes(repo) != expected:
        raise CheckError("implementation changed during verification; rerun the complete candidate checks")


def verify(args, report, workspace, artifacts):
    if args.reference:
        reference = args.reference.resolve()
        report["upstreams"] = {"carrot-wip": {"sha": full_sha(git(reference, "rev-parse", "HEAD")),
                                                       "source": str(reference), "latest_queried": False}}
    else:
        report["upstreams"] = resolve_upstreams()
        reference = workspace / "reference"
        upstream = report["upstreams"]["carrot-wip"]
        fetch_reference(upstream["url"], upstream["sha"], reference)
    assert_clean_reference(reference)
    report["reference_root"] = str(reference)
    report["relevant_paths"] = list(RELEVANT_PATHS)
    report["relevant_blobs"] = snapshot_blobs(reference)
    baseline = json.loads(args.baseline.read_text(encoding="utf-8")) if args.baseline.exists() else None
    report["baseline"] = {"path": str(args.baseline), "available": baseline is not None,
                          "upstreams": baseline.get("upstreams") if baseline else None}
    report["relevant_changes"] = changed_blobs(baseline.get("relevant_blobs", {}) if baseline else {},
                                              report["relevant_blobs"])
    print(f"{report['mode']}: carrot-wip {report['upstreams']['carrot-wip']['sha']}", flush=True)
    print("Changed integration files" + (" (no validated baseline yet):" if baseline is None else ":"), flush=True)
    changed = report["relevant_changes"]
    for kind in ("added", "modified", "removed"):
        for name in changed[kind]:
            print(f"  {kind}: {name}", flush=True)
    if not any(changed.values()):
        print("  none", flush=True)
    sys.path.insert(0, str(ROOT))
    from adapters.carrot.integration import build_candidate
    candidate = workspace / "candidate"
    try:
        report["candidate_manifest"] = build_candidate(reference, candidate)
    except Exception as exc:
        # Signature drift is a failed compatibility gate, never an adaptation success.
        report["checks"].append({"name": "candidate-adapter", "required": True, "status": "FAIL",
                                 "error": f"{type(exc).__name__}: {exc}"})
        report["status"] = "FAIL"
        return
    report["candidate_root"] = str(candidate)
    for filename in ("candidate.patch", "manifest.json"):
        source = candidate / ".jetlink-candidate" / filename
        if not source.is_file():
            raise CheckError(f"candidate builder did not produce required review artifact: {source}")
        shutil.copyfile(source, artifacts / filename)
    optimization = workspace / 'optimization-candidate'
    try:
        report['optimization_candidate_manifest'] = build_candidate(reference, optimization, experimental_optimizations=True)
    except Exception as exc:
        report['checks'].append({'name': 'optimization-adapter', 'required': True, 'status': 'FAIL',
                                 'error': f'{type(exc).__name__}: {exc}'})
        report['status'] = 'FAIL'
        return
    for filename in ('candidate.patch', 'manifest.json'):
        shutil.copyfile(optimization / '.jetlink-candidate' / filename, artifacts / ('experimental-' + filename))
    for name, tests in required_suites(ROOT, candidate):
        result = execute_pytest_suite(name, tests, candidate, ROOT, artifacts / name,
                                      reference=reference, optimization_candidate=optimization)
        report["checks"].append(result)
        print(f"{result['status']}: {name}: {result['passed']}/{result['tests']} passed, "
              f"{result['skipped']} skipped ({result['log']})", flush=True)
    assert_clean_reference(reference)
    assert_source_unchanged(report["implementation_source_sha256"])
    if any(check["status"] != "PASS" for check in report["checks"] if check["required"]):
        report["status"] = "FAIL"
        return
    if not args.reference:
        report["upstreams_after_verification"] = resolve_upstreams()
        if report["upstreams_after_verification"] != report["upstreams"]:
            raise CheckError("upstream moved during verification; rerun against its new latest HEAD")
        report["latest_compatible"] = True
    report["status"] = "PASS"
    if args.update_baseline:
        report["finished_utc"] = datetime.now(timezone.utc).isoformat()
        update_baseline(args.baseline, report)
        report["baseline_updated"] = True


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, help="OFFLINE only: verify an existing clean checkout")
    parser.add_argument("--report", type=Path, default=ROOT / ".reports/carrot-compat.json")
    parser.add_argument("--baseline", type=Path, default=ROOT / "artifacts/carrot_compat_baseline.json")
    parser.add_argument("--update-baseline", action="store_true", help="advance baseline only after full ONLINE PASS")
    parser.add_argument("--work-dir", type=Path, help="keep reference/candidate in this NEW directory for review")
    args = parser.parse_args(argv)
    args.report, args.baseline = args.report.resolve(), args.baseline.resolve()
    report = {"schema_version": 1, "mode": "OFFLINE_REFERENCE" if args.reference else "ONLINE_LATEST",
              "status": "BLOCKED", "latest_compatible": False, "baseline_updated": False,
              "started_utc": datetime.now(timezone.utc).isoformat(), "checks": [],
              "environment": {"python": sys.version, "executable": sys.executable, "platform": platform.platform()},
              "hardware_validation": {"status": "SKIP", "required": False,
                                      "reason": "No Jetson/TensorRT/USB/vehicle execution; CPU software evidence only"},
              "invocation": [sys.executable, str(Path(__file__).resolve()), *(argv if argv is not None else sys.argv[1:])]}
    try:
        report["implementation_sha"] = full_sha(git(ROOT, "rev-parse", "HEAD"))
        report["implementation_changes"] = git(ROOT, "status", "--porcelain")
        report["implementation_source_sha256"] = local_source_hashes()
        if args.reference and args.update_baseline:
            raise CheckError("--update-baseline cannot be used with an OFFLINE --reference")
        artifacts = args.report.parent / args.report.stem
        artifacts.mkdir(parents=True, exist_ok=True)
        with ExitStack() as stack:
            if args.work_dir:
                workspace = args.work_dir.resolve()
                workspace.mkdir(parents=True, exist_ok=False)
            else:
                workspace = Path(stack.enter_context(tempfile.TemporaryDirectory(prefix="carrot-compat-")))
            verify(args, report, workspace, artifacts)
    except Exception as exc:
        report["status"] = "BLOCKED"
        report["latest_compatible"] = False
        report["error"] = f"{type(exc).__name__}: {exc}"
        print(report["error"], file=sys.stderr, flush=True)
    report["finished_utc"] = datetime.now(timezone.utc).isoformat()
    write_json(args.report, report)
    print(f"{report['status']}: {args.report}", flush=True)
    return {"PASS": 0, "FAIL": 1, "BLOCKED": 2}[report["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
