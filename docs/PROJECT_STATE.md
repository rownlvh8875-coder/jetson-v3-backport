# Cinque V3 Jetson — 현재 진행 상태

## 5B-1 후속: 콤마4 기존 접속 이력 복원 (2026-10-11)

사용자 요청에 따라 이전 ChatGPT/Codex 기록과 **기록에서 확인한 경로만** 읽었다.
현재 장치에 접속하거나 시험한 결과가 아니다. 아래 초기 체크포인트의 연결 정보 부족 중
콤마 접속 방법은 이번 이력 확인으로 복원했다. 실제 설치/런타임/상태는 여전히 미확인이다.

- Codex 작업 **「CyberPilot 작업 상태 복원」**, 2026-10-01 13:17:33 UTC:
  실제 SSH 명령 exit 0, 원격 응답에 `aarch64`, `carrot-wip`가 기록돼 있다.
  같은 기록에서 관련 SSH 호출 8개 중 7개 exit 0, 1개 exit 1이었다.
  과거 명령은 재실행하지 않았다. 이 당시 branch/응답은 현재 장치 버전 증거가 아니다.
- 당시 연결은 **WSL Ubuntu의 전용 키**와 명시적 기존 known_hosts,
  `IdentitiesOnly=yes`, `BatchMode=yes`, `StrictHostKeyChecking=yes`를 사용했다.
  계정/주소/개인 경로/키 내용은 공개 문서에 기록하지 않는다.
- 현재 해당 WSL 개인키 파일 존재/권한 0600, 공개키 파일 존재/0644,
  known_hosts 존재/0600을 확인했다. 개인키 내용은 읽지 않았다.
  `ssh-keygen -F`로 과거 대상의 기존 known_hosts 항목 존재를 확인했다(로컬 조회, 접속 아님).
- 공개키를 메모리 안에서 GitHub 공개 등록 키와 비교했고 **동일함**을 확인했다.
  앞선 Windows 공개키만의 비교는 WSL 키를 포함하지 않았으므로 장치 인증 방법 부재의 근거가 아니다.
  키/주소/계정은 출력·게시하지 않았고, 키/host-key/SSH 설정을 변경하지 않았다.
- ChatGPT **「Jetlink 오류 원인 확인」**에는 Jetson 기존 키/이전 주소 관련 안내가 있지만,
  SSD 재설치 뒤 현재 주소·host-key·인증 성공 여부는 확인되지 않았다. 안내를 성공 로그로 간주하지 않는다.
- 사용자에게 **현재도 같은 콤마4인지, 비운행·안전한 점검 상태인지** 확인을 요청했다.
  확인 전 장치 접속은 보류한다. Jetson 현재 대상은 별도 확인이 필요하다.

이번 변경은 이력 복원 요약뿐이다. 원격 SSH/네트워크 스캔/HELLO/ENGINE/infer 요청,
장치 코드·환경·Params·서비스·모델 선택 변경은 없었다.
다음 첫 작업은 현재 대상 동일성/안전 상태 확인 후, 기존 host-key 검증을 유지한 읽기 전용 접속이다.

## 5B-1 읽기 전용 사전점검 체크포인트 (2026-10-11)

**로컬 기준 확인 완료 / 실제 Jetson·comma 점검 BLOCKED — 지정 대상·기존 연결·안전 상태 확인 대기.**
이번 승인은 지정 장치의 기존 연결을 통한 읽기 전용 inventory뿐이다.
설치/적용/build/load/infer/선택/서비스 변경은 승인되지 않았고, 점검 이후 자동 진행하지 않는다.
아래 소프트웨어 인계/ORT 기록은 개발 PC 결과이며 장치 검증으로 승격하지 않는다.

- 실제 origin은 지정 저장소, branch는 `feature/cinque-v3-jetson`.
  시작 로컬/실제 조회 원격 모두 `804daae48c4caeeed568879b5bccae903d6bbad5`, 미커밋 변경 없음.
  제품 테스트 SHA `e1096e60664ff2fd92d364ff9c1af10ce01488d7`와 patch 기준은 유지했다.
- AGENTS/현재 상태/계획/manifest/현재 적용·원복·현장 절차를 읽었다.
  과거 JETSON_SETUP_GUIDE 설치 명령은 실행하지 않았다.
- 기존 인계 기록에는 실제 장치 주소/계정/설치 경로/서비스/설치 SHA가 미확인이다.
  로컬 OpenSSH 실행 파일은 있지만, 승인된 특정 대상과 인증 이용 가능 여부는 확인되지 않았다.
  사용자에게 Jetson/comma 각각의 기존 SSH 별칭 또는 주소·계정·포트/기존 인증 방법과
  운행 중이 아닌 안전한 점검 상태 확인을 요청했다. 비밀번호/개인키 내용은 요청하지 않았다.
  다른 SSH 대상/네트워크/자격증명을 탐색하거나 접속하지 않았다.

### 이번에 실제 확인한 로컬 자료

`git remote get-url origin`, `git branch --show-current`, `git rev-parse HEAD`,
`git status --porcelain=v1`, `git ls-remote origin refs/heads/feature/cinque-v3-jetson`을 실행했다.
Python 표준 라이브러리 `hashlib/json/subprocess`로 manifest의 두 패치 SHA256,
고정 참고 HEAD/clean status(`git --no-optional-locks`), 기준 Git blob hash 및
최종 개발 사본의 19개 적용 후 파일 hash를 비교했다: **PASS / exit 0**.
이는 로컬 자료 점검이며 장치 파일 비교가 아니다. ONNX/engine을 읽거나 실행하지 않았다.

최초 참고 working-tree 바이트 비교는 C `contracts.py`에서 불일치로 **FAIL / exit 1**이었다.
원인은 참고 C checkout의 CRLF였다. 고정 SHA의 Git blob으로 원인을 확인했고,
C 8개 기존 파일은 CRLF만 다르며 baseline Git blob/최종 LF 적용본은 manifest와 일치했다.
파일/설정을 고치지 않았다. 실제 장치의 hash 불일치를 이 사유로 자동 허용하지 않는다.

| 실제 장치 항목 | Jetson | comma |
|---|---|---|
| 설치 코드 HEAD/branch/변경/실제 실행 소스 | 미확인 | 미확인 |
| manifest 파일 전·후 일치/다름/없음 | 위치 미확인, 9개 모두 비교 미실행 | 위치 미확인, 10개 모두 비교 미실행 |
| OS/L4T/JetPack/CUDA/TRT/서비스 Python | 미확인 | 해당 장치 OS/실행환경 미확인 |
| 서비스/프로세스/작업 디렉터리 | 미확인 | jetlinkd/modeld 시작 방식 포함 미확인 |
| 모델/cache/metadata 존재·크기·mount/overlay | 미확인 | 미확인 |
| V3 선택/실제 active/fallback/정보 신선도 | 미확인 | 두 프로세스 opt-in과 상태 파일 미확인 |
| V2 보존·원복 자료/격리 공간/권한 | 미확인 | 미확인 |
| 적용 가능성 판정 | **정보 부족 — 적용 보류** | **정보 부족 — 적용 보류** |

### 연결 정보 확인 후 이 승인 안에서 수행할 순서

1. 안전 상태를 확인하고 기존 host-key 검증/인증을 그대로 사용한다. 미등록/변경된 host-key,
   인증/권한 실패는 기록하고 우회하지 않는다. 장치에 점검 파일/로그를 쓰지 않는다.
2. 프로세스/서비스의 실행 파일·소스·cwd부터 찾고 해당 설치본만 비교한다.
   Git이 있으면 `GIT_OPTIONAL_LOCKS=0`으로 HEAD/branch/status를 읽는다.
   Git이 없으면 설치 metadata와 manifest 대상 실제 파일 hash로 기록하며 SHA를 추정하지 않는다.
3. 기존 OS/L4T/패키지 metadata·proc/sysfs/mount 정보를 읽는다.
   CUDA/TRT/ONNX runtime을 import하거나 엔진을 deserialize하지 않는다.
   service Python은 실제 프로세스 실행 파일/시작 정의로 확인한다. 전체 cmdline/env/고유번호는 공개하지 않는다.
