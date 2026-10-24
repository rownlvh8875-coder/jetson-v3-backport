# jetson-v3-backport

> **2026-10-19 현재 기준:** 개발 주 경로를 **protocol 3 + Jetson 멀티모델**로 전환했다.
> 현재 `carrot-wip`는 이미 protocol 3, dynamic `ModelSpec`, stateful 모델 parsing/fallback 기반을 갖고 있다.
> 따라서 과거 protocol-2 Cinque V3 force-fit은 역사/비상 fallback 자료로 보존하고,
> 신규 작업은 [Carrot × Jetson 멀티모델 개발계획](docs/JETLINK_MULTIMODEL_PLAN_20261019.md)을 따른다.
> 실제 Jetson 적용 전에는 [read-only runtime inventory](tools/jetson_runtime_inventory.py)로
> SSD에 설치된 R2 runtime/service/TensorRT 경로를 먼저 확인한다.

**최신 작업 인계:** [CODEX_CONTINUATION.md](docs/CODEX_CONTINUATION.md).

2026-10-24 [M19-C1 OFF 배포 시도](docs/M19C1_810E_ACTUAL_OFF_DEPLOYMENT_20261024.md):
첫 실제 값이 OFF/ON0/1이어서 **BLOCKED_NOT_OFFROAD**로 중단했다.
migration·ticket·capture·restart는 하지 않았으며 fresh CPU415 PASS다.
정상 OFF 전환 후 새 preflight부터 재개해야 한다.

2026-10-24 [M19-C0 exact810e recorder](docs/M19C0_810E_SHARED_INPUT_REBASE_20261024.md):
사용자 보고 actual810e의 shared-input/N16 계약에 맞춘 **별도 오프라인 후보**를 준비했다.
기존366 recorder는 현재 API와 **호환되지 않는다**. CPU415 PASS이며 실제 comma·Jetson에
접근하거나 배포·ticket·capture·restart를 수행하지 않았다. 다음은 별도 승인된 OFF 배포
preflight다. 이전366 설치/준비 상태를810e의 현재 검증으로 재사용하지 않는다.

2026-10-24 [M19-B0 activation 검토](docs/M19B0_ACTIVATION_CHOREOGRAPHY_20261024.md):
**B 권고**, 기본 OFF/1회성 volatile ticket 후보를 오프라인 검증했다.
준비용 subprocess의 잘못된 소비를 막는 modeld/launcher guard와 2파일 delta·reverse를 준비했고
**CPU310 PASS**다. 실제 comma는 M19-A 설치 OFF 상태 그대로이며 후보 배포·capture는 하지 않았다.
다음은 별도 승인된 detached/OFF activation-delta 배포이며 차량10프레임은 아직 NO다.


2026-10-24 [M19-A detached 설치 결과](docs/M19A_DETACHED_INSTALL_RESULT_20261024.md):
actual366의 원래48 overlay를 보존하고 exact recorder patch를 설치했다.
**PATCH_LEFT_INSTALLED_OFF**, 재시작·ticket·활성화·capture는 하지 않았다.
Panda/harness detached evidence, OFF health와 별도 POST attestation PASS다.
M19-B는 offroad arming/일시적 launch 환경 전달 순서를 먼저 검토해야 하므로 **아직 NO**다.
수치 판정은 PARITY_UNDETERMINED, M2는 NO다.

현재 source adapter, 검증 결과와 원복 절차는
[current candidate 검증 안내](docs/CURRENT_CARROT_VALIDATION_20261019.md)에 있다.
최신 upstream 확인과 분리된 CPU 검증은
`python tools/check_latest_carrot_compat.py --update-baseline`으로 실행한다.
2026-10-23 [M0.5 비교](docs/M05_CARROT_NAV_VS_WIP_20261023.md)는 **전략 A**를 추천한다.
실제 comma의 `carrot-nav`와 운영 Protocol2/V2/Nav를 보존하고 필요한 managed P3 부분만 별도 준비한다.
[M1 실기 기록](docs/M1_JETSON_V3_TRT10_BUILD_20261023.md): 격리 경로에서 실제 Orin/TRT10.3
V3 빌드와 BASE 10+1000프레임/reset/reload 검사를 통과했다. ORT↔TRT는 수치 측정만 했으며
승인 허용오차가 없다. **DO_NOT_INSTALL**. USB/comma 추론·fallback·차량 검증은 NOT_RUN이다.

