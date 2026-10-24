# M19-C2.1 — exact5bb private capture storage preparation

**PASS_STORAGE_READY.** `/data/v3_input_capture` was created as an empty private
0700 directory owned by UID/GID1000:1000 on the internal ext4 `/data` filesystem.
The exclusive32-byte fixed-payload write/read/fsync probe passed, and only that
probe was removed. No ticket, capture child, writer, activation or dataset was
created. Recorder source remains RECORDER_5BB_DEFERRED_NAV_V1_INSTALLED_OFF.

Actual branch: carrot-nav. HEAD: `5bbbe160822c7cae4245d7a8e96b40d158941ff7`.
Fresh OFF/ON:1/0. Six installed hashes and33 normalized source pins passed before,
immediately before creation, after the probe and in a separate final read-only
guard. N16 model/spec, five server-owned state pairs, image(2,6,128,256),
packed65595 and first12=8/2/2 remain exact. One reviewed footer remains installed.

## Scope and fresh gates

Development started at `ecd556cd2c7cc20b323aed3b298eb80ed8a3ebcc`, exact
feature/jetlink-multimodel-carrot, CLEAN/local=upstream=remote. Continuation,
C14 deployment report/artifact and C04 review report/artifact were read first.
Historical evidence is unchanged. Only this report, its artifact and a new
continuation checkpoint are changed in development.

The first actual reads were cat IsOffroad then cat IsOnroad, returning1/0,
immediately followed by branch/HEAD reads. A local terminal parser initially
mistook an echoed queued command for branch output. The retained raw executed
prompt shows carrot-nav/exact5bb; a prompt-bound parser correction retained a
new accepted receipt referencing the original SHA. No device drift or mutation
occurred during that correction. Fresh subsequent source gates independently
confirmed exact identity. No historical OFF observation was reused.

Ticket namespace was absent, with no arm.ticket, consumed marker or capture
claim. Writer/memfd/legacy activation counts were0; normal OFF roles were present
and onroad-only modeld/camerad/card/controlsd/selfdrived absent. Source and index
were read only, with optional Git locks suppressed. No pull/reset/checkout/
rebase, updater control, Params write, restart or Jetson connection was used.

## Filesystem, ownership and uploader separation

Fresh mountinfo/fstab/sysfs identify `/data` as ext4 on the internal UFS userdata
partition, mount root `/`, removable=0; writable by UID1000. It is not tmpfs,
network/removable storage or an overlay/bind redirection. `/` and `/data` are
real directories with exact canonical paths; the authorized child was absent.
No nested mount redirects the capture root. `/data` itself is outside a Git
working tree; the operating checkout is the separate `/data/openpilot` tree.

Live manager UID/GID values are1000:1000. The exact process configuration launches
modeld as PythonProcess(only_onroad); its normal launcher inherits manager
credentials. The installed recorder writer uses Popen without user/group
overrides. Therefore owner1000:1000 and mode0700 allow future modeld/writer
child creation without privilege escalation. No chown or arbitrary identity
was used. Modeld was not started to establish this proof.

Source/config and selected live environments establish log_root as
`/data/media/0/realdata`, with no LOG_ROOT override in the seven inspected
manager/transfer-related processes. Uploader enumeration uses that root;
athena uses log_root/swaglog_root; boot/crash paths stay under existing logs.
Carrot dashcam root is realdata, tmux uploads use named log/settings files and
cweb_push does not scan capture directories. No observed source integration,
user crontab or active sync process discovers the new root. Current service/
cron/source evidence is private. This concerns automatic discovery at this
stage; it does not promise protection against a future explicit user upload.

Canonical paths/mounts establish separation from route/qlog/rlog/boot/crash,
swaglog/stats, model storage, Carrot state/cache and Git trees. The new root
was not added to uploader configuration, Git, cloud sync or a route directory.
Fresh checks also bind21 ownership/uploader boundary sources, with overlap
with the33 recorder pins. No uploader source function was executed.

