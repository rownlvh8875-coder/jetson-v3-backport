# M19-C1.5C — lightweight process diagnosis · 2026-10-26

**BLOCKED_PROCESS_SCOPE_UNAVAILABLE.** One actual read-only diagnostic was
incomplete. No recorder redeployment, policy acceptance, ticket or capture followed.

The device remained carrot-nav at exact24c
`24c1ba5e4b3428f56fa0e402f5a10097e2e94c32`. Six pure24c/surviving5bb PRE hashes,
41 source pins, N16 source contract, index and existing empty private storage
passed their measured guards. The recorder footer remained absent. Writer0,
frames0, datasetNONE; no restart, Jetson access or operational configuration write.
These source/storage observations do not establish full critical-process or
operating preservation.

## What was measured

The first two device commands were the OFF/ON parameter reads:1/0. A separate
12.080372668s receive-only preflight passed, with22 deviceState,111 pandaStates
and22 managerState fresh samples. No prior OFF evidence substituted for it.

The single main process window lasted60.016269732s, bracketed by a simultaneous
70.067792366s receive-only OFF window. Its129/647/129 fresh device/panda/manager
samples retained started=false, ignition=false/false, normal OFF roles and no
ticket/writer. The telemetry window covered the process timer. The owned observer
exited naturally and was reaped; no cleanup signal or operating restart was used.

The process instrument nevertheless retained **zero generations**. Its baseline
and240 fast records all failed scope acquisition with untagged ENOENT before PID
enumeration. Empty lists therefore mean failed observation, not absent processes.
The median0.250006588s/max0.256501903s loop intervals are **empty-loop timing**.
They are not accepted as process-sampler performance. There are no positive-read,
birth, exit, ancestry, nmcli or complete critical-identity witnesses from this
window. The instrument's scope-unknown status and the overall failed collection
were preserved without a retry.

## Missing capability and offline correction

One subsequent bounded read of five fixed system paths found
`/proc/self/ns/pid` unavailable with FileNotFoundError/ENOENT2. Mount namespace,
mountinfo, boot ID and the real /proc directory were readable; mountinfo described
one whole proc mount with no hidepid option. The frozen scope routine reads the
PID namespace first. This supports the observed failure path, while the original
window itself had no field-specific error tag. No kernel build configuration is
inferred. This capability probe was not another sampling window.

The sampler made a platform assumption that prevented useful collection. The
development correction now retains PID enumeration independently from scope
failure, tags the failing field, retains failed-baseline evidence and stops before
the fast window when required capabilities are unavailable. Timer cadence and
valid process coverage are separate; both must pass. Missing namespace evidence
still fails closed. This corrected instrument was tested offline and **was not
redispatched to the device**. The actual source/receipt commitments describe the
earlier instrument, not the corrected development revision.

The reusable diagnostic also retains explicit PID-list absence/reuse and direct
exit probes, conservative lifetime censoring, per-read brackets and PPID, PID/start
generation identity, measured head/work/tail gaps, and owned fork/pipe cleanup.
It has no helper allowlist or deployment policy. Metadata caching cannot prove
that executable/credentials never changed between samples. Its cooperative child
deadline requires bounded callbacks and periodic health checks; it is not a
preemptive timeout for arbitrary code.

## Verification and remaining gate

Fresh authoritative prior cases:1165+148=1313 PASS. Final sampler cases:61 PASS,
including seven regression cases added after the failed device attempt. Unique
total1374/0FAIL/0SKIP, with disjoint case IDs. Earlier54/60-case runs are not added
again. The1313 cases exercise unchanged existing inputs; the corrected sampler's
61-case run covers the new tool. Source reviews and receipt checks are additional
evidence checks, not extra regression cases.

Diagnostics4 remain dependency-blocked by missing zstandard and are uncounted.
Root collection was not executed because its static audit finds top-level live
fetch/exit behavior. Native FFmpeg remains unavailable. No dependency was installed.
The regression audit preserved8,341 prior evidence files. Source and evidence
reviews were independent; the failed main receipt and later capability receipt
remain private and separately committed by SHA256 in the public artifact.

The historical nmcli attribution remains INSUFFICIENT_EVIDENCE. Current helper
safety, full critical identity and full Params/service/USB effect absence remain
UNKNOWN. PhaseB policy acceptance, redeployment and Vehicle10 remain NOT_RUN.
Parity remains UNDETERMINED; M2=NO.

Next: review an equivalent scope attestation for this missing PID-namespace
interface. Do not relax preservation gates, automatically repeat sampling,
reinstall the recorder or arm a ticket from this result.

Result commit: `git log -1 --format=%H -- artifacts/m19c15c_lightweight_process_diagnosis_20261026.json`