2026-10-23 [M1.5 semantic 비교](docs/M15_ORT_TRT_PARITY_20261023.md)는 실제 ORT/TRT
101프레임과 Nav parser를 측정했다. desire 예측 불일치 1건과 미승인 허용오차로
**PARITY_UNDETERMINED / M2 readiness NO**다. [최소 Nav adapter](docs/M15_CARROT_NAV_PROTOCOL3_ADAPTER_20261023.md)는
별도 개발 사본에서 P2/V2/Nav 회귀와 P3/fallback CPU 검증을 통과했다.
[M2 정차 USB 계획](docs/M2_PARKED_USB_PLAN_20261023.md)은 실행하지 않았다.

2026-10-23 [M1.6 정밀 분석](docs/M16_NUMERICAL_ACCEPTANCE_20261023.md): 기존 plan 그대로
historical512프레임의 독립 recurrence와 teacher forcing을 측정했다. 최대 plan/lead 차이는
각각 10초 horizon의 x이고, desire 예측 flip은 작은 top2 margin에서 재현된다.
128-slot turnover는 도달했으나 대표 기록 입력·승인 기준은 없으며 bounded TRT는
deserialize OOM으로 0프레임이다. **PARITY_UNDETERMINED / M2 NO**, 운영본·adapter는 보존했다.

2026-10-23 [M1.7 실제 주행 기록 조사](docs/M17_RECORDED_DRIVING_PARITY_20261023.md):
actual comma의 88개 route를 조사하고 최근 5개 rlog의 복사·해시를 검증했다.
원본 road/wide 영상과 로그 image payload가 없어 V3 입력 재구성은 0프레임이다.
**ORT/TRT NOT_RUN / PARITY_UNDETERMINED / M2 NO**이며 원본·운영본을 보존했다.

2026-10-23 [M1.8 exact input recorder](docs/M18_V3_INPUT_RECORDER_DESIGN_20261023.md):
actual366용 기본 OFF observer patch와 strict replay reader를 오프라인 검증했다.
신규131 + 기존 smoke87 = **CPU218 PASS**, 512프레임20Hz host simulation PASS.
실제 콤마 설치·활성화·기록은 하지 않았다. [M19 계획](docs/M19_COMMA_CAPTURE_PLAN_20261023.md)은
별도 승인 후 정차 preflight부터 진행한다. 수치 승인과 M2는 계속 보류한다.

2026-10-23 [M19 정차 capture 결과](docs/M19_PARKED_CAPTURE_RESULT_20261023.md):
actual366/Offroad1·Onroad0와 원본 source pin은 확인했지만 미추적48항목으로
**BLOCKED_DIRTY_TREE**다. 설치·재시작·활성화·capture는 하지 않았고 기존 상태를 보존했다.
정차10프레임과 주행 capture는 미실행이며 M2는 계속 NO다.

2026-10-23 [M19.1 읽기 전용 감사](docs/M191_DIRTY_TREE_AUDIT_20261023.md):
미추적48항목은 실제로2,006파일/417,208,589bytes다. 생성물19, 동일 백업1,
런타임 필수26, 소유·생성 근거 미확정2로 분류했다. Recorder 경로 충돌은 없지만
dependency overlay가 실제 사용 중이므로 일괄 정리는 불가하다. 전후 해시·상태를
보존했고 이동·삭제·ignore 변경은 하지 않았다. **M19 설치 재시도 NO / M2 NO**다.

2026-10-24 [M19.2 exact dirty baseline](docs/M192_ATTESTED_DIRTY_BASELINE_20261024.md):
runtime overlay 48항목을 이동·삭제 없이 원래 digest로 재검증했다. U46은 PC에서
byte-exact 재생성했지만 U32의 현재 dynamic 사용 여부가 미확정이므로
**ATTESTED_DIRTY_BASELINE_PARTIAL / M19 재시도 NO**다. 읽기 전용 checker와
disposable layout 검증을 추가해 **CPU200 PASS / FAIL0 / SKIP0**다. 과거 JSON
전송기의 nanosecond 정밀도 손실도 수정·재수집했으며 baseline은 바꾸지 않았다.
실제 source 변경·recorder 설치·재시작·capture는 하지 않았다. **M2 NO**를 유지한다.