## Creation, probe and output-path dry verification

After every precondition passed, a held no-follow `/data` directory descriptor
was verified against the fresh parent device/inode. Immediately before mkdir,
OFF, HEAD, six hashes,33 pins, index, ticket/writer, owner, mount and free-space
gates were repeated. One relative mkdir created only v3_input_capture with0700.
The new root was opened no-follow and its owner/type/mode/canonical path and
zero children verified immediately. Permission adjustment was restricted to
that newly created directory if needed. Parent-directory fsync passed.

One random hidden regular probe was created under the held root descriptor
using O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC and private permissions.
It wrote32 non-sensitive fixed bytes, fsynced, reopened no-follow and verified
the exact inode and bytes. Cleanup rechecked the identity of the created inode
before unlinking that exact probe, then fsynced the root. No other path was
deleted, and the root again had zero children. No root cleanup/rollback or
automatic retry is implemented after an uncertain operation.

Only the installed hook's two pure functions `_no_symlinks` and `_output_paths`
were evaluated with a synthetic32-hex future ID. Existing absolute root,
canonical/no-symlink path, exact parent, absent child and realdata exclusion
passed. The hook package was not imported. No ticket/arming helper was called,
no JSON ticket was constructed and no future child or ID claim was created.

## Final evidence

| Field | Result |
| --- | --- |
| Root | /data/v3_input_capture |
| Created / type | YES / DIRECTORY |
| Canonical / symlink | PASS / NO |
| Owner / mode | UID1000:GID1000 / 0700 |
| Empty / writable / exclusive probe / fsync | PASS / PASS / PASS / PASS |
| Filesystem / mount | ext4 / /data (internal UFS) |
| Total bytes | 94524579840 |
| Available bytes | 28407676928 |
| Available MiB | 27091.671875 |
| Available percent | 30.053217 |
| Minimum available bytes | 104857600 (PASS) |
| Route / Git overlap / uploader integration | NO / NO / NO |
| HEAD / six hashes /33 pins / index stable | PASS / PASS / PASS / PASS |
| Ticket / consumed marker / claims | ABSENT / ABSENT /0 |
| Activation / writer / frames / dataset | NOT_RUN /0 /0 / NONE |
| Updater drift | NONE |
| Actual mutations | STORAGE_ROOT_ONLY (probe removed) |
| Restart / reboot / Jetson access | NOT_RUN / NOT_RUN / NO |
| Jetson mutation | NONE |

A separate final read-only guard passed with the same root inode/mode/owner,
empty contents, exact source/profile/index and absent capture state. Core role
identities and boot identity remained stable across the retained PRE/POST/final
observations. These are bounded observations, not a continuous whole-device or
unrelated Params-content snapshot. Private process/route details, device address
and randomized probe names are omitted from public evidence.

Local POSIX checks:4PASS/0FAIL, covering exclusive probe/fsync/removal, existing
regular-file collision preservation, symlink collision preservation and own-probe
cleanup on injected write failure. They use synthetic temporary storage only.
The actual comma probe passed separately once. No public recorder/tool code was
changed, so the historical C14 1165-case regression was not rerun or recounted.

Final state: **RECORDER_5BB_DEFERRED_NAV_V1_INSTALLED_OFF +
PRIVATE_CAPTURE_STORAGE_READY**. Ready for Vehicle10:
**YES_READINESS_ONLY**. No capture authority is implied by storage preparation.
PARITY_UNDETERMINED; M2NO.

Next action: M19-C2 under separate capture authorization, starting with fresh
OFF/source/profile revalidation before any one-shot ticket.

Full sanitized per-file/pin rows and private evidence commitments are in
artifacts/m19c21_5bb_private_capture_storage_20261024.json. Result commit:
git log -1 --format=%H -- artifacts/m19c21_5bb_private_capture_storage_20261024.json