4. 모델/엔진은 알려진 실제 cache 경로에서 존재·크기·기존 JSON만 확인한다.
   상태 파일은 설치 코드에서 경로·읽기 부작용부터 확인하고 선택/active/fallback/갱신 시각만 읽는다.
   `/proc/<pid>/environ`을 읽을 수 있으면 `CARROT_JETLINK_V3` 키만 추출하며 전체 환경을 출력하지 않는다.
   HELLO/ENGINE/status client 등 build/load를 유발할 수 있는 진입점은 실행하지 않는다.
5. V2 복구 자료·격리 폴더 후보의 mount/공간/권한·기존 서비스 관리 방식·GPU/메모리 충돌 조건을
   읽기 전용으로 확인한다. 설치 차이가 있으면 먼저 개발 PC에서 차이 검토/재검증을 계획한다.
   실제 변경 파일/경로·원복·시험 실행·활성화는 별도 승인 목록으로만 남긴다.

수치 합격 기준은 여전히 미확정이며 기존 ORT 측정 exit 3을 유지한다.
마지막 완료는 로컬 기준/manifest 확인, 다음 첫 작업은 요청한 대상·인증 방법·안전 상태 확인이다.
실제 장치 접속/명령/운영 코드·설정·서비스·Params·모델 선택 변경은 **없음**.
제품 코드/패치/manifest/main/참고 저장소도 변경하지 않았다.

## 최종 소프트웨어 인계 — 4A/4B/4C/5A (2026-10-11)

**4A 협상, 4B 선택/준비, 4C CPU·loopback 통합, 5A 적용/원복, 최종 검토·수정·재시험을 완료했다.**
결과물은 실기 미검증 **experimental**이다. 5B 실제 Jetson/comma/TRT/USB/차량 검증은
**BLOCKED / 별도 현장 승인 대기**이며 장치 탐색·접속·설치·활성화는 수행하지 않았다.
아래 체크포인트와 1–3단계 절은 당시 기록이다. 현재 결과와 적용물은 이 절과
[현재 계획](V3_JETSON_PLAN.md), manifest를 따른다.

- 저장소/브랜치: `rownlvh8875-coder/jetson-v3-backport`, `feature/cinque-v3-jetson`.
  시작 로컬/실제 원격 SHA `5fda3e8b6db8b6b7f4c1c50cdb732dc32aed93ce`, 미커밋 변경 없음.
- 최종 제품·집중 테스트 SHA: **`e1096e60664ff2fd92d364ff9c1af10ce01488d7`**.
  이후 변경은 인계 문서뿐이다. 최종 문서 포함/확인한 원격 SHA는 게시 후 응답에서 보고한다.
- 깨끗한 고정 기준 J `d0dc96fa32410403dfb2fefff3e2909c11ec109b`,
  C `029ab60eb19e7b9d4d76bfee1ce99a7521934511`는 변경하지 않았다.
  최종 적용 검사 사본은 `../development/carrot-jetson-v3-final`,
  `../development/openpilot-v3-clean`이며 실제 import `__file__`을 검사했다.
- 최종 패치는 `patches/jetson-production-v3.patch`와 `patches/comma-integration-v3.patch`.
  `patches/experimental-v3-manifest.json`의 기준/패치/19개 파일 전후 SHA256와 MIT 라이선스를
  대조한다. 과거 부분 패치와 중복 적용하지 않는다. 원본 ONNX/엔진/개인 경로/원본 로그는 패키지에 없다.

### 구현과 검토 결과

실제 경로는 `mac.prepare → Client HELLO/approve_v3/ensure_engine → Session ENGINE →
EngineHost worker/build/load/_warm → daemon Unix IPC → link.Client → JoiningModel.run →
infer_begin/end → Session._infer/state commit → driving-only response → parse_outputs`다.
서버 원본 가공/build/load/state 구현은 3단계 것을 재사용했다.

- V2 기본값을 보존했다. `CARROT_JETLINK_V3=1`을 읽는 jetlinkd/modeld만 정확한 V3를 선택한다.
  현재 HELLO의 capability v1·전체 semantic 명세·identity·session_id와 ENGINE ready/generation까지
  일치해야 protocol2 V3를 허용한다. 일반 stateful protocol2 거부와 protocol3 App 경로는 유지한다.
- V3는 서버에 사전 준비된 원본/엔진만 요청한다. V2 URL로 대체하지 않는다.
  최초/미상주 준비는 ignition-off, 기존 승인+현재 resident 재연결만 `ready_only=true`로 허용한다.
  ready-only는 worker를 시작하지 않는다. setup 요청 send/recv도 ignition/cancel을 다시 검사한다.
- wire uint8/packed scalars와 engine FP16 state를 분리했다. V3 prev_feat와 next_state wire 전송은 없다.
  실패 header는 payload를 기다리지 않는다. 새 HELLO/모델/generation에서 이전 승인/응답을 폐기한다.
  commit 실패로 invalid된 state는 reload·새 승인 전 정상 재진입을 막는다.
  selected/실제 active/fallback 표시를 분리하고 기존 parser/reset/FAULT/복귀 함수를 사용한다.
- 별도 읽기 전용 reviewer가 찾은 새 V2 wire dtype 회귀와 ignition/준비 race를 실패 재현 후 수정했다.
  자체 최종 리뷰/기존 회귀에서 찾은 legacy sequence/HELLO spec 회귀도 수정했다.
  모의 검증기의 암묵적인 ORT 설치 의존성은 해당 mock 범위 안에서만 제거했다.
  실제 ORT 부재 실패 검사는 유지했다. 최종 재시험에서 확인한 미해결 소프트웨어 결함은 없다.
  실제 commIssue 메시지 전달·QCOM warp·하드웨어 fallback 추론은 검증하지 못했다.

### 실제 실행·환경·결과

Windows 격리 `$Py=../.venv-v3/Scripts/python.exe`: Python 3.12.14, NumPy 2.5.4,
ONNX 1.23.2, ORT 1.31.0, pytest 9.1.1. WSL **Ubuntu-24.04**의 기존 `$WSL_VENV/bin/python`:
Python 3.12.3, NumPy 2.5.4, ONNX 1.23.2, pytest 9.1.1, ORT 없음.
양쪽 모두 실제 TensorRT/CUDA 검사는 수행하지 않았다. 시스템 환경은 변경하지 않았다.
다음 명령은 작업 저장소에서 실행했다. `$J/$C`는 위 최종 적용 사본,
Linux에서는 같은 사본의 WSL 경로다. 개인 절대경로를 대신한 변수는 실제 경로 확인 후 지정한다.

```powershell
$env:CINQUE_PRODUCTION_ROOT = $J
$env:CINQUE_COMMA_ROOT = $C
& $Py -m pytest -s -q tests/test_production_v3.py tests/test_v3_build_verify.py tests/test_v3_negotiation.py tests/test_comma_selection_v3.py tests/test_experimental_patch.py
& $Py tests/test_stateful_safety.py
& $Py tests/test_backport.py
# WSL: env CINQUE_PRODUCTION_ROOT="$J" CINQUE_COMMA_ROOT="$C" "$WSL_VENV/bin/python" -m pytest -s -q <동일 5개 파일> tests/test_v3_loopback.py
# 고정 C upstream: PYTHONPATH="$C" "$WSL_VENV/bin/python" -m pytest --noconftest -o addopts= -p no:cacheprovider -q <아래 8개 파일>
```

upstream 대상: `$C/openpilot/selfdrive/modeld/tests/test_{jetlink,jetlink_mac}.py`와
`$C/tools/jetlink/test_{stateful_protocol,cache_persistence,app_models,protocol_compat,protocol_choice,v3}.py`.
위 brace 표기는 파일 목록 설명이며 실제 호출은 8개 파일을 각각 인자로 지정했다.

| 실행/근거 로그 | 실제 결과 / 종료 코드 | 대상과 한계 |
|---|---|---|
| `phase4-final-windows.log` | **PASS 169 / 0** | 최종 제품 SHA, 적용된 실제 C/J 모듈, CPU/mock/작은 ONNX |
| `phase4-final-linux.log` | **PASS 198 / 0** | 최종 제품 SHA, 위 검사+localhost TCP/Unix IPC 29; seed 73, 변화 영상/nonzero state |
| `phase4-final-upstream.log` | **PASS 199, SKIP 1 / 0** | 최종 적용 C의 기존 V2/App/protocol3/cache 회귀 |
| `phase4-final-safety.log` | **PASS 46 / 0** | `f11185ad78d909c4384142b04b9903848c2034dd`; CPU+실제 V3 ONNX/ORT, 해당 코드 최종까지 동일 |
| `phase4-final-backport.log` | **PASS 38 / 0** | 위 f11185 SHA; V2/원본 I/O/기존 pointer 검사, 해당 코드 최종까지 동일 |
| `phase4-final-roundtrip.log` | **PASS / 0** | 최종 J/C 패치 reverse→원본 파일 hash·clean status→preflight→재적용 |
| `phase4-post-reapply.log` | **PASS 47 / 0** | 재적용 후 negotiation/selection, 최종 제품 SHA |