2026-10-24 [M19.3 U32 provenance](docs/M193_U32_PROVENANCE_20261024.md):
관련 공개 fork의99.80% 유사 source와 exact PC pyc 재생성을 확인했다. 현재 runtime
사용 여부는 UNKNOWN이며, actual366의 고정된 source/namespace/OFF 경계에 한정해
**UNKNOWN_ACCEPTABLE_FOR_PATCH_ISOLATION**으로 수용한다. 기존 M192 checker의
PARTIAL은 보존하고 별도 M193 정책으로 baseline PASS를 기록한다. **M19 재시도 YES**는
새 정차 preflight와 별도 설치 승인부터 시작한다는 뜻이다. 실제 변경·capture는 없고
**CPU258 PASS / FAIL0 / SKIP0 / M2 NO**다.

2026-10-24 [M19 재시도](docs/M19_PARKED_CAPTURE_RESULT_20261024.md): fresh dirty baseline은
PASS했지만 live carState가 없어 **BLOCKED_STATIONARY_UNCONFIRMED**로 중단했다.
설치·재시작·capture는 없고 원래48/source/model/process/route 증거를 보존했다.
**CPU258 PASS / FAIL0 / SKIP0 / 주행 capture NO / M2 NO**다.

2026-10-20 [외부 Jetson 최적화 검토](docs/JETSON_REVIEW_A890_ANALYSIS.md):
DeviceState와 InputFastpath는 기존 검증을 유지한 기본 OFF 실험 후보다.
AIO는 운영 transport에 연결하지 않았으며, 실장 순서는 M0 → 기본 V3 → USB →
latency 측정 → 필요한 최적화 A/B를 유지한다.

> Jetson Orin Nano Super에서 Cinque V3 및 호환 Big Model을
> Carrot/comma4와 안전하게 연결하기 위한 연구·백포트 저장소

## 현재 목표

1차 목표는 **기존 V2를 보존한 채 Cinque Terre V3를 protocol 3으로 추가**하고,
정차/offroad에서 V2↔V3를 선택할 수 있게 만드는 것이다.

그 다음 같은 프레임워크로 BMRLNAP v6 등 호환 모델을 하나씩 검증한다.
Lebowski나 최신 Mountain Dew 계열은 모델 목록에 있다는 이유만으로 자동 허용하지 않는다.

목표 구조:

```text
comma4 / carrot-wip
  ├─ local small model fallback
  ├─ Jetlink protocol 3
  ├─ dynamic queued/stateful ModelSpec
  └─ offroad model approval
             │ USB 3
             ▼
Carrot Jetson R2 / Orin Nano Super
  ├─ existing V2 engine
  ├─ protocol 3 host
  ├─ TensorRT 10.3 engine cache
  └─ V3 → 이후 검증된 추가 모델
```

## 왜 방향이 바뀌었나요?

이 저장소를 처음 만들 때는 Carrot의 Jetson 경로가 사실상 protocol 2 + Cinque V2 고정이어서
stateful V3를 직접 백포트해야 했다.

하지만 2026-10-19 현재 `ajouatom/openpilot:carrot-wip`에는 다음 기반이 이미 들어가 있다.

- strict protocol 2/3 wire
- queued/stateful `ModelSpec`
- dynamic packed input/output parser
- protocol 3 App-selected 모델 검증
- offroad-only approval
- external model failure → internal small model fallback

그래서 지금의 핵심 공사는 **comma 쪽 V3를 다시 만드는 것**이 아니라
**Carrot Jetson R2 host/server를 protocol 3 + multi-engine 구조로 올리는 것**이다.

## 소스 기준

2026-10-19 조사 기준:

| 구성 | 기준 |
|---|---|
| 이 저장소 기존 V3 branch | `feature/cinque-v3-jetson @ 26c9c06a...` |
| 현재 개발 branch | `feature/jetlink-multimodel-carrot` |
| carrot-wip | `5032afca77a96e31a077a5e9ac738d9ac08a99df` |
| carrot-jetson | `d0dc96fa32410403dfb2fefff3e2909c11ec109b` |
| zoompilot/jetlink 참고 | `d24328d849b0e5154b55f149dc18c5dfe8bd79cc` |
| Carrot R2 metadata | L4T 36.4.7 / TensorRT 10.3.0 / aarch64 |

