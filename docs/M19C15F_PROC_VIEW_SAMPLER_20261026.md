# M19-C1.5F — ProcView sampler/stream integration · 2026-10-26

**PASS_OFFLINE_DIAGNOSTIC_INTEGRATION_WITH_LIMITS. No actual device action.**

Started 2026-10-26; completed 2026-10-27 Asia/Seoul. Stage filenames retain the
start date.

Implemented an opt-in diagnostic path from FD-relative ProcView through a private
journal, sampler provider, optional owned observer, cleanup, strict replay and
closed public summary. The strict ProcReader/default, old prepare/collect,
recorder patches/source pins and actual dispatcher remain unchanged. Actual
source/OFF/runtime state was not freshly observed. No deployment, ticket, capture,
restart, Params/service/USB/updater configuration or Jetson action occurred.

## What changed and why

ProcView has an optional fixed sink installed before acquisition. It records
constructor/close lifecycle, its closed semantic API results/failures and the
instrumented low-level attempts. This is complete instrumented semantic coverage,
not every kernel syscall. The old bounded512 tail remains explicitly incomplete
after eviction. Sink failure/reentrancy poisons further use and preserves primary
errors while cleanup continues.

`PrivateJournal` uses exclusive no-follow0600 creation under a held private parent,
canonical JSONL, a sequence/hash chain, finite byte/event/line budgets and reserved
terminal space. Bytes and literal reserved dictionaries have distinct encodings.
Short writes are completed; overflow/IO/fsync/close failures cannot return a
trusted seal. Replay requires an external trusted final digest/count, exact EOF,
canonical values and complete lifecycle/call pairing. Hash consistency alone does
not authenticate a producer or prove omission-free operating visibility.
[Write semantics](https://man7.org/linux/man-pages/man2/write.2.html).

`ProcViewReader` reuses GenerationTracker for positive records only. NOT_FOUND is
unadmitted UNREADABLE; scan completeness/visibility support always remain false.
Metadata verifies the requested PID/start generation. The unchanged old prepare
still refuses this provider. The separate collector records timing/overrun,
scope drift and partial failures; native interval remains .25–.5s. Shorter test
intervals require an injected backend. No BOUNDED lifetime or policy acceptance.

Replay binds each top-level scope/scan/probe/available-metadata fact to a consumed
matching semantic call result in the same session. Capability success needs a
matching successful baseline scope; a ready constructor is insufficient. Window
counts and timing reconcile with bound observations. Failed runs retain observed
partial counts and mark timing unknown. Public output is rebuilt from a fixed
allowlist, retaining fixture/native provenance and forcing authority flags false.
No PID, argv, namespace link, private path, nonce or arbitrary error text is public.
Call sequence and begin/result clocks also bind each fact to its current scan
phase. A cached pre-list probe, pre-scan enumeration or pre-completion final scope
cannot be promoted into fresh evidence.

The observer protocol uses an inherited anonymous pipe, fresh challenge, mapped
identity, parent ACK, ready/result framing and EOF. Child ProcView semantic events
relay into the sole parent writer after inherited descriptors are closed. Early
result/error, duplicate/invalid frames, ownership loss or cleanup failure rejects.
Signals target only the unreaped fork-return direct child, never a supplied PID.
Callback checks are cooperative; a blocked callback/kernel syscall is not hard
preempted. Protocol origin under trusted code/FD/wait ownership does not establish
helper safety or namespace/global/temporal visibility.
[Pipe interface](https://man7.org/linux/man-pages/man2/pipe.2.html),
[wait ownership](https://man7.org/linux/man-pages/man2/waitpid.2.html).

`run_diagnostic` defaults to one capability baseline, without a child or fast
window. Full diagnostics are explicit. A killed child can leave an unclosed stream:
the private file/anchor and fixed incomplete-verification receipt survive; strict
replay still rejects it. No closing event is reconstructed to obtain success.

## Validation and preservation

Fresh relevant validation: **290 unique PASS / 0 FAIL / 0 ERROR / 0 SKIP**:
90 new cases (journal32/provider30/observer19/capability9) plus200 existing cases
(acquisition65/model74/strict61). Existing tests are rerun once in that total;
earlier262/272/275/276/281/287 and historical1374 are not added. Environment: existing WSL Linux
x86_64, Python3.12.3, pytest9.1.1. No dependency installation. Root collection's
live-fetch/exit blocker, diagnostics4 dependency blocker and native FFmpeg blocker
remain separate and were not rerun.

Fixtures cover corruption/truncation/budgets/IO/cleanup, >512 operation streaming,
generation reuse, baseline refusal, timing and partial evidence, fake fact
rejection, summary privacy, pipe framing/nonce/ACK/early exit/reaping and child
detachment failure. Controlled observer scope fixtures explicitly inject the
profile that native WSL refuses; they are labeled INJECTED_FIXTURE and are not
actual or native full-scope approval. Local native checks are not comma tests.

Independent static reviewers checked the final source, saved test receipt and
preservation boundaries. Findings were reproduced in RED cases before correction.
All335 frozen prior tracked files excluding the authorized acquisition extension
and continuation prepend, plus13 selected historical private receipts, retain
their original working-byte hashes. Historical failures are not upgraded.

## Actual handoff boundary

The separate count-only `probe_capability` function performs one read-only scope
query and discards raw fields. It creates no journal/file, child, ticket or fast
window. One local native invocation returned **BLOCKED_SCOPE_PROFILE**, with33
semantic events and zero processes/journals/windows/tickets. The WSL submount
restriction was preserved. Actual kernel/libc/statx support remains UNKNOWN;
only local x86_64 was exercised and aarch64 was not.

The source-pinned in-memory capability payload is also prepared: the builder
requires exactly three reviewed modules and verifies their external SHA pins.
Its deterministic loader checks pins before compilation, restores temporary
module aliases/bytecode policy and emits one closed capability summary. Source
drift and pin tamper reject. It was tested only in a local Linux child.

There is no SSH/device dispatcher or target payload installation in this stage.
Any target invocation needs the reviewed whole-payload SHA plus fresh OFF/source
gates and must use `python -B` over stdin from process startup, including standard
library imports. The prepared payload is 66708 bytes, SHA256
`be13b17d4318d4dd0b9c0ff7e9f1e620c49a9690a5143092af44a0b98bf71767`.
It is not an automatic60-second retry. Unsupported
capabilities/profile stop before sampling and do not select a fallback.

FD trust, privileged remount/filter/exec ABA, native-thread behavior, global scope,
critical root metadata, achieved device cadence and helper lifetime/effects remain
separate proof obligations. Actual policy/redeployment/Vehicle10 readiness: NO.
Parity: UNDETERMINED. M2: NO.

Next action: perform at most one source-pinned, in-memory, read-only target
capability check after fresh OFF/source verification. Do not start a target observer/window, recorder or ticket
from this offline result.

Result commit: `git log -1 --format=%H -- artifacts/m19c15f_proc_view_sampler_20261026.json`