Windows/WSL의 중복 검사를 고유 테스트 개수로 합산하지 않는다.
upstream SKIP은 선택적 `REFERENCE_ROOT`가 필요한 protocol3 reference session 한 검사다.
별도 최신 참조 fork를 가져오지 않았다. 나머지 protocol3 golden vectors/App 검사는 실행했다.
3개 warning은 선택적 pytest plugin config 누락이며 제품 검사를 성공으로 바꾼 것은 아니다.
CI workflow가 없어 결과는 로컬 검사다. 초기 RED 및 수정 후 GREEN 로그는 Git 밖 evidence에 보존했다.
최종 repo와 적용 C/J 모듈의 `python -m compileall -q` 및 `git diff --check`도 PASS(exit 0)다.
게시 대상 변경 파일의 크기·개인 절대경로 검사를 통과했고 모델/엔진/원본 로그는 추적하지 않는다.

실제 client/prepare/daemon/Session/worker/warm/infer/큐/parser/JoiningModel.run을 실행했다.
fake 경계는 CPU engine·합성 plan/산술 state·일반 host buffer·camera/internal model/compiled runtime이다.
CUDA graph/pinned allocation/USB/차량 메시지·주행 품질 검증을 뜻하지 않는다.
잘못된 capability/spec/generation, 짧은 실패 header/잘린·초과 payload, NaN/Inf,
다른 frame/지연/중복/이전 연결 응답, disconnect/cancel/invalid state/reload 및 실제 내부 복귀/FAULT를 검사했다.

### 개인정보 없는 증거 식별

원본 로그는 Git 밖 `../evidence/`에만 있다. 재현에는 위 명령·고정 SHA·manifest·seed를 사용한다.
동적 token/시각/경로 때문에 재실행 로그 hash가 같을 필요는 없다. 아래는 이번 실행의 SHA256이다.

| 로그 이름 | SHA256 |
|---|---|
| `phase4-final-windows.log` | `b4de6d7da7e77eb6a733c8ff9dfcdfe7978917611c3a8cb1bc483a90f7cf7fcd` |
| `phase4-final-linux.log` | `4e33efe2bf9e2c019bcac1fff83a0678519add927816947e6a7096e23709b484` |
| `phase4-final-upstream.log` | `5e4863813089335853d6f4c0d6bff3fe786af83b07caaa1905a191d7e40a28b8` |
| `phase4-final-safety.log` | `0079dbe205ed591cd4661b86195e3fbcef06faba54b637a29e740f4fa336c5c8` |
| `phase4-final-backport.log` | `a42cf10d8fc5f725768d7107b3084b09de0d0ca34e2643e4b5d2b99c9d525e67` |
| `phase4-final-roundtrip.log` | `9e95f9737d9279ca3e6fff7e7b676b3c4b4ac9ee9c02e128710f13d87974eff4` |
| `phase4-post-reapply.log` | `c9a8a948540d21574563dc4f4a24c7a65f1cb48bef6f898787016c8aafb833cc` |

### 원본/실장치와 마지막 체크포인트

- 원본 `artifacts/big_driving_supercombo_v3.onnx` 재사용, 전체 SHA256 재확인:
  `404a18cfd86d29637d20c697dfde245bb47c666ae016730ab674c65f4d1e1aa4`, **766354845 bytes**.
  semantic JSON/실제 I/O 대조는 2·3단계 확인을 보존했다. 원본과 dtype 명세를 변경하지 않았다.
- `jetlink/cinque_v3.py` Git blob은 3단계 테스트 SHA와 현재 모두
  `bc60a0ddd24b50f86c45cf9936dbac5dcf45e398`: production graph 가공 변경 없음.
  따라서 대형 원본↔production patched ORT 비교는 재실행하지 않았다.
  기존 recurrent/same-state 각5프레임 오차0은 측정 기록/허용오차 판정 보류 **exit 3**다.
  same-state는 매 step zero state였으며 실제 TRT 합격이 아니다.
- 5B는 **BLOCKED**: 실제 설치 SHA/런타임, TRT build/load/infer/state/CUDA graph,
  USB/comma 전체 경로 성능·내부 복귀·commIssue·온도/메모리 미확인. 주행 검증은 범위 밖이다.
- 마지막 완료: 최종 깨끗한 적용본 회귀→양쪽 원복/원본 hash 일치→재적용→47개 재검사.
  진행 중 제품 변경 없음. 문서 인계 커밋·일반 push/원격 확인 후 종료한다.
- 다음 첫 작업: **현장 승인 후 읽기 전용 장치 inventory로 실제 설치 SHA/런타임을 고정 기준과 비교**.
  대상·변경 목록·V2 원복·제어 경로 격리 조건 승인 전에는 장치에 적용하지 않는다.

아래 과거 기록의 개인 절대경로는 `$WORKSPACE/$WSL_VENV/$BUNDLED_PYTHON` 등으로 비식별화했다.
당시 측정 수치/판정은 변경하지 않았다.

## 4C/5A·리뷰 체크포인트 (2026-10-11)

- 마지막 완료: 별도 C/J 프로세스의 실제 client/Session/worker/warm/infer/TCP와
  mac.prepare→daemon._serve_local→Unix IPC Client→parser/JoiningModel.run 복귀 검사.
  Linux loopback **29 PASS**. GPU/CUDA/USB/QCOM warp/내부 추론 연산만 합성 경계다.
- 실제 읽기 전용 별도 리뷰에서 V2 새 명세의 dtype 필드 회귀와 stale-preloaded/ignition
  준비 race를 발견했다. V2 queued wire는 기존 필드를 보존하고, V3 onroad 요청은
  `ready_only=true`로 현재 resident/valid engine만 받는다. offroad 요청도 send마다
  ignition/cancel을 확인한다. 각각 RED→GREEN 테스트로 고정했다.
- 실행: production+negotiation **97 PASS**, selection **22 PASS**;
  기존 C Linux 회귀/App **122 PASS**. 최종 깨끗한 패치 적용본에서 재검사 중이다.
- 5A: `patches/experimental-v3-manifest.json`에 기준 SHA·19개 파일 전후 hash·패치 hash·
  설정/라이선스를 기록했다. `tools/experimental_patch.py`는 개발 사본만 검사/적용/원복하며
  잘못된 SHA/dirty/내용 변조/이미 적용됨을 거부한다. fixture **6 PASS**,
  실제 두 고정 사본 preflight/apply/reverse/재적용 확인 중이다.
- 막힌 항목: 5B 현장 승인/장치, 실제 TRT/USB/QCOM/차량 메시지·commIssue 실측.
  실제 ONNX 가공 구현은 변경하지 않았고 기존 ORT 측정(exit 3) 한계를 유지한다.
- 다음 첫 작업: 최종 제품 커밋 기준으로 깨끗한 적용본 검사·원복·재적용을 마치고,
  개인정보 없는 증거 요약·현장 절차를 갱신해 지정 feature 브랜치에 게시한다.

## 4A/4B 체크포인트 (2026-10-11)

- 시작 로컬/실제 원격 HEAD `5fda3e8b6db8b6b7f4c1c50cdb732dc32aed93ce`, 지정 branch, 변경 없음.
- 4A 구현: 정확한 semantic JSON/dtype 보존, HELLO capability/version/spec digest/session token,
  ENGINE identity/ready/generation, 새 HELLO 승인·pending 폐기. 일반 stateful protocol2 차단 유지.
- 4B 구현: `CARROT_JETLINK_V3=1` 선택, 기본 V2, 서버 사전 준비 모델만 요청,
  offroad 승인/취소 및 IPC spec 검증, 기존 parser/prev_feat/fallback 재사용.