최신 zoompilot Jetlink의 Jetson benchmark는 JetPack 7.2.1 / TensorRT 10.16 계열이므로
그 바이너리/성능 수치를 현재 R2에 그대로 적용하지 않는다.

## 폴더 설명

| 폴더/파일 | 내용 |
|---|---|
| `docs/JETLINK_MULTIMODEL_PLAN_20261019.md` | **현재 개발 기준**. protocol 3 + 멀티모델 로드맵 |
| `docs/CURRENT_CARROT_HOST_GAPS_20261019.md` | current carrot-wip server에서 실제로 남은 V3 gap을 파일 단위로 정리 |
| `tools/jetson_runtime_inventory.py` | 첫 SSH 접속 때 쓰는 read-only runtime 조사 도구 |
| `jetlink/multimodel_policy.py` | managed protocol-3 Jetson 선택 계약 proposal |
| `artifacts/multimodel_seed.json` | V2/V3 초기 로컬 seed identity |
| `docs/PROJECT_STATE.md` | 2026-10-11까지의 세부 구현/검증 기록 |
| `docs/V3_JETSON_PLAN.md` | 과거 단일 V3 force-fit 계획. 신규 주 경로 아님 |
| `artifacts/cinque_v3.json` | 실제 V3 ONNX에서 생성한 모델 계약 |
| `tools/build_trt_v3.py` | TensorRT 10.3 V3 engine build/verify 도구 |
| `tools/jetson_m1.py`, `tools/jetson_m1_recurrent.py` | 격리·offroad guard와 실제 BASE 반복 추론 도구; M1 보고서의 실행 조건 필수 |
| `tools/jetson_m1_parity.py` | 원본 ORT CPU와 BASE TRT의 독립 recurrent 수치 비교; 허용오차 없으면 exit3 |
| `jetlink/` | stateful spec/state/registry 백포트 자산 |
| `tests/` | recurrent/finite/identity/loopback 등 회귀검사 |
| `patches/` | 과거 고정 SHA용 실험 패치. 현재 carrot-wip에 무조건 적용 금지 |
| `REPORT.md` | 2026-10-05까지의 초기 백포트 보고서 |

## 이미 확보된 자산

- Cinque V3 ONNX identity:
  - SHA256 `404a18cfd86d29637d20c697dfde245bb47c666ae016730ab674c65f4d1e1aa4`
  - size `766354845` bytes
- 실제 ONNX 기반 `cinque_v3.json`
- TensorRT 10.3 builder
- stateful recurrent state 관리
- finite/shape/identity gate
- V2 회귀검사
- recurrent multi-frame parity 도구
- fail-closed 설계 자료

## 실기 확인 상태

M0에서 NVMe/runtime/release/service와 패키지를 조사했고, M1에서 실제 TRT/CUDA API,
V3 engine build와 합성 입력 BASE 반복 추론을 확인했다. 전후 운영 cache/service/current는 동일하다.
수치 parity 승인과 다음 항목은 남아 있다.

- protocol-3 USB host/server
- comma camera → Jetson → parser end-to-end
- 20 Hz latency
- 열/전력/throttle
- link/model failure 시 실제 local model fallback
- V2↔V3 전환
- 정지→재출발 거동

## 어디서부터 시작하나요?

**현재 작업** → [JETLINK_MULTIMODEL_PLAN_20261019.md](docs/JETLINK_MULTIMODEL_PLAN_20261019.md)

Jetson SSH가 준비되면 첫 단계:

```bash
python3 tools/jetson_runtime_inventory.py --pretty
```

이 명령은 설치·서비스 재시작·모델 build를 하지 않고 현재 runtime을 읽기만 한다.

과거 구현 맥락 → [PROJECT_STATE.md](docs/PROJECT_STATE.md)

초기 백포트 전체 보고 → [REPORT.md](REPORT.md)

## 주의

- 기존 정상 V2 환경을 먼저 보존한다.
- 과거 `jetson-production-v3.patch` / `comma-integration-v3.patch`를 현재 HEAD에 그대로 적용하지 않는다.
- 최신 upstream Jetson binary를 Carrot R2에 바로 복사하지 않는다.
- 모델 build/download/선택은 offroad에서만 한다.
- 실제 USB·latency·fallback 검증 전에는 V3 주행 사용을 완료로 선언하지 않는다.
- v3가 정지·재출발 흔들림을 개선한다는 것은 아직 실증되지 않았다.
