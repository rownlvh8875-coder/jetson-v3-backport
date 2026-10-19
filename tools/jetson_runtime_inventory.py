#!/usr/bin/env python3
"""Read-only Carrot Jetson runtime inventory.

This script intentionally performs no package installation, service restart,
mount, write, model build, GPU initialization, or network configuration.
It prints JSON to stdout. Redirect it to a file on the caller side if desired.

Do not add environment dumps, NetworkManager profiles, SSH material, or other
secrets to this report.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
from typing import Any


MAX_HASH_BYTES = 32 << 20

KNOWN_PATHS = (
    "/opt/carrot-jetlink",
    "/opt/carrot",
    "/home/jetlink",
    "/data",
    "/var/lib/carrot-jetlink",
    "/usr/local/lib/carrot-jetlink",
    "/etc/carrot-jetlink-protected.json",
    "/run/carrot-storage.json",
)

KNOWN_UNITS = (
    "carrot-jetlink.service",
    "carrot-jetlink-wifi.service",
    "carrot-jetlink-hud.service",
    "carrot-jetlink-boot-display.service",
)


def run(argv: list[str], timeout: float = 8.0) -> dict[str, Any]:
    try:
        result = subprocess.run(
            argv,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            errors="replace",
            timeout=timeout,
            check=False,
            env={**os.environ, "LC_ALL": "C"},
        )
        return {
            "argv": argv,
            "returncode": result.returncode,
            "stdout": result.stdout.rstrip(),
            "stderr": result.stderr.rstrip(),
        }
    except FileNotFoundError:
        return {"argv": argv, "missing": True}
    except subprocess.TimeoutExpired:
        return {"argv": argv, "timeout": True}


def small_file_info(path: Path) -> dict[str, Any]:
    value: dict[str, Any] = {"path": str(path), "exists": path.exists() or path.is_symlink()}
    if not value["exists"]:
        return value
    try:
        st = path.lstat()
        value.update(
            type="symlink" if path.is_symlink() else "dir" if path.is_dir() else "file",
            size=st.st_size,
            mode=oct(st.st_mode & 0o7777),
        )
        if path.is_symlink():
            value["target"] = os.readlink(path)
        elif path.is_file() and st.st_size <= MAX_HASH_BYTES:
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                for block in iter(lambda: stream.read(1 << 20), b""):
                    digest.update(block)
            value["sha256"] = digest.hexdigest()
    except (OSError, PermissionError) as exc:
        value["error"] = f"{type(exc).__name__}: {exc}"
    return value


def git_state(path: Path) -> dict[str, Any] | None:
    if not (path / ".git").exists():
        return None
    head = run(["git", "-C", str(path), "rev-parse", "HEAD"])
    branch = run(["git", "-C", str(path), "branch", "--show-current"])
    status = run(["git", "-C", str(path), "status", "--porcelain=v1"])
    return {
        "path": str(path),
        "head": head,
        "branch": branch,
        "status": status,
    }


def service_state(unit: str) -> dict[str, Any]:
    return run([
        "systemctl", "show", unit,
        "--property=Id,LoadState,ActiveState,SubState,FragmentPath,ExecMainPID,ExecStart",
        "--no-pager",
    ])


def python_module_version(module: str) -> dict[str, Any]:
    code = (
        "import importlib; "
        f"m=importlib.import_module({module!r}); "
        "print(getattr(m, '__version__', 'unknown'))"
    )
    return run(["python3", "-c", code])


def main() -> int:
    parser = argparse.ArgumentParser(description="Print a read-only Carrot Jetson runtime inventory as JSON.")
    parser.add_argument("--pretty", action="store_true", help="indent JSON for humans")
    args = parser.parse_args()

    report: dict[str, Any] = {
        "schema": 1,
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "read_only": True,
        "host": {
            "hostname": platform.node(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        "commands": {},
        "paths": [],
        "services": {},
        "git": [],
    }

    commands = {
        "uname": ["uname", "-a"],
        "l4t_release": ["cat", "/etc/nv_tegra_release"],
        "os_release": ["cat", "/etc/os-release"],
        "lsblk": ["lsblk", "-J", "-o", "NAME,SIZE,TYPE,FSTYPE,LABEL,MOUNTPOINTS,MODEL,SERIAL"],
        "findmnt_root": ["findmnt", "-J", "/"],
        "ipv4": ["ip", "-j", "-4", "addr", "show", "scope", "global"],
        "nvpmodel": ["/usr/sbin/nvpmodel", "-q"],
        "jetson_clocks": ["/usr/bin/jetson_clocks", "--show"],
        "nvcc": ["nvcc", "--version"],
        "nvidia_smi": ["nvidia-smi"],
        "tensorrt_packages": [
            "dpkg-query", "-W",
            "-f=${Package}\t${Version}\n",
            "libnvinfer*", "tensorrt*",
        ],
    }
    for name, argv in commands.items():
        report["commands"][name] = run(argv)

    report["commands"]["python_tensorrt"] = python_module_version("tensorrt")
    report["commands"]["python_cuda"] = python_module_version("cuda")

    for item in KNOWN_PATHS:
        report["paths"].append(small_file_info(Path(item)))

    for unit in KNOWN_UNITS:
        report["services"][unit] = service_state(unit)

    report["commands"]["related_units"] = run([
        "systemctl", "list-unit-files",
        "carrot*", "jetlink*",
        "--no-legend", "--no-pager",
    ])

    for candidate in (
        Path("/opt/carrot-jetlink/current"),
        Path("/opt/carrot-jetlink"),
        Path("/home/jetlink/carrot"),
        Path("/home/jetlink/jetlink"),
    ):
        state = git_state(candidate)
        if state is not None:
            report["git"].append(state)

    for binary in ("python3", "jetlink", "jetlink-server", "trtexec", "git"):
        report.setdefault("which", {})[binary] = shutil.which(binary)

    print(json.dumps(report, indent=2 if args.pretty else None, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