- 실행: `python -m pytest -q tests/test_v3_negotiation.py tests/test_comma_selection_v3.py`
  **39 PASS / exit 0**, 적용 C/J 모듈 CPU 계약 검사, 로그 `phase4-negotiation-selection.log` (Git 밖).
  `test_v3_negotiation.py + test_production_v3.py`: **94 PASS / exit 0**.
  새 기능 부재(import/API/서버 generation) 실패를 먼저 재현했다. 작은 fixture는 실제 모델 추론이 아니다.
- 진행 중: 실제 C/J 별도 프로세스 Linux loopback·기존 회귀, 최종 패치 적용/원복과 인계.
- 막힌 항목: GPU/USB/QCOM/실제 장치(5B). 기존 graph 가공은 변경하지 않았다.
- 다음 첫 작업: loopback 장애·연속 state 및 기존 App/V2 회귀를 확인하고 5A로 계속한다.

아래 1–3단계 결과는 당시 기록이다. 현재 작업은 승인된 4A→최종 인계까지 계속한다.

## 3단계 결과 (2026-10-11, 현재 기준)

**production 서버 소프트웨어 경로를 고정 소스의 개발 사본에 연결했고 오프라인 검사를 마쳤다.**
실제 TensorRT/Jetson build/load/infer와 comma 연결 성공을 뜻하지 않는다.
comma protocol/모델 선택·운영 설치·서비스·Params는 수정하지 않았다.
아래 1·2단계 절은 당시 기록이며 이 절이 현재 상태다.

| 항목 | 결과 |
|---|---|
| 시작 origin/branch | `https://github.com/rownlvh8875-coder/jetson-v3-backport`, `feature/cinque-v3-jetson` |
| 시작 로컬/원격 HEAD | `a1db7e3ab5270d9834af7171eef10a61bf6daaac`, 일치, 미커밋 변경 없음 |
| 고정 carrot-jetson | `d0dc96fa32410403dfb2fefff3e2909c11ec109b`; 기준 사본 변경 없음 |
| 고정 carrot-wip | `029ab60eb19e7b9d4d76bfee1ce99a7521934511`; 기준 사본 변경 없음 |
| 제품 코드·테스트 SHA | **`a96a792bc042cd893dcdb3eeb5d56336cf98ce52`** (이후 문서/AGENTS/README만 수정) |
| 공통 가공 코드 커밋 | `c653eef0fed8e59816834a7373a64203c7d562fe` |
| production 소프트웨어 연결 | **PASS (소스/오프라인)** — patch/build/metadata/cache/load/warm/infer/state 연결 |
| CPU/mock 통합·회귀 | **PASS** — Windows production 74 + build_verify 41, safety 46, backport 38; WSL production 74 |
| 실제 원본·가공본 ONNX | **PASS (무결성/구조)** — 기존 원본 재사용, 전체 hash/size/I/O/slices/checkpoint 재대조 |
| 실제 원본↔가공본 ORT CPU | **측정 완료·합격 판정 보류** — recurrent/same-state 각 5프레임, 모든 4종 출력 max/mean 0, exit 3 |
| 실제 TensorRT/Jetson build/load/infer | **BLOCKED** — 해당 런타임/장치 환경 미실시; mock으로 대체한 경계임 |
| 실제 comma 연결·성능·state·복귀/알림 | **BLOCKED / 후속 단계** — protocol2 stateful 차단 및 모델 선택 수정도 아직 안 함 |
| 실제 장치 설치 SHA | 미확인; 고정 참고 SHA와 같다고 가정하지 않음 |
| 주행 검증 | 범위 밖, 미실시 |

### 적용물과 실제 호출 경로

현재 작업 저장소 경로는 아래 2단계 절과 같다. 기준 사본 `../references/carrot-jetson`는 읽기 전용으로 보존했고,
개발 사본 `../development/carrot-jetson-v3` 및 최종 재적용 사본 `../development/carrot-jetson-v3-check`를 사용했다.
두 개발 사본 HEAD는 고정 J이며 수정 파일은 이 저장소 패치에 보존했다. 참고 원격에 push하지 않는다.

최종 적용물: [`patches/jetson-production-v3.patch`](../patches/jetson-production-v3.patch),
SHA256 `d59c72bb5e616aceee7797b7b8539a20de0ca44b79b9011dacb91e130e595fe9`.
별도 깨끗한 고정 소스에 **이 파일 하나만** 적용한다. 적용/원복 명령은 [계획](V3_JETSON_PLAN.md#3단계-구현과-개발-사본의-재현-방법)에 있다.

실제 수정 대상은 J `third_party/jetlink/jetlink/` 아래 8개 파일이다:
`cinque_v3.py`(추가), `spec.py`, `queues.py`, `onnx_patch.py`, `server/session.py`,
`server/backends/trt/build.py`, `server/backends/trt/__init__.py`, `server/backends/trt/engine.py`.

호출 흐름은 `EngineHost.request/_run/_build_job → TrtBackend.build → build_engine → patch_file →
parser/build → plan/JSON 게시 → TrtBackend.load → TrtEngine → EngineHost._warm → Session._infer → state commit`이다.
통합 검사에서는 이 함수들을 실제로 실행하고 TensorRT parser/compiler/runtime 및 cudart 경계만 fake로 대체했다.
cache hit와 새 host/backend, **새 Python 프로세스**에서 원본/임시 patched 파일 없이 load하는 검사도 수행했다.

- V3는 고정 SHA/크기·전체 semantic spec·graph 계약 일치 시만 선택한다. 다른 new_img 모델은 거부한다.
- 공통 graph 가공 함수는 개발 도구와 production이 공유하며 내용 일치를 검사한다.
  `jetlink/spec.py/queues.py`, `patches/session.py.new`도 실제 적용 모듈과 동기화했다.
  `session.py.orig`는 고정 J 원본과 일치한다. 개별 spec/queues/session patch도 같은 고정 원본에서 다시 생성했다.
  이 3개는 통합 패치 부분집합이므로 중복 적용하지 않는다. 과거 comma/LFS 패치는 이번에 적용하지 않았다.
- 기존 원본 dtype는 보존한다. `new_img/state_img_q/next_state_img_q`만 FP16 physical 계약으로 선언한다.
  source/patched/engine hash·size, patch ID, semantic spec, 허용 dtype, 기존 TRT/GPU/cache 정보가 영속 JSON에 연결된다.
  기록 checksum은 우발적 손상 탐지이며 서명/인증은 아니다. loader는 임시 절대경로에 의존하지 않는다.
- staging 완료 후 plan/JSON을 게시하고 복구 가능한 두 번째 rename 실패는 기존 plan을 복원한다.
  두 파일의 crash-atomic transaction을 주장하지 않는다. 중단 시 엔진 hash 불일치를 load에서 차단한다.
  metadata 손상과 device/메모리 오류를 구분하고, 후자로 정상 캐시를 삭제하지 않는다.
- 실제 엔진 이름/mode/정확 shape/dtype를 할당 전에 대조한다. pinned buffers/named tensor/CUDA graph,
  memory budget/progress/timing cache를 유지하며 production에 PyCUDA 실행기를 이식하지 않았다.
- `_warm`은 reset→입력→warm/capture→reset, 같은 host buffer 주소를 유지한다.
  capture/실행 실패에서도 stream drain을 시도하고, drain 실패 시 live 메모리를 해제/reset하지 않는다.
- `_infer`는 length/scalar finite 및 원래 outputs/next_state 3종의 이름·shape·dtype·finite 검사 후 commit한다.
  state dtype는 쌍별 동일하며 same_kind 축소를 제거했다. finite float32 70000→FP16 state도 실패 처리한다.
  검증 실패 시 committed state 보존, 명시적 RESET은 별도다. read-only/두 번째·세 번째 copy 실패는
  부분 commit 가능성을 인정하고 generation을 invalid 처리한다. RESET/HELLO만으로 복구하지 않으며 reload 전 정상 응답 금지다.
  기존 실패 Status의 header만 반환한다. 정상 wire에는 driving outputs만 담고 state 3종은 내부에 남긴다.

### 원본과 ORT 실측

- 원본 `artifacts/big_driving_supercombo_v3.onnx`: **766354845 bytes**,
  SHA256 `404a18cfd86d29637d20c697dfde245bb47c666ae016730ab674c65f4d1e1aa4`.
  정상 기존 파일을 재사용했고 다운로드/전체 PC 재탐색을 하지 않았다. 검사 뒤에도 전체 identity 불변.
- production 가공본 `artifacts/v3_phase3_patched.onnx`: **766352746 bytes**,
  SHA256 `38c479b144d1342ce25e6ce7894d9d0bc64c02159b9128ba6cf62282082bf268`.
  이번 production 함수로 새로 생성하여 실제 비교했다. 2단계 결과 문구를 복사한 것이 아니다.
- 원본 7 inputs/4 outputs의 이름·정확 shape/dtype, output_slices 15개, checkpoint가 기존 JSON과 모두 일치.
  slice metadata는 제한된 pickletools 문법으로 해석하며 pickle callable을 실행하지 않는다.
- 실제 import: `../development/carrot-jetson-v3-check/third_party/jetlink/jetlink/onnx_patch.py`.
  원본↔patched ORT CPU는 세션을 순차 실행했다. 등록 provider는 매 세션 `['CPUExecutionProvider']`.
  seed 73, frame 0 zero smoke, 이후 변화 영상·0/255 경계 픽셀·desire 전환.
  recurrent는 각 backend의 next_state를 독립적으로 이어가고, same-state는 **매 step zero state**다.
  두 모드 각 5프레임에서 outputs와 next_state 3종의 max/mean abs error 모두 0.
  허용오차 근거가 없으므로 합격 판정은 **SKIP/보류(exit 3)**다. 도로 품질/TRT 수치·성능 측정이 아니다.
  원본/가공본/engine은 Git에 포함하지 않는다.

### 실제 실행 명령·환경·로그

제품 코드 기준은 위 전체 SHA이며 참고 검사만 고정 C SHA다. 로그는 저장소 밖 `../evidence/`에 보존한다.
Windows `$Py=../.venv-v3/Scripts/python.exe` (실제 Python 3.12.14, NumPy 2.5.4,
ONNX 1.23.2, ORT 1.31.0, pytest 9.1.1), TensorRT/PyCUDA 미설치.
`$Prod=../development/carrot-jetson-v3-check`이며 `CINQUE_PRODUCTION_ROOT`를 절대경로로 지정했다.
WSL Ubuntu-24.04 Python 3.12.3의 격리 venv는 `$WSL_VENV`:
NumPy 2.5.4/ONNX 1.23.2/pytest 9.1.1, 시스템 패키지 업그레이드 없음.

| 실제 명령 (작업 디렉터리=이 저장소) | 결과 / exit | 분류 / 로그 |
|---|---|---|
| `git -C $Prod apply --check <patch>` / `apply <patch>` / `apply --reverse --check <patch>` / `apply --reverse <patch>` 후 재적용 | 모두 0, 원복 시 status 빈 출력, 8개 파일 bytes 일치 | PASS; 고정 깨끗한 사본. `phase3-clean-patch.log` |
| `& $Py -m pytest -s -q tests/test_production_v3.py tests/test_v3_build_verify.py` | **115 passed / 0** (74+41) | PASS CPU/mock + 실제 작은 ONNX 가공. 원본 없는 safety subprocess도 포함. `phase3-final-windows.log` |
| `wsl -d Ubuntu-24.04 -- env CINQUE_PRODUCTION_ROOT=<위 $Prod의 /mnt/c/... 경로> $WSL_VENV/bin/python -m pytest -s -q tests/test_production_v3.py` | **74 passed / 0** | PASS Linux CPU/mock, 실제 적용 모듈 __file__ 기록. `phase3-final-linux.log` |
| `& $Py tests/test_stateful_safety.py` | **46 passed, 0 failed / 0** | PASS; 합성 안전성 + 실제 원본 ORT recurrent/가공 검사. TRT 아님. `phase3-final-safety.log` |
| `& $Py tests/test_backport.py` | **38 passed, 0 failed / 0** | PASS; V2 queued/stateful 합성·실제 V3 I/O 및 기존 pointer 조회. `phase3-final-backport.log` |
| `& $Py ../evidence/phase3_real_onnx.py` | 두 모드 각 5프레임 측정, 전 출력 max/mean 0 / **3** | 실제 production patch + ORT CPU; 합격 판정 SKIP/보류. `phase3-final-real-onnx.log` |
| `wsl -d Ubuntu-24.04 -- $WSL_VENV/bin/python -m pytest --noconftest -o addopts= -q ../references/openpilot/tools/jetlink/test_stateful_protocol.py ../references/openpilot/tools/jetlink/test_cache_persistence.py` | **13 passed / 0**, pytest config warning 3 | PASS; 고정 C의 Linux loopback 통신/캐시 fixture, 실제 comma 아님. `phase3-linux-reference.log` |
| `& $Py -m compileall -q jetlink tools tests ../development/carrot-jetson-v3-check/third_party/jetlink/jetlink` | 0 | PASS 문법만. `phase3-final-compile.log` |
| 실제 TensorRT parser/compiler/CUDA/Jetson 추론 | 미실행 | **BLOCKED** — GPU fake 계약 검사를 실제 실행으로 승격하지 않음 |

실제 모델 비교의 로컬 helper는 적용본 `patch_file(spec=...)`와 기존
`tools/build_trt_v3.py::verify_onnx_pair(...,frames=5,mode=...,seed=73)`를 순서대로 호출한다.
공유 가공 함수를 이용한 재현 CLI는 다음과 같다 (명령마다 exit 3은 허용오차 판정 보류다):

```powershell
& $Py tools/build_trt_v3.py --onnx artifacts/big_driving_supercombo_v3.onnx --spec artifacts/cinque_v3.json --out artifacts/v3_phase3_patched.onnx --onnx-only --frames 5 --comparison-mode recurrent
& $Py tools/build_trt_v3.py --onnx artifacts/big_driving_supercombo_v3.onnx --spec artifacts/cinque_v3.json --out artifacts/v3_phase3_patched.onnx --onnx-only --frames 5 --comparison-mode same-state
```

초기 고정 소스 검사 `phase3-server-red.log`는 1 FAIL/27 ERROR(stateful/dtype 필드 부재)를 재현했다.
후속 red 로그는 metadata 미연결, 잘못된 ready/캐시 처리, 이름 변경 우회와 capture cleanup 누락을 재현하고 수정 뒤 통과했다.
WSL 최초 1건은 테스트 fixture가 런타임 auto 선택에 의존한 문제였으며 명시적 CPU fake backend로 독립화했다.
`/tmp` venv가 후속 WSL 호출에서 없어져 exit 127이 발생한 시도는 사용자 홈의 격리 venv로 재생성 후 위 결과로 재검사했다.
sendmsg/fcntl 삭제나 성공 대체는 하지 않았다. 기존 검사 전체를 pytest 방식으로 재작성하지 않았다.

### 게시와 남은 작업

제품 커밋 2개와 이 절을 포함한 문서 커밋만 `feature/cinque-v3-jetson`에 일반 push한다.
최종 문서 SHA는 `git log -1 --format=%H -- docs/PROJECT_STATE.md`,
게시 상태는 실제 `git ls-remote origin refs/heads/feature/cinque-v3-jetson` 조회로 최종 보고한다.
main 직접 수정/병합, force push, 참고 원격 push는 하지 않는다.

남은 소프트웨어 연결은 [4단계 계획](V3_JETSON_PLAN.md#4단계가-소비할-계약과-첫-작업)의
comma protocol2 stateful 거부·V2 기본 선택 및 server capability 연결이다.
서버는 아직 새 capability를 광고하지 않는다. 이 차단을 이번 단계에서 삭제하지 않았다.
실제 TRT/GPU I/O·pinned/CUDA graph·cache·state 반복/성능 및 전체 comma 경로·복귀/알림은 장치 검증 전까지 미완료다.
다음 단계 지시 전에는 더 진행하지 않는다.

## 2단계 결과 (2026-10-11)

사용자가 1단계 계획을 확인하고 로컬 원본 확보·CPU 검사·빌더/검증기 수정을 승인했다.
실제 comma/Jetson 접속·설치·서비스·Params 변경은 하지 않았다. 서버 stateful 운영 통합과
comma protocol/모델 선택은 후속 단계다. 아래 1단계 기록은 당시의 이력이며 이 절의 상태가 우선한다.

| 항목 | 결과 |
|---|---|
| 시작 브랜치/HEAD | `feature/cinque-v3-jetson` / `09c2ddda4de0111c245b4d45d48023e569ace966`; 로컬/원격 일치, 변경 없음 |
| 기존 제품 기준 | `2519ad0bdbf6e796fa590063fc90d4d6461b6b8d`, 이력 보존, main 변경 없음 |
| 테스트 대상 코드 SHA | `e65ed6a46befba4c9211d9707e9bee63f7f29507` (이후 문서만 수정) |
| A. 코드 수정·CPU 회귀 | **PASS** — 집중 41, 원본 없는 격리 사본의 기존 safety 40 PASS 포함 |
| B. 원본 다운로드·전체 해시·I/O | **PASS** — 지정 파일 본문·7 inputs·4 outputs·slice/checkpoint 전체 일치 |
| C. 원본↔patched ONNX | **측정 완료·합격 판정 보류** — ORT CPU, recurrent/same-state 각 5프레임, 4종 출력 max/mean 오차 0, exit 3 |
| D. 실제 TRT/Jetson 빌드·수치 비교 | **BLOCKED** — 개발 venv에 TensorRT/PyCUDA 없음, 실제 장치 접속·검사 미실시 |
| 실제 comma 연결·속도·state·복귀/알림 | **BLOCKED / 후속 단계** — 현재 연결/선택 코드는 변경하지 않음 |
| 주행 검증 | 범위 밖, 미실시 |

### 원본과 메타데이터

저장소 실제 경로: `$WORKSPACE\jetson-v3-backport`.
origin: `https://github.com/rownlvh8875-coder/jetson-v3-backport`.

- 원본: `artifacts/big_driving_supercombo_v3.onnx` (위 저장소 아래).
  SHA256 `404a18cfd86d29637d20c697dfde245bb47c666ae016730ab674c65f4d1e1aa4`, **766354845 bytes**.
- 기존 [HF 다운로드 주소](https://huggingface.co/commaai/openpilot_driving_models/resolve/main/f78ed37d-afad-4dbc-8050-40ea885eedde/12864/big_driving_supercombo.onnx)에서
  TLS 검증을 유지해 본문을 `.onnx.part`에 저장했다. 시작 시 C: 여유 약 90.6 GiB.
  전체 해시·크기가 일치한 뒤에만 최종 경로로 rename했다. 마지막 검사에서도 전체 해시/크기 불변.
- 가공본: `artifacts/v3_phase2_patched.onnx`, **766352746 bytes**,
  SHA256 `38c479b144d1342ce25e6ce7894d9d0bc64c02159b9128ba6cf62282082bf268`.
  원본을 수정하지 않았다. ONNX/가공본/엔진/다운로드 임시 파일은 Git에서 제외한다.
- 원본 protobuf I/O의 이름 집합·정확 shape·dtype 모두 기존 `artifacts/cinque_v3.json`과 일치.
  자세한 계약은 계획 문서의 표와 그대로 같다. JSON은 변경하지 않았다.
- 원본 `metadata_props.output_slices` 15개와 `model_checkpoint`가 JSON과 일치했다.
  output_slices는 `pickletools` opcode를 제한적으로 해석하며 callable/pickle을 실행하지 않는다.
  원본 metadata에는 frame_skip 필드가 없으므로 기존 `frame_skip=4`를 새 실측값이라고 표시하지 않는다.

### 수정 범위와 남은 소비 지점

- `tests/test_stateful_safety.py`: 실제 ONNX에 의존하던 identity negative 검사를 임시 바이트 파일의
  실제 해시/크기로 변경. 올바른 identity, 잘못된 hash/size, 부재, 각각 main의 build 미호출 검사.
  mock/sys.argv는 context manager로 복원. 바이트 fixture는 모델 구조/추론 검증이 아니다.
- `tools/build_trt_v3.py::build_engine`: 입력은 `num_inputs/get_input`으로 열거.
  retype 기록의 실제 경로 반환. 원본 I/O/dtype와 intentional physical dtype 3개를 분리.
  원본·가공본·engine·patcher 해시, 가공 모드, TRT 버전, workspace/FP16을 연결해 기록한다.
  staging 후 engine을 마지막에 원자적으로 게시. 빌드/게시 실패 시 기존 engine/기록 유지 검사.
  사용되지 않는 실패 시도 sidecar/가공 파일이 남더라도 현재 engine 해시로는 읽히지 않는다.
- `load_build_record`: `<engine.name>.<engine SHA256>.retypes.json`만 읽고 source/engine/patched identity를 대조.
  반환 경로와 실제 기록 일치·다른 engine 차단 검사. 원본 JSON dtype 덮어쓰기 없음.
- `verify_engine/trt_runner`: 실제 named I/O name/mode/shape/dtype를 할당 전에 대조.
  PyCUDA primary context 활성화 후 TRT deserialize/context 생성; pinned host→device→enqueue→host→sync.
  실패 시에도 sync, buffer/context 자원 해제, pop/detach. deserialize/context/address/execute 실패 검사.
  enqueue 시간·CUDA event 시간·완료된 복사/추론 시간을 구분한다. 실제 통신 경로 성능 측정이 아니다.
- 수치 검증: ORT metadata로 원본 uint8 feed 구성, 명시한 이미지 retype만 float16으로 공급.
  이름/shape/dtype·NaN/Inf·비정상 error·threshold 초과를 실패 처리. reshape/cast로 오류를 숨기지 않음.
  frames<=0, 음수/NaN/Inf threshold 거부; threshold 0은 유효한 exact gate.
  ORT 부재/비교 미수행은 INCOMPLETE. gate 요청을 build-only로 무시하지 않는다.
- `verify_onnx_pair`: ORT CPU 세션 하나씩 실행, 첫 backend 출력은 임시 디스크에 보관.
  seed 73, frame 0 zero smoke, 이후 변화하는 영상·0/255 픽셀·desire 전환·동일 scalar 입력.
  recurrent는 각자 next_state를 이어가며, same-state는 매 step 동일한 zero state를 공급.
  outputs와 next_state 3종을 매번 검사하며 실패 state를 다음 frame에 전달하지 않는다.
- `tools/patch_v3_uint8.py`: 원본 경로 덮어쓰기 거부, FP16 이외 Cast 경계 거부, 별도 파일에 원자적 저장.
  `tools/onnx_meta_light.py`: 원본 I/O·slice/checkpoint 대조 추가. JSON 재생성/PKL 실행 없음.
- V2: 기존 5개 fresh-build dtype/legacy 계약 검사 유지. V3 auto 판별이 V2에 새 retype을 적용하지 않음.
  고정 J의 V2 head-Cast 가공/build/backend는 변경하지 않았다. 실제 V2 TRT build는 검증하지 않았다.
- **미연결:** 고정 J production `onnx_patch.py::patch_file`, TRT `build.py::build_engine`,
  `__init__.py::TrtBackend`는 이 V3 sidecar를 읽지 않는다. 별도 패치를 만든 것으로도 보고하지 않는다.
  후속 단계에서 기존 cache/runtime tag 및 session load/warm에 이 기록을 전달해야 한다.
  session/queues state narrowing, protocol2 거부/모델 선택 문제도 이번 수정 범위 밖이다.

### 실제 환경·명령·결과

실행 파일 `$PY = '../.venv-v3/Scripts/python.exe'` (저장소 기준).
Windows 개발용 venv: Python **3.12.14**, NumPy **2.5.4**, pytest **9.1.1**,
onnx **1.23.2**, onnxruntime **1.31.0**, protobuf **7.36.2**.
bundled Python `$BUNDLED_PYTHON`로
`-m venv ../.venv-v3`, 해당 venv에서 `-m pip install numpy pytest onnx onnxruntime` 실행.
시스템/운영 Python은 변경하지 않았다. Windows 실행 별칭은 사용하지 않았다.
실제 ORT 등록 provider는 매 세션 **`['CPUExecutionProvider']`**. GPU 실행/전체 op GPU placement 주장은 없음.

아래 최종 실행은 모두 `e65ed6a46befba4c9211d9707e9bee63f7f29507`의 동일 제품 코드다.
로컬 로그는 `../evidence/phase2-final-*.log`, 명령/exit/SHA는 `phase2-final-results.json`에 보존한다.

| 실제 실행 명령 (`& $PY`) | 결과 / exit | 구분 |
|---|---|---|
| `-m pytest tests/test_v3_build_verify.py -q` | **41 PASS**, exit 0 | CPU fixture, 작은 실제 ONNX 구조, TRT/CUDA/ORT mock; 모델 없는 격리 safety 40 PASS 포함 |
| `tests/test_stateful_safety.py` | **46 PASS**, exit 0 | CPU/모의 session 40 + 실제 원본 ORT recurrence·patched parity 6 assertions |
| `tests/test_backport.py` | **38 PASS**, exit 0 | 기존 V2/state/spec, 실제 네트워크 조회, 실제 ONNX I/O shape 검사 |
| `tools/onnx_meta_light.py artifacts/big_driving_supercombo_v3.onnx artifacts/cinque_v3.json` | **PASS**, exit 0 | 실제 원본 I/O dtype까지 포함, slice/checkpoint 대조 |
| 아래 공통 비교 명령 + `--comparison-mode recurrent` | **측정 완료**, exit 3 | 실제 ONNX/ORT CPU, 독립 state 5프레임×4 tensors, max/mean abs 0; 합격 보류 |
| 아래 공통 비교 명령 + `--comparison-mode same-state` | **측정 완료**, exit 3 | 같은 zero state의 단일 step 5회×4 tensors, max/mean abs 0; 합격 보류 |
| 실제 TensorRT parse/build/run, 원본↔TRT | **BLOCKED**, 미실행 | TensorRT/PyCUDA와 장치 환경 없음; mock 통과와 구분 |
| Linux 통신/운영 tests 전체 | **SKIP**, 재실행 안 함 | 1단계 Windows sendmsg/fcntl 제약 기록 유지, 이번 범위 밖 |

공통 비교 명령:
```powershell
& $PY -u tools/build_trt_v3.py --onnx artifacts/big_driving_supercombo_v3.onnx --spec artifacts/cinque_v3.json --out artifacts/v3_phase2_patched.onnx --onnx-only --frames 5
```
`--require-max-abs-err`는 지정하지 않았다. 허용오차 근거가 없으므로 0 오차 관측을
TRT/장치/차량 적용의 합격 기준으로 확대하지 않는다. exit **0**은 요청 gate 통과 또는 build-only 완료,
**1**은 실패, **2**는 잘못된 CLI 인수, **3**은 비교 미완료/측정 후 합격 보류다.

수정 전: 기존 safety는 30 PASS 뒤 실제 파일 부재로 exit 1 (`phase2-safety-before.log`).
fixture 추가 후에도 missing-file 메시지 계약이 없어 실패함을 확인하고 identity 함수를 최소 수정했다.
집중 검사 첫 실행은 17 FAIL (`phase2-focused-red.log`), 이후 기능 수정으로 통과.
gate를 build-only에서 무시하는 문제와 cleanup 실패 시 pop 누락도 2 FAIL로 재현 후 수정했다
(`phase2-final-gates-red.log`). 기존 assertion을 완화/삭제하거나 전체 suite를 skip하지 않았다.

### 고정 참고와 다음 단계

carrot-jetson `d0dc96fa32410403dfb2fefff3e2909c11ec109b`,
carrot-wip `029ab60eb19e7b9d4d76bfee1ce99a7521934511` 재대조, 사본 둘 다 clean.
최신화·원격 push 없음. 실제 설치 버전은 여전히 미확인이다.
미수행 범용 변환기/MDM 작업은 현재 목표에서 제외한 상태를 유지한다.

3단계 첫 작업: 고정 J의 V3 patch/build/backend 소비 지점을 격리 개발 사본에서 연결하고
기존 stateful session을 최소 hunk로 재사용하여 V2/V3 build/cache/load/warm 계약을 검사한다.
별도 사용자 지시 전 시작하지 않는다. V3 정상가동/차량 적용 준비 완료로 보고하지 않는다.

## 1단계 조사 기록 (아래는 당시 상태)


조사일: 2026-10-11 (Asia/Seoul). 제품 코드 수정·장치 접속/변경·주행 없음.
현재 목표/제약은 [AGENTS.md](../AGENTS.md), 후속 작업은 [최소 변경계획](V3_JETSON_PLAN.md)을 따른다.
README/REPORT/GPT_PROMPT/설치 가이드의 과거 성공 문구는 아래의 현재 결과를 대체하지 않는다.

## 작업 기준점

| 항목 | 확인 결과 |
|---|---|
| 대화 시작 경로 | `$WORKSPACE` — 비어 있음, Git 저장소 아님 |
| 실제 개발 저장소 | 시작 경로 아래 `jetson-v3-backport`에 지정 원격을 새로 클론 |
| origin | `https://github.com/rownlvh8875-coder/jetson-v3-backport` |
| 최초 로컬 HEAD / 원격 main | `2519ad0bdbf6e796fa590063fc90d4d6461b6b8d` |
| 작업 브랜치 | `feature/cinque-v3-jetson` (main에서 생성) |
| 최초 차이 | `git rev-list --left-right --count HEAD...origin/main` → `0 0`, 미커밋 변경 없음 |
| 기존 이력 | 26 commits 보존. `3d315f92434657825673be7279f389e7ea1ea309` 안전성 테스트, `3794dd5bd6a1d9b8500f3e2b0ae28ace8b602a43` dtype seam, `7c8a67d310b6f2bd4742f788989079941ea92d3c` V3 patch/FP16 수정 등 |
| 기존 지침/진행 문서 | 이 저장소 및 적용되는 상위 경로에 AGENTS.md 없음. docs/ 두 파일도 없음. README, REPORT, SUMMARY_QA, GPT_PROMPT, JETSON_SETUP_GUIDE를 읽음 |

기존 개발 사본 검색 범위: Documents/Codex, Desktop, Downloads, `C:\openpilot`,
`D:\CyberPilot`, `D:\carrot-jetson-windows`. 대상 저장소 사본/개발 브랜치는 이 범위에서
발견하지 못했고, 원격 heads는 main 하나였다. 다른 사용자 작업/프로세스는 변경하지 않았다.
위 HEAD는 **제품 코드 조사·테스트 기준 SHA**다. 이후 문서 커밋의 HEAD/원격 상태는
최종 보고와 `git rev-parse HEAD`, `git ls-remote origin refs/heads/feature/cinque-v3-jetson`으로 확인한다.

## 고정 참고 코드

| 저장소 | 시작 시 조회·고정한 전체 SHA | 개발용 사본 |
|---|---|---|
| [carrot-jetson](https://github.com/ajouatom/carrot-jetson/tree/d0dc96fa32410403dfb2fefff3e2909c11ec109b) | `d0dc96fa32410403dfb2fefff3e2909c11ec109b` | `../references/carrot-jetson` (detached) |
| [openpilot carrot-wip](https://github.com/ajouatom/openpilot/tree/029ab60eb19e7b9d4d76bfee1ce99a7521934511) | `029ab60eb19e7b9d4d76bfee1ce99a7521934511` | `../references/openpilot` (detached, 관련 경로 sparse checkout) |

`git ls-remote` 후 해당 SHA를 fetch/checkout했고 `git rev-parse HEAD`로 대조했다.
참고 사본에는 제품 변경이 없다. carrot-jetson의 `third_party/jetlink/UPSTREAM.md`는
vendoring 원본을 `194ff6dc71cd27282378fff155e94daa7770152b`로 기록한다.
그러나 현재 파일 상태는 각 고정 저장소 SHA로 판단한다.
실제 장치의 Git SHA, JetPack/L4T/CUDA/TensorRT 버전은 **미확인**이다.
과거 REPORT의 L4T 36.4.7 / TensorRT 10.3.0 / Carrot R2는 과거 기록일 뿐이다.

## V3 원본 확보 상태

- 명세 기록: SHA256 `404a18cfd86d29637d20c697dfde245bb47c666ae016730ab674c65f4d1e1aa4`, `766354845` bytes.
- `artifacts/big_driving_supercombo_v3.onnx`는 없다. 검색한 로컬 모델 후보도 모두 불일치했다.
  저장소/위 개발 폴더 외에 `.cache`, OneDrive, `C:\Temp`, `D:\CarrotLogs`, `D:\carrotlog`도 검색했다.
  전체 PC/오프라인 볼륨/NAS에 없다고 단정하지 않는다.
- 전체 파일 해시를 계산한 후보: `D:\CarrotLogs\주행모델\driving_supercombo.onnx`는
  `96618974` bytes / `d0caa7d771cf9b905fca9db471d3413eed1b8b0611413f84c0da964e5992126e`;
  CyberPilot의 두 개발 사본은 각각 `60792584` / `f73a9e535523d5e9acb9e642c64e33d631825dc8ba74123757d107cedd047bb5`,
  `60918562` / `65a08adc31d5c456219687d99b7bf5e44d61dae2d49ea67850e76105c7248cce`.
  다른 CarrotLogs 사본은 133-byte LFS pointer였다. 대체 모델로 사용하지 않았다.
- 기존 출처 [HF tree API](https://huggingface.co/api/models/commaai/openpilot_driving_models/tree/main/f78ed37d-afad-4dbc-8050-40ea885eedde/12864)에서
  `big_driving_supercombo.onnx`의 LFS oid/size가 위 기록과 일치했다.
  [기존 다운로드 주소](https://huggingface.co/commaai/openpilot_driving_models/resolve/main/f78ed37d-afad-4dbc-8050-40ea885eedde/12864/big_driving_supercombo.onnx)의
  TLS 검증을 유지한 HEAD는 HTTP 200, Content-Length `766354845`였다.
  본문 다운로드/전체 해시/실제 I/O 재파싱은 하지 않았다. 출처 응답은 확보 완료 증거가 아니다.

| 진행 항목 | 현재 상태 |
|---|---|
| V3 원본 확보·전체 해시·I/O 대조 | BLOCKED — 대상 로컬 원본 미확보, 출처 metadata/HEAD만 확인 |
| 소프트웨어 테스트 | 일부 PASS, FAIL/환경 제약/SKIP 있음 (아래 실행 기록) |
| 실제 Jetson 엔진 빌드·반복 추론 | BLOCKED — 원본/실제 장치 환경 미확인 |
| 원본 대비 수치 검증 | SKIP — 실제 ONNX/ORT/TRT 없음, 허용오차 미정 |
| 실제 comma 연결·성능·state·복귀/알림 | BLOCKED — 실제 장치 검증은 후속 단계 |
| 주행 검증 | 이번 범위 밖, 미실시 |

## 실제 검사 기록

Windows 11, Python `3.14.7`, NumPy `2.5.2`, pytest `9.1.1`.
onnx/onnxruntime/tensorrt/cuda 모듈 없음. 패키지 업그레이드 없음.
아래 명령의 `$PY`는 PowerShell에서 다음 실행 파일이다.

```powershell
$PY = '$SYSTEM_PYTHON_3_14'
```

기본 작업 디렉터리는 개발 저장소. `WIP`는 위 carrot-wip SHA의 개발용 사본,
`JETSON`은 위 carrot-jetson SHA의 사본이다. 로그와 일회성 CPU 재현 스크립트는
저장소 밖 `../evidence/`에 보존하며 Git에 포함하지 않는다.
`--noconftest -o addopts=`는 하드웨어/전체 런타임을 초기화·정리하는 저장소 공통 fixture와
미설치 전체 스위트 플러그인을 제외한 독립 단위 검사다. 테스트 본문/assertion은 변경하지 않았다.
전체 openpilot 스위트나 장치 테스트 통과로 해석하지 않는다.

| 명령 / 코드 기준 | 실제 결과·exit | 분류·근거 / 로컬 로그 |
|---|---|---|
| `& $PY tests/test_backport.py` / `2519ad0…` | 36 passed, 0 failed, exit 0 | PASS; JSON/합성 state/V2 회귀 및 실제 네트워크 pointer 조회. 원본 I/O 검사 한 구간 SKIP. `backport-py314.log` |
| `& $PY tests/test_stateful_safety.py` / `2519ad0…` | 30개 PASS 후 FileNotFoundError, exit 1 | FAIL; 525행 identity negative 검사가 원본을 무조건 열어 중단. 실제 모델 recurrent/patch parity 두 구간 SKIP. `safety-py314.log` |
| `& $PY -m compileall -q jetlink tools tests` / `2519ad0…` | exit 0 | PASS, 문법만 검사 (실제 실행 아님). 실제 호출은 대화 폴더에서 각 경로 앞에 `jetson-v3-backport/`를 붙임 |
| `& $PY tools/build_trt_v3.py --help` / `2519ad0…` | exit 0 | PASS, argparse만 검사. `build-help.log` |
| JETSON: `& $PY -m pytest --noconftest -o addopts= -q tools/jetlink/test_download_model.py` | 4 passed, exit 0 | PASS; 합성 bytes/monkeypatch 다운로드, 실제 V3 다운로드 아님. `carrot-jetson-download.log` |
| WIP: `& $PY -m pytest --noconftest -o addopts= -q tools/jetlink/test_stateful_protocol.py` | 2 passed, 9 failed, exit 1 | FAIL (개발 OS 제약); 9건은 Windows socket의 `sendmsg` 부재. Linux/USB/Jetson 결함으로 단정하지 않는다. `carrot-wip-stateful.log` |
| WIP: `& $PY -m pytest --noconftest -o addopts= -q openpilot/selfdrive/modeld/tests/test_jetlink.py` | 17 passed, 5 skipped, exit 0 | PASS/SKIP; 모의 warp·IPC 경계/명세·deadline, Windows AF_UNIX 부재로 5건 SKIP. `carrot-wip-joining-focused.log` |
| WIP: `& $PY -m pytest --noconftest -o addopts= -q tools/jetlink/test_app_models.py -k 'model_spec_round_trip_and_parser_shapes or joining_model_uses_selected_buffers_parser_and_recurrence'` | collection error, exit 2 | BLOCKED; `daemon.py`의 Linux `fcntl` 없음. V3 parser/복귀 본문은 미실행. `carrot-wip-app-focused.log` |
| `& $PY ../evidence/audit_checks.py` / 개발 저장소 + WIP SHA | exit 0, 결함 재현 assertion 충족 | CPU 합성/mock 재현; **제품 동작 PASS가 아님**. state narrowing Inf, builder layer 접근/반환, ORT NaN gate, protocol2 V3 차단. `audit-checks.log` |
| `git -C <참고사본> apply --check <각 원본 patch>` | 6개 모두 exit 1 | FAIL; Windows CRLF 영향도 존재. 원본/참고 코드 변경 없음 |
| LF 사본으로 `git -C <참고사본> apply --cached --check <patch.lf>` | Jetson 4개 exit 0, comma 2개 exit 1 | PASS/FAIL; index 대상 읽기 검사만, 실제 적용 없음. comma 문맥 불일치 확정. 정규화 사본은 `../evidence/*.patch.lf` |

최초 `python tests/...` 두 호출은 WindowsApps 실행 별칭 때문에 exit 9009였다.
실행 파일을 명시하여 위 결과를 얻었다. 초기 WIP 합동 collection은 sparse checkout의
`openpilot.common` 부재와 `fcntl`로 중단(exit 2); 직접 의존 common을 checkout한 뒤
단독 test_jetlink를 실행했다. 합동 시도는 `carrot-wip-joining.log`에 남아 있다.
Ubuntu/Ubuntu-24.04의 기존 Python에는 NumPy/pytest가 없었다.
Ubuntu-24.04에서 `/tmp/cinque-v3-phase1-20261011`에 개발용 venv 생성을 시도했지만
ensurepip/python3-venv 부재로 exit 1, 이어진 해당 venv pip도 모듈 부재로 실패했다.
패키지는 설치되지 않았으며 운영/시스템 패키지 변경으로 확장하지 않았다. Linux 재실행은 BLOCKED다.
pytest는 미설치 asyncio/cpp 플러그인 설정 3개의 warning도 보고했다.

## 기존 기능과 미수행 범용 작업의 처리

`jetlink/spec.py`, `queues.py`, `patches/session.py.new`의 stateful/검증/초기화 구현과
현재 carrot-wip의 전처리·동적 packed·출력 parser·복귀를 재사용한다.
과거 리뷰의 finite/shape/warm/BuilderFlag/API 지적은 코드에서 이미 반영된 부분과
현재 남은 문제를 [계획](V3_JETSON_PLAN.md)에 분리했다.
`jetlink/registry/catalog.py`와 LFS resolver 등 범용 성격의 기존 코드는 보존한다.
대상 원본의 identity/pointer 확인에 필요한 부분만 재사용하며 카탈로그/CLI 확장은 하지 않는다.
이 저장소 26개 이력/파일에서 별도 범용 변환기·MDM 구현계획은 확인되지 않았다.
다른 대화/위치의 미수행 범용 작업은 이번 사용자 지시로 현재 목표에서 제외한다.
